import csv
import json
from collections import defaultdict, deque
from pathlib import Path

from sqlmodel import Session, select

from app.db.models import PracticeAttempt, Question
from app.db.session import engine


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def export_sequences(session: Session) -> None:
    rows = session.exec(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .order_by(PracticeAttempt.user_id, PracticeAttempt.created_at)
    ).all()

    by_user: dict[int, list[dict]] = defaultdict(list)
    for attempt, question in rows:
        qtype = question.type if question is not None else "mcq"
        qdiff = float(question.difficulty) if question is not None else 0.5
        by_user[int(attempt.user_id)].append(
            {
                "kp_id": int(attempt.kp_id),
                "question_id": int(attempt.question_id),
                "difficulty": qdiff,
                "type": qtype,
                "is_correct": int(attempt.correct),
                "duration_ms": int(attempt.duration_ms or 0),
                "timestamp": attempt.created_at.isoformat() if attempt.created_at else "",
            }
        )

    out_path = DATA_DIR / "sequence.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for uid, interactions in by_user.items():
            f.write(json.dumps({"user_id": uid, "interactions": interactions}, ensure_ascii=False) + "\n")


def export_samples(session: Session, window: int = 10) -> None:
    rows = session.exec(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .order_by(PracticeAttempt.user_id, PracticeAttempt.kp_id, PracticeAttempt.created_at)
    ).all()

    history: dict[tuple[int, int], deque] = {}
    out_path = DATA_DIR / "samples.csv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "user_id",
                "kp_id",
                "question_id",
                "difficulty",
                "type",
                "recent_correct_rate",
                "recent_attempts",
                "recent_avg_duration_ms",
                "is_correct",
            ],
        )
        writer.writeheader()

        for attempt, question in rows:
            key = (int(attempt.user_id), int(attempt.kp_id))
            if key not in history:
                history[key] = deque(maxlen=window)
            hist = history[key]

            if hist:
                recent_correct_rate = sum(1 for x in hist if x["correct"]) / len(hist)
                recent_attempts = len(hist)
                recent_avg_duration_ms = sum(x["duration_ms"] for x in hist) / len(hist)
            else:
                recent_correct_rate = 0.0
                recent_attempts = 0
                recent_avg_duration_ms = 0.0

            qtype = question.type if question is not None else "mcq"
            qdiff = float(question.difficulty) if question is not None else 0.5

            writer.writerow(
                {
                    "user_id": int(attempt.user_id),
                    "kp_id": int(attempt.kp_id),
                    "question_id": int(attempt.question_id),
                    "difficulty": qdiff,
                    "type": qtype,
                    "recent_correct_rate": round(recent_correct_rate, 6),
                    "recent_attempts": recent_attempts,
                    "recent_avg_duration_ms": round(recent_avg_duration_ms, 2),
                    "is_correct": int(attempt.correct),
                }
            )

            hist.append({"correct": bool(attempt.correct), "duration_ms": int(attempt.duration_ms or 0)})


def main() -> None:
    with Session(engine) as session:
        export_sequences(session)
        export_samples(session)
    print("Exported: sequence.jsonl, samples.csv")


if __name__ == "__main__":
    main()