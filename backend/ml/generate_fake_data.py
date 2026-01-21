import json
import math
import random
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AttemptRow:
    user_id: int
    kp_id: int
    question_id: int
    difficulty: float
    qtype: str
    is_correct: int
    duration_ms: int
    timestamp: str


def _clip(x: float, lo: float = 0.05, hi: float = 0.95) -> float:
    return max(lo, min(hi, x))


def generate_attempts(num_users: int = 30, seq_len: int = 80) -> list[AttemptRow]:
    rows: list[AttemptRow] = []
    for user_id in range(1, num_users + 1):
        base_skill = random.uniform(0.35, 0.75)
        kp_skill = {kp: _clip(base_skill + random.uniform(-0.15, 0.15), 0.05, 0.95) for kp in range(1, 13)}
        for i in range(seq_len):
            kp_id = random.randint(1, 12)
            # Difficulty distribution: more medium questions.
            difficulty = _clip(random.gauss(0.45, 0.18), 0.1, 0.9)
            qtype = "blank" if random.random() < 0.4 else "mcq"
            # Slight learning effect over time.
            learn_boost = min(0.12, i / seq_len * 0.12)
            skill = _clip(kp_skill[kp_id] + learn_boost, 0.05, 0.95)
            prob = skill - (difficulty - 0.5) * 0.9
            prob = _clip(prob, 0.05, 0.95)
            is_correct = 1 if random.random() < prob else 0
            # Harder or wrong answers tend to take longer.
            base_time = 9000 + int(difficulty * 12000)
            if is_correct == 0:
                base_time += 4000
            duration_ms = int(_clip(random.gauss(base_time, 2500), 5000, 40000))
            rows.append(
                AttemptRow(
                    user_id=user_id,
                    kp_id=kp_id,
                    question_id=random.randint(1, 300),
                    difficulty=round(difficulty, 2),
                    qtype=qtype,
                    is_correct=is_correct,
                    duration_ms=duration_ms,
                    timestamp=f"2026-01-19T10:{i:02d}:00",
                )
            )
    return rows


def gen_sequences(rows: list[AttemptRow]) -> None:
    out = DATA_DIR / "sequence.jsonl"
    by_user: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_user[r.user_id].append(
            {
                "kp_id": r.kp_id,
                "question_id": r.question_id,
                "difficulty": r.difficulty,
                "type": r.qtype,
                "is_correct": r.is_correct,
                "duration_ms": r.duration_ms,
                "timestamp": r.timestamp,
            }
        )
    with out.open("w", encoding="utf-8") as f:
        for user_id, interactions in by_user.items():
            f.write(json.dumps({"user_id": user_id, "interactions": interactions}, ensure_ascii=False) + "\n")


def gen_samples(rows: list[AttemptRow], window: int = 10) -> None:
    out = DATA_DIR / "samples.csv"
    header = [
        "user_id",
        "kp_id",
        "question_id",
        "difficulty",
        "type",
        "recent_correct_rate",
        "recent_attempts",
        "recent_avg_duration_ms",
        "is_correct",
    ]
    history: dict[tuple[int, int], deque] = {}
    with out.open("w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            key = (r.user_id, r.kp_id)
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

            row = [
                str(r.user_id),
                str(r.kp_id),
                str(r.question_id),
                f"{r.difficulty:.2f}",
                r.qtype,
                f"{recent_correct_rate:.3f}",
                str(recent_attempts),
                str(int(recent_avg_duration_ms)),
                str(r.is_correct),
            ]
            f.write(",".join(row) + "\n")
            hist.append({"correct": bool(r.is_correct), "duration_ms": r.duration_ms})


def main() -> None:
    random.seed(42)
    rows = generate_attempts()
    gen_sequences(rows)
    gen_samples(rows)
    print("Fake data generated in backend/ml/data")


if __name__ == "__main__":
    main()
