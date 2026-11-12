"""Görüntü okuma/yazma.

cv2.imread / cv2.imwrite Windows'ta yolda Türkçe karakter (ç, ğ, ş, ö, ü, ı)
varsa sessizce başarısız olur. Bu yüzden numpy üzerinden okuyup yazıyoruz.
"""
from pathlib import Path

import cv2
import numpy as np

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def imread(path, flags=cv2.IMREAD_COLOR) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, flags) if data.size else None
    if img is None:
        raise ValueError(f"Görüntü okunamadı: {path}")
    return img


def imwrite(path, img: np.ndarray) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(path.suffix or ".png", img)
    if not ok:
        raise ValueError(f"Görüntü yazılamadı: {path}")
    buf.tofile(str(path))


def list_images(folder) -> list[Path]:
    return sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMAGE_EXTS)
