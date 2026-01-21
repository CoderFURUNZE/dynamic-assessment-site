from __future__ import annotations

from pathlib import Path
from typing import Iterable

try:
    import torch  # type: ignore
except Exception:  # pragma: no cover
    torch = None  # type: ignore
from sqlmodel import Session, desc, select

from app.db.models import PracticeAttempt, Question


MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "models" / "reco_mlp.pt"


if torch is not None:
    class MLP(torch.nn.Module):
        def __init__(self, input_dim: int):
            super().__init__()
            self.net = torch.nn.Sequential(
                torch.nn.Linear(input_dim, 32),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.1),
                torch.nn.Linear(32, 16),
                torch.nn.ReLU(),
                torch.nn.Linear(16, 1),
            )

        def forward(self, x):
            return self.net(x)
else:  # pragma: no cover
    MLP = object  # type: ignore


def _load_model() -> tuple[torch.nn.Module, torch.device] | None:
    if torch is None:
        return None
    if not MODEL_PATH.exists():
        return None
    try:
        data = torch.load(MODEL_PATH, map_location="cpu")
        input_dim = int(data.get("input_dim", 5))
        model = MLP(input_dim=input_dim)
        model.load_state_dict(data.get("state_dict", {}))
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        return model, device
    except Exception:
        return None


def _user_features(session: Session, user_id: int, kp_id: int, window: int = 10) -> tuple[float, float, float]:
    rows = session.exec(
        select(PracticeAttempt)
        .where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id == kp_id)
        .order_by(desc(PracticeAttempt.created_at))
        .limit(window)
    ).all()
    if not rows:
        return 0.0, 0.0, 0.0
    correct_rate = sum(1 for r in rows if r.correct) / len(rows)
    recent_attempts = min(10.0, float(len(rows))) / 10.0
    avg_duration = sum(r.duration_ms for r in rows) / len(rows)
    avg_duration_scaled = min(60000.0, float(avg_duration)) / 60000.0
    return correct_rate, recent_attempts, avg_duration_scaled


def _question_feature(question: Question, user_feats: tuple[float, float, float]) -> torch.Tensor:
    if torch is None:  # pragma: no cover
        raise RuntimeError("torch not available")
    correct_rate, recent_attempts, avg_duration_scaled = user_feats
    difficulty = float(question.difficulty)
    type_is_blank = 1.0 if question.type == "blank" else 0.0
    return torch.tensor(
        [difficulty, type_is_blank, correct_rate, recent_attempts, avg_duration_scaled], dtype=torch.float32
    )


def predict_one(
    session: Session, *, user_id: int, kp_id: int, question: Question
) -> float | None:
    if torch is None:
        return None
    loaded = _load_model()
    if loaded is None:
        return None
    model, device = loaded
    feats = _user_features(session, user_id=user_id, kp_id=kp_id)
    x = _question_feature(question, feats).unsqueeze(0).to(device)
    with torch.no_grad():
        prob = torch.sigmoid(model(x)).cpu().item()
    return float(prob)


def score_recent(
    session: Session, *, user_id: int, kp_id: int, limit: int = 10
) -> list[float] | None:
    if torch is None:
        return None
    loaded = _load_model()
    if loaded is None:
        return None
    model, device = loaded
    feats = _user_features(session, user_id=user_id, kp_id=kp_id)
    rows = session.exec(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id == kp_id)
        .order_by(desc(PracticeAttempt.created_at))
        .limit(limit)
    ).all()
    if not rows:
        return []
    q_list = [q for _, q in rows if q is not None]
    xs = torch.stack([_question_feature(q, feats) for q in q_list]).to(device)
    with torch.no_grad():
        probs = torch.sigmoid(model(xs)).cpu().numpy().reshape(-1).tolist()
    # return chronological (oldest -> newest)
    return list(reversed([float(p) for p in probs]))


def score_questions(
    session: Session, *, user_id: int, kp_id: int, questions: Iterable[Question]
) -> list[tuple[float, Question]] | None:
    if torch is None:
        return None
    loaded = _load_model()
    if loaded is None:
        return None
    model, device = loaded
    feats = _user_features(session, user_id=user_id, kp_id=kp_id)
    if feats is None:
        feats = (0.0, 0.0, 0.0)

    q_list = list(questions)
    if not q_list:
        return []
    xs = torch.stack([_question_feature(q, feats) for q in q_list]).to(device)
    with torch.no_grad():
        probs = torch.sigmoid(model(xs)).cpu().numpy().reshape(-1).tolist()
    return list(zip([float(p) for p in probs], q_list))
