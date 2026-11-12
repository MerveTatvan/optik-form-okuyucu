"""Uçtan uca akış: görüntü -> hizalama -> okuma -> puanlama -> görselleştirme."""
from pathlib import Path
from typing import Optional, Union

import numpy as np

from . import io
from .align import AlignResult, align_form
from .grader import AnswerKey, GradeResult, grade
from .reader import ReadResult, ReaderParams, read_form
from .visualize import draw_markers, draw_overlay


def process_image(
    source: Union[str, Path, np.ndarray],
    key: AnswerKey,
    params: Optional[ReaderParams] = None,
    debug_dir: Optional[Path] = None,
) -> tuple[GradeResult, ReadResult, AlignResult, np.ndarray]:
    """Döndürür: (puan sonucu, okuma sonucu, hizalama sonucu, renkli sonuç görseli)."""
    img = io.imread(source) if not isinstance(source, np.ndarray) else source
    aligned = align_form(img)
    read = read_form(aligned.warped, params)
    result = grade(read, key)
    overlay = draw_overlay(aligned.warped, read, key, result)

    if debug_dir is not None:
        debug_dir = Path(debug_dir)
        io.imwrite(debug_dir / "1_isaretciler_maske.png", aligned.marker_mask)
        io.imwrite(debug_dir / "2_bulunan_koseler.png", draw_markers(aligned.image, aligned.markers))
        io.imwrite(debug_dir / "3_hizalanmis_form.png", aligned.warped)
        io.imwrite(debug_dir / "4_isik_duzeltilmis.png", read.normalized)
    return result, read, aligned, overlay
