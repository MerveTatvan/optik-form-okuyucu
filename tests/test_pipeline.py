"""Uçtan uca testler: sahte (simüle) fotoğraflar üretip okunan sonucu gerçek değerle karşılaştırır."""
import numpy as np
import pytest

from omr import layout as L
from omr.align import AlignmentError, align_form
from omr.formgen import draw_blank_form, fill_form, random_answers, simulate_photo
from omr.grader import AnswerKey, grade, load_answer_key
from omr.pipeline import process_image
from omr.reader import read_form

KEY = "ABCDEABCDEBCDEACDEABEDCBAEDCBADCBAEBCDAE"


@pytest.fixture(scope="module")
def blank():
    return draw_blank_form(2)


def expected(answers):
    out = []
    for a in answers:
        out.append(None if a == "" else a if len(a) == 1 else "*")
    return out


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("rotate_k", [0, 1, 2, 3])
def test_read_matches_ground_truth(blank, seed, rotate_k):
    rng = np.random.default_rng(seed)
    answers = random_answers(KEY, rng, p_correct=0.6, p_blank=0.1, p_multi=0.1)
    sid = "".join(str(d) for d in rng.integers(0, 10, L.ID_DIGITS))
    photo = simulate_photo(fill_form(blank, answers, sid, 2, seed), seed=seed, rotate_k=rotate_k)

    al = align_form(photo)
    assert al.rotation in range(4)
    read = read_form(al.warped)
    assert read.answers == expected(answers)
    assert read.student_id == sid


def test_grading_math():
    from omr.reader import ReadResult
    answers = list("ABCDE") + [None, "*"] + ["A"] * 3
    read = ReadResult(answers, [], np.zeros((1, 1)), "12345678", np.zeros((1, 1)))
    key = AnswerKey(list("ABCDE") + list("AAAAA"), points_per_question=2, wrong_penalty=0.25)
    res = grade(read, key)
    # 5 doğru + 3 doğru (A,A,A son üç) = 8; 0 yanlış; 1 boş; 1 çift
    assert (res.n_correct, res.n_wrong, res.n_blank, res.n_multiple) == (8, 0, 1, 1)
    assert res.score == 16

    key2 = AnswerKey(list("BBBBB"), points_per_question=1, wrong_penalty=0.25)
    read2 = ReadResult(["A", "A", "A", "A", "B"], [], np.zeros((1, 1)), "00000000", np.zeros((1, 1)))
    assert grade(read2, key2).score == 0.0 + max(0, 1 - 4 * 0.25)


def test_cancelled_question_is_free_point():
    from omr.reader import ReadResult
    read = ReadResult([None, "A"], [], np.zeros((1, 1)), "00000000", np.zeros((1, 1)))
    res = grade(read, AnswerKey(["X", "B"], points_per_question=1))
    assert res.n_correct == 1 and res.n_wrong == 1


def test_invalid_key_rejected():
    with pytest.raises(ValueError):
        AnswerKey(["A", "Z"])


def test_blank_image_raises_alignment_error():
    with pytest.raises(AlignmentError):
        align_form(np.full((800, 600, 3), 255, np.uint8))


def test_process_image_with_key_file(blank, tmp_path):
    key = load_answer_key("data/answer_key.json")
    answers = list(key.answers)
    photo = simulate_photo(fill_form(blank, answers, "20240001", 2, 1), seed=1)
    res, read, _, overlay = process_image(photo, key, debug_dir=tmp_path)
    assert res.n_correct == 40 and res.score == 100.0
    assert overlay.shape[:2] == (L.FORM_H, L.FORM_W)
    assert (tmp_path / "3_hizalanmis_form.png").exists()


def test_light_pencil_and_low_resolution(blank):
    """Soluk kurşun kalem + düşük çözünürlüklü fotoğraf da doğru okunmalı."""
    import cv2
    rng = np.random.default_rng(5)
    answers = random_answers(KEY, rng, p_correct=0.6, p_blank=0.1, p_multi=0.05)
    filled = fill_form(blank, answers, "12345678", 2, 5)
    new_marks = (filled < 100) & (blank > 200)
    filled[new_marks] = rng.integers(140, 170, size=new_marks.sum()).astype(np.uint8)   # soluk gri
    photo = simulate_photo(filled, seed=5)
    photo = cv2.resize(photo, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)       # ~650x900
    read = read_form(align_form(photo).warped)
    assert read.answers == expected(answers)
