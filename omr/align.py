"""Form hizalama.

Adımlar:
 1. Işık farkını gider (morfolojik kapama ile arka plan kestirimi) ve Otsu ile ikili görüntü üret.
 2. Konturlar arasından "dolu siyah kare" olanları (köşe işaretçileri) bul.
 3. Dört uç noktayı sırala (SolÜst, SağÜst, SağAlt, SolAlt).
 4. Perspektif dönüşümü ile formu sabit 1000x1414 tuvale düzleştir.
 5. Yön çubuğuna bakarak 0/90/180/270 derece döndürülmüş fotoğrafları düzelt.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from . import layout as L


class AlignmentError(RuntimeError):
    """Form hizalanamadığında fırlatılır (işaretçiler bulunamadı vb.)."""


@dataclass
class AlignResult:
    image: np.ndarray          # (gerekirse küçültülmüş) orijinal BGR görüntü
    warped: np.ndarray         # düzleştirilmiş gri form, FORM_H x FORM_W
    markers: np.ndarray        # 4x2, görüntüdeki işaretçi merkezleri (formun SolÜst, SağÜst, SağAlt, SolAlt sırasıyla)
    rotation: int              # kaç çeyrek tur döndürülmüş bulundu (0-3)
    orient_score: float        # yön çubuğu karanlık skoru (0-255)
    marker_mask: np.ndarray    # debug için ikili görüntü


def limit_size(img: np.ndarray, max_side: int = 1800) -> np.ndarray:
    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_side:
        return img
    s = max_side / m
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def _marker_mask(gray: np.ndarray) -> np.ndarray:
    h, w = gray.shape
    k = max(31, int(max(h, w) * 0.06) | 1)          # işaretçiden büyük bir çekirdek
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)   # koyu küçük nesneleri siler => arka plan ışığı
    norm = cv2.divide(gray, bg, scale=255)                  # ışık farkını gider
    _, th = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    return cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def _find_square_candidates(mask: np.ndarray, min_ratio: float = 1.5e-4, max_ratio: float = 1e-2):
    """Dolu, kareye yakın konturların ağırlık merkezlerini döndürür."""
    img_area = mask.shape[0] * mask.shape[1]
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    centers = []
    for c in contours:
        area = cv2.contourArea(c)
        if not (min_ratio * img_area <= area <= max_ratio * img_area):
            continue
        (_, _), (rw, rh), _ = cv2.minAreaRect(c)
        if min(rw, rh) < 1:
            continue
        aspect = min(rw, rh) / max(rw, rh)                       # kareye yakınlık
        extent = area / (rw * rh)                                # dikdörtgeni doldurma (daire ~0.78, kare ~1)
        solidity = area / max(cv2.contourArea(cv2.convexHull(c)), 1)
        if aspect < 0.65 or extent < 0.85 or solidity < 0.9:
            continue
        m = cv2.moments(c)
        centers.append((m["m10"] / m["m00"], m["m01"] / m["m00"]))
    return np.array(centers, dtype=np.float32)


def order_points(pts: np.ndarray) -> np.ndarray:
    """Noktalardan dört uç köşeyi seçip SolÜst, SağÜst, SağAlt, SolAlt sırasında döndürür."""
    s = pts.sum(axis=1)
    d = pts[:, 1] - pts[:, 0]
    idx = [int(np.argmin(s)), int(np.argmin(d)), int(np.argmax(s)), int(np.argmax(d))]
    if len(set(idx)) != 4:
        raise AlignmentError("Dört farklı köşe işaretçisi seçilemedi.")
    return pts[idx].astype(np.float32)


def _orientation_score(warped: np.ndarray) -> float:
    cx, cy = L.ORIENT_BAR_CENTER
    bw, bh = L.ORIENT_BAR_SIZE
    patch = warped[cy - bh // 2: cy + bh // 2, cx - bw // 2: cx + bw // 2]
    return float(255 - patch.mean())


def align_form(image_bgr: np.ndarray, max_side: int = 1800) -> AlignResult:
    img = limit_size(image_bgr, max_side)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mask = _marker_mask(gray)
    centers = _find_square_candidates(mask)
    if len(centers) < 4:
        raise AlignmentError(
            f"Köşe işaretçileri bulunamadı ({len(centers)}/4). "
            "Formun dört köşesi de görünür, net ve yeterince aydınlık olmalı."
        )

    quad = order_points(centers)
    quad_area = cv2.contourArea(quad)
    if quad_area < 0.08 * gray.shape[0] * gray.shape[1]:
        raise AlignmentError("Form görüntüde çok küçük. Kameraya biraz daha yaklaşın.")

    dst = np.float32(L.MARKER_CENTERS)
    best = None
    for k in range(4):                                    # 0/90/180/270 derece olasılıkları
        src = np.roll(quad, -k, axis=0)
        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(gray, M, (L.FORM_W, L.FORM_H), flags=cv2.INTER_LINEAR)
        score = _orientation_score(warped)
        if best is None or score > best[0]:
            best = (score, k, warped, src)

    score, k, warped, src = best
    if score < 100:
        raise AlignmentError("Yön çubuğu bulunamadı; form doğru basılmamış ya da köşe kapanmış olabilir.")
    return AlignResult(img, warped, src, k, score, mask)
