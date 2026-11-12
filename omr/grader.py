"""Cevap anahtarı ve puanlama."""
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import layout as L
from .reader import ReadResult

_COUNTERS = {"correct": "n_correct", "wrong": "n_wrong", "blank": "n_blank", "multiple": "n_multiple"}
CANCELLED = "X"   # Anahtarda 'X' = iptal edilen soru, herkese doğru sayılır


@dataclass
class AnswerKey:
    answers: list
    exam_name: str = ""
    points_per_question: float = 0.0     # 0 ise toplam 100 puana göre otomatik hesaplanır
    wrong_penalty: float = 0.0           # Yanlış başına düşülecek "doğru oranı" (0.25 = 4 yanlış 1 doğruyu götürür)

    def __post_init__(self):
        self.answers = [str(a).strip().upper() for a in self.answers]
        if not 1 <= len(self.answers) <= L.NUM_QUESTIONS:
            raise ValueError(f"Cevap anahtarında 1-{L.NUM_QUESTIONS} soru olmalı, {len(self.answers)} bulundu.")
        bad = [a for a in self.answers if a not in L.OPTIONS and a != CANCELLED]
        if bad:
            raise ValueError(f"Cevap anahtarında geçersiz değer(ler): {sorted(set(bad))}. İzinli: {L.OPTIONS} veya X.")
        if not self.points_per_question:
            self.points_per_question = 100.0 / len(self.answers)

    @property
    def n(self) -> int:
        return len(self.answers)


def load_answer_key(path) -> AnswerKey:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    answers = data["answers"]
    return AnswerKey(
        answers=list(answers) if isinstance(answers, str) else answers,
        exam_name=data.get("exam_name", ""),
        points_per_question=data.get("points_per_question") or 0.0,
        wrong_penalty=data.get("wrong_penalty") or 0.0,
    )


@dataclass
class QuestionResult:
    number: int                # 1 tabanlı
    marked: object             # 'A'..'E' | None | '*'
    correct: str
    status: str                # 'correct' | 'wrong' | 'blank' | 'multiple'


@dataclass
class GradeResult:
    student_id: str
    items: list = field(default_factory=list)
    n_correct: int = 0
    n_wrong: int = 0
    n_blank: int = 0
    n_multiple: int = 0
    score: float = 0.0
    max_score: float = 0.0


def grade(read: ReadResult, key: AnswerKey) -> GradeResult:
    res = GradeResult(student_id=read.student_id, max_score=round(key.n * key.points_per_question, 2))
    for i in range(key.n):
        marked, correct = read.answers[i], key.answers[i]
        if correct == CANCELLED:
            status = "correct"
        elif marked is None:
            status = "blank"
        elif marked == "*":
            status = "multiple"
        elif marked == correct:
            status = "correct"
        else:
            status = "wrong"
        res.items.append(QuestionResult(i + 1, marked, correct, status))
        counter = _COUNTERS[status]
        setattr(res, counter, getattr(res, counter) + 1)
    raw = res.n_correct * key.points_per_question - res.n_wrong * key.points_per_question * key.wrong_penalty
    res.score = round(max(0.0, raw), 2)
    return res
