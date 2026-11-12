"""Hizalanmış formdan işaretli şıkları okuma.

Her balon için, balonun iç kısmındaki (basılı çemberin çizgisini hariç tutan) küçük bir
daire içinde "koyu piksel oranı" hesaplanır. Oran eşiğin üstündeyse balon işaretlidir.
"""
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from . import layout as L


@dataclass
class ReaderParams:
    dark_level: int = 190          # Işık düzeltmesi sonrası bu değerin altı "koyu" sayılır (0-255)
    mark_ratio: float = 0.40       # Balonun iç alanının en az bu kadarı koyuysa "işaretli"
    inner_radius: int = 8          # Ölçüm dairesinin yarıçapı (basılı çember çizgisi dışarıda kalsın)


@dataclass
class ReadResult:
    answers: list                  # Her soru için: 'A'..'E' | None (boş) | '*' (birden fazla işaret)
    marked: list                   # Her soru için işaretli şık indeksleri
    ratios: np.ndarray             # (NUM_QUESTIONS, şık sayısı) doluluk oranları
    student_id: str                # Okunamayan hane '?' ile gösterilir
    id_ratios: np.ndarray          # (ID_DIGITS, 10)
    normalized: np.ndarray = field(repr=False, default=None)


def normalize_illumination(gray: np.ndarray) -> np.ndarray:
    """Gölge ve ışık farkını giderir: kağıt ~255, kurşun kalem/mürekkep koyu kalır."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    bg = cv2.GaussianBlur(bg, (0, 0), 8)
    return cv2.divide(gray, np.maximum(bg, 1), scale=255)


def _disk(r: int) -> np.ndarray:
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    return (xx * xx + yy * yy) <= r * r


def _fill_ratio(dark: np.ndarray, cx: int, cy: int, mask: np.ndarray, r: int) -> float:
    patch = dark[cy - r: cy + r + 1, cx - r: cx + r + 1]
    if patch.shape != mask.shape:
        return 0.0
    return float(patch[mask].mean())


def decide(ratios: np.ndarray, mark_ratio: float) -> list:
    """Eşiği geçen şık indekslerini döndürür."""
    return [int(i) for i in np.where(ratios >= mark_ratio)[0]]


def read_form(warped_gray: np.ndarray, params: Optional[ReaderParams] = None) -> ReadResult:
    p = params or ReaderParams()
    norm = normalize_illumination(warped_gray)
    dark = norm < p.dark_level
    mask = _disk(p.inner_radius)
    r = p.inner_radius

    n_opt = len(L.OPTIONS)
    ratios = np.zeros((L.NUM_QUESTIONS, n_opt), dtype=np.float32)
    answers, marked = [], []
    for q in range(L.NUM_QUESTIONS):
        for o in range(n_opt):
            cx, cy = L.answer_bubble_center(q, o)
            ratios[q, o] = _fill_ratio(dark, cx, cy, mask, r)
        idx = decide(ratios[q], p.mark_ratio)
        marked.append(idx)
        answers.append(None if not idx else (L.OPTIONS[idx[0]] if len(idx) == 1 else "*"))

    id_ratios = np.zeros((L.ID_DIGITS, 10), dtype=np.float32)
    digits = []
    for pos in range(L.ID_DIGITS):
        for d in range(10):
            cx, cy = L.id_bubble_center(pos, d)
            id_ratios[pos, d] = _fill_ratio(dark, cx, cy, mask, r)
        idx = decide(id_ratios[pos], p.mark_ratio)
        digits.append(str(idx[0]) if len(idx) == 1 else "?")

    return ReadResult(answers, marked, ratios, "".join(digits), id_ratios, norm)
