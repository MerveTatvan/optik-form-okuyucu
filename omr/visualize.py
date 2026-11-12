"""Sonuçları düzleştirilmiş form üzerine renkli olarak çizer."""
import cv2
import numpy as np

from . import layout as L
from .grader import AnswerKey, GradeResult
from .reader import ReadResult

GREEN = (0, 160, 0)
RED = (0, 0, 220)
ORANGE = (0, 140, 255)


def _ring(img, center, radius, color, thickness):
    cv2.circle(img, center, radius, color, thickness, cv2.LINE_AA)


def draw_overlay(warped_gray: np.ndarray, read: ReadResult, key: AnswerKey, result: GradeResult) -> np.ndarray:
    img = cv2.cvtColor(warped_gray, cv2.COLOR_GRAY2BGR)
    r = L.BUBBLE_RADIUS + 4

    for item in result.items:
        q = item.number - 1
        if item.correct in L.OPTIONS:
            ci = L.OPTIONS.index(item.correct)
            if item.status == "correct":
                _ring(img, L.answer_bubble_center(q, ci), r, GREEN, 3)
            else:
                _ring(img, L.answer_bubble_center(q, ci), r, GREEN, 1)     # doğru cevabı ince yeşil göster
        if item.status == "wrong":
            for oi in read.marked[q]:
                _ring(img, L.answer_bubble_center(q, oi), r, RED, 3)
        elif item.status == "multiple":
            for oi in read.marked[q]:
                _ring(img, L.answer_bubble_center(q, oi), r, ORANGE, 3)

    # Öğrenci numarası okunan balonlar
    for pos, ch in enumerate(read.student_id):
        if ch.isdigit():
            _ring(img, L.id_bubble_center(pos, int(ch)), L.BUBBLE_RADIUS + 3, GREEN, 2)

    # Sağ üstteki "PUAN" kutusuna özet yaz
    x0, y0, x1, y1 = 560, 420, 930, 560
    cv2.rectangle(img, (x0 + 2, y0 + 2), (x1 - 2, y1 - 2), (255, 255, 255), -1)
    f = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, f"No: {result.student_id}", (x0 + 15, y0 + 35), f, 0.75, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(img, f"PUAN: {result.score:g} / {result.max_score:g}", (x0 + 15, y0 + 78), f, 0.9, (150, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(
        img,
        f"D:{result.n_correct}  Y:{result.n_wrong}  B:{result.n_blank}  Cift:{result.n_multiple}",
        (x0 + 15, y0 + 118), f, 0.6, (0, 0, 0), 2, cv2.LINE_AA,
    )
    return img


def draw_markers(image_bgr: np.ndarray, markers: np.ndarray) -> np.ndarray:
    img = image_bgr.copy()
    pts = markers.astype(int)
    cv2.polylines(img, [pts.reshape(-1, 1, 2)], True, (0, 200, 0), 3, cv2.LINE_AA)
    for name, (x, y) in zip(("SolUst", "SagUst", "SagAlt", "SolAlt"), pts):
        cv2.circle(img, (int(x), int(y)), 10, (0, 0, 255), -1)
        cv2.putText(img, name, (int(x) + 12, int(y) - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
    return img
