"""Boş optik form üretimi + test/demo için doldurulmuş form ve "kamera fotoğrafı" simülasyonu.

Not: OpenCV'nin Hershey yazı tipleri Türkçe karakterleri desteklemediği için form üzerindeki
yazılar ASCII (OGRENCI NO, CEVAPLAR ...) yazılmıştır.
"""
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from . import io
from . import layout as L

FONT = cv2.FONT_HERSHEY_SIMPLEX


def _p(v: float, s: int) -> int:
    return int(round(v * s))


def _text(img, text, x, y, s, size=0.8, thick=2, center=False, color=0):
    th = max(1, round(thick * s / 2))
    (tw, _), _ = cv2.getTextSize(text, FONT, size * s, th)
    px = _p(x, s) - (tw // 2 if center else 0)
    cv2.putText(img, text, (px, _p(y, s)), FONT, size * s, color, th, cv2.LINE_AA)


def draw_blank_form(scale: int = 2) -> np.ndarray:
    """Boş formu gri (uint8) görüntü olarak çizer. scale=2 -> 2000x2828 px (yazdırmak için ideal)."""
    s = scale
    img = np.full((L.FORM_H * s, L.FORM_W * s), 255, np.uint8)

    # Köşe işaretçileri
    half = L.MARKER_SIZE // 2
    for cx, cy in L.MARKER_CENTERS:
        cv2.rectangle(img, (_p(cx - half, s), _p(cy - half, s)), (_p(cx + half, s) - 1, _p(cy + half, s) - 1), 0, -1)

    # Yön çubuğu
    bx, by = L.ORIENT_BAR_CENTER
    bw, bh = L.ORIENT_BAR_SIZE
    cv2.rectangle(img, (_p(bx - bw / 2, s), _p(by - bh / 2, s)), (_p(bx + bw / 2, s) - 1, _p(by + bh / 2, s) - 1), 0, -1)

    # Başlıklar
    _text(img, "OPTIK OKUMA FORMU", 500, 125, s, size=1.3, thick=3, center=True)
    _text(img, "Kursun kalemle daireyi tamamen doldurun. Silerken kagidi yirtmayin.", 500, 165, s, size=0.55, thick=1, center=True)
    _text(img, "OGRENCI NO", L.ID_X0 + 3.5 * L.ID_X_STEP, 195, s, size=0.8, thick=2, center=True)
    _text(img, "CEVAPLAR", 500, 618, s, size=0.9, thick=2, center=True)

    r = _p(L.BUBBLE_RADIUS, s)
    line = max(1, s)

    # Öğrenci numarası: elle yazma kutuları + balonlar
    for pos in range(L.ID_DIGITS):
        cx, _ = L.id_bubble_center(pos, 0)
        cv2.rectangle(img, (_p(cx - 17, s), _p(L.ID_Y0 - 48, s)), (_p(cx + 17, s), _p(L.ID_Y0 - 22, s)), 0, line)
        for d in range(10):
            cx, cy = L.id_bubble_center(pos, d)
            cv2.circle(img, (_p(cx, s), _p(cy, s)), r, 0, line, cv2.LINE_AA)
    for d in range(10):
        _, cy = L.id_bubble_center(0, d)
        _text(img, str(d), L.ID_X0 - 38, cy + 7, s, size=0.55, thick=1, center=True)

    # Sağ taraf: ad-soyad, sınıf, puan kutusu
    for label, y in (("AD SOYAD:", 270), ("SINIF:", 330), ("TARIH:", 390)):
        _text(img, label, 560, y, s, size=0.6, thick=1)
        cv2.line(img, (_p(680, s), _p(y + 4, s)), (_p(930, s), _p(y + 4, s)), 0, line)
    cv2.rectangle(img, (_p(560, s), _p(420, s)), (_p(930, s), _p(560, s)), 0, line)
    _text(img, "PUAN (ogretmen)", 575, 445, s, size=0.5, thick=1)

    # Cevap balonları
    for col in range(2):
        for o, ch in enumerate(L.OPTIONS):
            _text(img, ch, L.ANSWER_X0[col] + o * L.ANSWER_X_STEP, L.ANSWER_Y0 - 25, s, size=0.6, thick=1, center=True)
    for q in range(L.NUM_QUESTIONS):
        x0, cy = L.answer_bubble_center(q, 0)
        _text(img, f"{q + 1}.", x0 - 70, cy + 7, s, size=0.55, thick=1)
        for o in range(len(L.OPTIONS)):
            cx, cy = L.answer_bubble_center(q, o)
            cv2.circle(img, (_p(cx, s), _p(cy, s)), r, 0, line, cv2.LINE_AA)
    return img


def fill_form(blank: np.ndarray, answers: Sequence[str], student_id: str = "", scale: int = 2, seed: int = 0) -> np.ndarray:
    """Boş forma el yapımı gibi işaretler ekler.

    answers: her soru için 'A'..'E', '' (boş) ya da 'AB' (birden fazla işaret).
    """
    rng = np.random.default_rng(seed)
    img = blank.copy()

    def mark(cx, cy):
        jx, jy = rng.normal(0, 0.8, 2)
        rad = L.BUBBLE_RADIUS - rng.uniform(1.5, 3.0)
        tone = int(rng.integers(30, 90))
        cv2.circle(img, (_p(cx + jx, scale), _p(cy + jy, scale)), _p(rad, scale), tone, -1, cv2.LINE_AA)

    for q, a in enumerate(answers):
        for ch in a:
            mark(*L.answer_bubble_center(q, L.OPTIONS.index(ch)))
    for pos, ch in enumerate(student_id):
        if ch.isdigit():
            mark(*L.id_bubble_center(pos, int(ch)))
    return img


def simulate_photo(form_gray: np.ndarray, seed: int = 0, rotate_k: int = 0, canvas=(1300, 1800)) -> np.ndarray:
    """Formu masa üstünde, hafif eğri/perspektifli, gölgeli ve gürültülü çekilmiş gibi gösterir.

    rotate_k: fotoğrafı saat yönünde k*90 derece çevirir (yan/baş aşağı çekim testi).
    """
    rng = np.random.default_rng(seed)
    cw, ch = canvas
    fw, fh = L.FORM_W, L.FORM_H
    form = cv2.resize(form_gray, (fw, fh), interpolation=cv2.INTER_AREA)
    form = cv2.cvtColor(form, cv2.COLOR_GRAY2BGR)

    src = np.float32([[0, 0], [fw, 0], [fw, fh], [0, fh]])
    ox, oy = (cw - fw) / 2, (ch - fh) / 2
    dst = np.float32([[ox, oy], [ox + fw, oy], [ox + fw, oy + fh], [ox, oy + fh]])
    dst += rng.uniform(-45, 45, (4, 2)).astype(np.float32)           # perspektif bozulması
    rot = cv2.getRotationMatrix2D((cw / 2, ch / 2), rng.uniform(-6, 6), 1.0)
    dst = cv2.transform(dst[None], rot)[0].astype(np.float32)        # hafif eğiklik

    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(form, M, (cw, ch), flags=cv2.INTER_LINEAR).astype(np.float32)
    mask = cv2.warpPerspective(np.full((fh, fw), 255, np.uint8), M, (cw, ch))
    mask = (cv2.GaussianBlur(mask, (0, 0), 1.2).astype(np.float32) / 255.0)[..., None]

    bg = np.empty((ch, cw, 3), np.float32)
    bg[:] = (90, 110, 130)
    bg += cv2.GaussianBlur(rng.normal(0, 14, (ch, cw)).astype(np.float32), (0, 0), 3)[..., None]
    out = warped * mask + bg * (1 - mask)

    a, b = rng.uniform(-0.2, 0.2, 2)                                  # ışık gradyanı (gölge)
    light = 1 + a * np.linspace(-1, 1, cw)[None, :] + b * np.linspace(-1, 1, ch)[:, None]
    out *= light[..., None]
    out += rng.normal(0, 5, out.shape)                                # sensör gürültüsü
    out = cv2.GaussianBlur(np.clip(out, 0, 255).astype(np.uint8), (0, 0), 1.0)

    rots = [None, cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]
    return out if rotate_k % 4 == 0 else cv2.rotate(out, rots[rotate_k % 4])


def random_answers(key: str, rng: np.random.Generator, p_correct=0.7, p_blank=0.05, p_multi=0.0) -> list:
    """Anahtara göre rastgele öğrenci cevapları üretir (test/demo için)."""
    out = []
    for c in key:
        u = rng.random()
        if u < p_blank:
            out.append("")
        elif u < p_blank + p_multi:
            out.append("".join(rng.choice(list(L.OPTIONS), 2, replace=False)))
        elif u < p_blank + p_multi + p_correct and c in L.OPTIONS:
            out.append(c)
        else:
            out.append(str(rng.choice([o for o in L.OPTIONS if o != c])))
    return out


def make_demo_samples(key: str, out_dir, seed: int = 7) -> list:
    """out_dir klasörüne 3 sahte öğrenci fotoğrafı üretir (cevaplar ground-truth olarak anahtara göre rastgele)."""
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    blank = draw_blank_form(2)

    profiles = [  # (öğrenci no, doğru oranı, boş oranı, çift işaret oranı, çeyrek tur)
        ("20240101", 0.90, 0.03, 0.00, 0),
        ("20240102", 0.55, 0.10, 0.00, 0),
        ("20240103", 0.70, 0.05, 0.05, 1),     # yan çevrilmiş çekim
    ]
    paths = []
    for i, (sid, pc, pb, pm, rk) in enumerate(profiles, 1):
        answers = random_answers(key, rng, pc, pb, pm)
        if pm:                      # demoda çift işaretli bir soru kesin görünsün
            answers[4] = "BC"
        filled = fill_form(blank, answers, sid, scale=2, seed=seed + i)
        photo = simulate_photo(filled, seed=seed + i, rotate_k=rk)
        path = out_dir / f"ogrenci_{i:02d}.jpg"
        io.imwrite(path, photo)
        paths.append(path)
    return paths
