from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from app.db.models import (  # noqa: E402
    KnowledgePoint,
    LearnerProfileSnapshot,
    LearningBehaviorEvent,
    Mastery,
    PracticeAttempt,
    Question,
    Quiz,
    QuizAttempt,
    RecommendationLog,
    ReviewSchedule,
    User,
    VideoProgress,
    QuizItem,
)
from app.db.session import engine  # noqa: E402
from backend.scripts.seed_midterm_three_student_paths import seed as seed_three_student_paths  # noqa: E402


BASE_URL = "http://127.0.0.1:8000/api"
SUBJECT = "高等数学"
GRADE = "通用"


@dataclass
class SmokeResult:
    name: str
    ok: bool
    detail: str = ""


class SmokeFailure(RuntimeError):
    pass


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def request_json(
    method: str,
    path: str,
    *,
    token: str | None = None,
    expected_status: int = 200,
    timeout: int = 20,
    **kwargs: Any,
) -> Any:
    headers = dict(kwargs.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=timeout, **kwargs)
    if response.status_code != expected_status:
        raise SmokeFailure(
            f"{method} {path} expected {expected_status}, got {response.status_code}: {response.text[:500]}"
        )
    if not response.content:
        return None
    return response.json()


def login(username: str, password: str = "123456") -> str:
    data = request_json("POST", "/auth/login", json={"username": username, "password": password})
    token = str(data.get("access_token") or "")
    assert_true(bool(token), f"{username} login did not return token")
    return token


def kp_by_code(code: str) -> KnowledgePoint:
    with Session(engine) as session:
        kp = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code)).first()
        assert_true(kp is not None and kp.id is not None, f"knowledge point missing: {code}")
        return kp


def user_by_username(username: str) -> User:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        assert_true(user is not None and user.id is not None, f"user missing: {username}")
        return user


def question_answer(question_id: int) -> str:
    with Session(engine) as session:
        question = session.get(Question, int(question_id))
        assert_true(question is not None, f"question missing: {question_id}")
        return str(question.answer)


def wrong_answer_for(question: dict) -> str:
    answer = question_answer(int(question["id"]))
    for option in question.get("options") or []:
        if str(option).strip().upper() != answer.strip().upper():
            return str(option)
    return f"{answer}__wrong"


def quiz_answers(quiz: dict) -> list[dict]:
    item_ids = [int(item["id"]) for item in quiz.get("items", [])]
    with Session(engine) as session:
        rows = {
            int(row.id): row.answer
            for row in session.exec(select(QuizItem).where(QuizItem.id.in_(item_ids))).all()
            if row.id is not None
        }
    return [{"item_id": int(item["id"]), "answer": rows[int(item["id"])]} for item in quiz["items"]]


def first_unfinished(data: dict) -> dict:
    overlay_by_id = {int(item["kp_id"]): item for item in data.get("overlay", [])}
    for kp in data.get("base", {}).get("kps", []):
        overlay = overlay_by_id.get(int(kp["id"]), {})
        mastery = float(overlay.get("mastery") or 0)
        status = str(overlay.get("status") or "not_started")
        if mastery < 0.7 and status != "mastered":
            return kp
    raise SmokeFailure("no unfinished visible KP found")


def test_student_path_recommendations() -> list[SmokeResult]:
    expected = {
        "student_demo_1": ("HM-MID-02", "HM-MID-02"),
        "student_demo_2": ("HM-MID-03", "HM-MID-03"),
        "student_demo_3": ("HM-MID-B3", "HM-MID-B3"),
    }
    results: list[SmokeResult] = []
    for username, (expected_first, expected_target) in expected.items():
        token = login(username)
        courses = request_json("GET", "/graph/courses", token=token)
        titles = [item.get("title") for item in courses]
        assert_true(SUBJECT in titles, f"{username} cannot see {SUBJECT}; courses={titles}")

        graph = request_json("GET", "/graph/map", token=token, params={"subject": SUBJECT, "grade": GRADE})
        visible_codes = [item["code"] for item in graph.get("base", {}).get("kps", [])]
        current = first_unfinished(graph)
        assert_true(
            current["code"] == expected_first,
            f"{username} first unfinished expected {expected_first}, got {current['code']} visible={visible_codes}",
        )

        reco = request_json("GET", "/reco", token=token, params={"kp_id": int(current["id"])}, timeout=30)
        target = reco.get("target_kp", {})
        assert_true(
            target.get("code") == expected_target,
            f"{username} recommendation target expected {expected_target}, got {target}",
        )
        assert_true(bool(reco.get("reason_summary")), f"{username} recommendation missing reason_summary")
        results.append(
            SmokeResult(
                name=f"path:{username}",
                ok=True,
                detail=f"visible={visible_codes}; first={current['code']}; target={target.get('code')}",
            )
        )
    return results


def test_practice_and_data_collection() -> list[SmokeResult]:
    username = "student_demo_1"
    token = login(username)
    kp = kp_by_code("HM-MID-01")
    user = user_by_username(username)

    request_json("POST", "/practice/reset", token=token, json={"kp_id": int(kp.id)})
    questions = request_json("GET", "/practice/questions", token=token, params={"kp_id": int(kp.id)})
    assert_true(len(questions) > 0, "practice questions missing for HM-MID-01")
    question = questions[0]
    next_item = request_json("GET", "/practice/next", token=token, params={"kp_id": int(kp.id)})
    assert_true(next_item.get("done") is False and next_item.get("question"), "practice next did not return a question")

    wrong = request_json(
        "POST",
        "/practice/submit",
        token=token,
        json={
            "question_id": int(question["id"]),
            "kp_id": int(kp.id),
            "answer": wrong_answer_for(question),
            "self_report": "guess",
            "duration_ms": 42000,
        },
    )
    assert_true(wrong.get("correct") is False, "wrong answer should be marked incorrect")
    wrong_list = request_json("GET", "/practice/wrong", token=token, params={"kp_id": int(kp.id)})
    assert_true(any(int(item["question_id"]) == int(question["id"]) for item in wrong_list), "wrong list missing submitted question")

    right = request_json(
        "POST",
        "/practice/submit",
        token=token,
        json={
            "question_id": int(question["id"]),
            "kp_id": int(kp.id),
            "answer": question_answer(int(question["id"])),
            "self_report": "sure",
            "duration_ms": 36000,
        },
    )
    assert_true(right.get("correct") is True, "correct answer should be marked correct")
    history = request_json("GET", "/practice/history", token=token, params={"kp_id": int(kp.id)})
    stats = request_json("GET", "/practice/stats", token=token, params={"kp_id": int(kp.id)})
    review = request_json("GET", "/practice/review/queue", token=token)
    assert_true(int(history.get("total") or 0) >= 2, "practice history did not record both attempts")
    assert_true(int(stats.get("total") or 0) >= 2, "practice stats did not include submitted attempts")
    assert_true("items" in review and "total" in review, "review queue shape is invalid")

    with Session(engine) as session:
        attempts = session.exec(
            select(PracticeAttempt).where(PracticeAttempt.user_id == int(user.id), PracticeAttempt.kp_id == int(kp.id))
        ).all()
        events = session.exec(
            select(LearningBehaviorEvent).where(
                LearningBehaviorEvent.user_id == int(user.id),
                LearningBehaviorEvent.kp_id == int(kp.id),
                LearningBehaviorEvent.event_type == "practice_submit",
            )
        ).all()
        mastery = session.exec(select(Mastery).where(Mastery.user_id == int(user.id), Mastery.kp_id == int(kp.id))).first()
        schedules = session.exec(
            select(ReviewSchedule).where(ReviewSchedule.user_id == int(user.id), ReviewSchedule.kp_id == int(kp.id))
        ).all()
    assert_true(len(attempts) >= 2, "PracticeAttempt rows were not persisted")
    assert_true(len(events) >= 2, "practice_submit behavior events were not persisted")
    assert_true(mastery is not None, "Mastery row missing after practice submit")
    assert_true(len(schedules) >= 1, "ReviewSchedule row missing after wrong submit")
    return [
        SmokeResult(
            name="practice:submit-history-stats-review",
            ok=True,
            detail=f"attempts={len(attempts)} events={len(events)} mastery={float(mastery.value):.2f}",
        )
    ]


def test_content_learning_collection() -> list[SmokeResult]:
    username = "student_demo_1"
    token = login(username)
    kp = kp_by_code("HM-MID-01")
    user = user_by_username(username)

    resources = request_json("GET", "/content/resources", token=token, params={"kp_id": int(kp.id)})
    assert_true(len(resources) > 0, "learning resources missing for HM-MID-01")
    video = next((item for item in resources if item.get("type") == "video"), resources[0])
    request_json("POST", "/content/resource/visit", token=token, json={"kp_id": int(kp.id), "resource_id": int(video["id"]), "action": "visit"})
    progress = {}
    for step in range(5):
        progress = request_json(
            "POST",
            "/content/video/progress",
            token=token,
            json={
                "kp_id": int(kp.id),
                "resource_id": int(video["id"]),
                "position_seconds": 120 * (step + 1),
                "duration_seconds": 600,
                "watched_delta_seconds": 120,
                "playback_rate": 4,
            },
        )
    assert_true(progress.get("completed") is True, "video progress should mark short demo video completed")

    quiz = request_json("GET", f"/content/quiz/{int(kp.id)}", token=token)
    assert_true(len(quiz.get("items", [])) > 0, "quiz items missing for HM-MID-01")
    answers = quiz_answers(quiz)
    quiz_submit = request_json(
        "POST",
        "/content/quiz/submit",
        token=token,
        json={"quiz_id": int(quiz["quiz_id"]), "kp_id": int(kp.id), "answers": answers, "duration_ms": 90000},
    )
    assert_true(quiz_submit.get("passed") is True, f"quiz should pass with correct answers: {quiz_submit}")

    with Session(engine) as session:
        video_rows = session.exec(
            select(VideoProgress).where(VideoProgress.user_id == int(user.id), VideoProgress.kp_id == int(kp.id))
        ).all()
        quiz_rows = session.exec(
            select(QuizAttempt).where(QuizAttempt.user_id == int(user.id), QuizAttempt.kp_id == int(kp.id))
        ).all()
        behavior_rows = session.exec(
            select(LearningBehaviorEvent).where(
                LearningBehaviorEvent.user_id == int(user.id),
                LearningBehaviorEvent.kp_id == int(kp.id),
            )
        ).all()
        snapshot = session.exec(
            select(LearnerProfileSnapshot).where(
                LearnerProfileSnapshot.user_id == int(user.id),
                LearnerProfileSnapshot.subject == SUBJECT,
                LearnerProfileSnapshot.grade == GRADE,
            )
        ).first()
    event_types = sorted({row.event_type for row in behavior_rows})
    assert_true(any(row.completed for row in video_rows), "completed VideoProgress row missing")
    assert_true(any(float(row.score) >= 1.0 for row in quiz_rows), "passing QuizAttempt row missing")
    assert_true({"resource_visit", "video_progress", "quiz_submit"}.issubset(set(event_types)), f"missing behavior events: {event_types}")
    assert_true(snapshot is not None, "LearnerProfileSnapshot missing after content activity")
    return [
        SmokeResult(
            name="content:resource-video-quiz-collection",
            ok=True,
            detail=f"events={event_types}; quiz_attempts={len(quiz_rows)}; video_rows={len(video_rows)}",
        )
    ]


def test_teacher_observability() -> list[SmokeResult]:
    token = request_json("POST", "/auth/login/admin", json={"username": "teacher_demo", "password": "123456"}).get("access_token")
    assert_true(bool(token), "teacher_demo login failed")
    overview = request_json("GET", "/admin/analytics/overview", token=token, params={"subject": SUBJECT, "grade": GRADE})
    assert_true(isinstance(overview, dict), "analytics overview should return object")
    student = user_by_username("student_demo_1")
    detail = request_json(
        "GET",
        "/admin/analytics/student-detail",
        token=token,
        params={"subject": SUBJECT, "grade": GRADE, "user_id": int(student.id)},
    )
    assert_true(isinstance(detail.get("mastery_map"), list), "student detail missing mastery_map")
    with Session(engine) as session:
        reco_count = len(
            session.exec(
                select(RecommendationLog).where(RecommendationLog.user_id == int(student.id), RecommendationLog.subject == SUBJECT)
            ).all()
        )
    assert_true(reco_count > 0, "RecommendationLog missing for teacher observability")
    return [SmokeResult(name="teacher:analytics-student-detail", ok=True, detail=f"recommendation_logs={reco_count}")]


def run_packet() -> list[SmokeResult]:
    # Reset the demo fixture so the smoke test starts from known data.
    seed_three_student_paths()
    results: list[SmokeResult] = []
    results.extend(test_student_path_recommendations())
    results.extend(test_practice_and_data_collection())
    results.extend(test_content_learning_collection())
    results.extend(test_teacher_observability())
    # Restore the demo fixture for the presentation after mutating smoke actions.
    seed_three_student_paths()
    return results


def main() -> int:
    try:
        request_json("GET", "/graph/courses", expected_status=401, timeout=5)
    except requests.RequestException as exc:
        print(f"[FAIL] backend is not reachable at {BASE_URL}: {exc}")
        return 2
    except SmokeFailure:
        # 401 is expected without token; any JSON response means the server is up.
        pass

    try:
        results = run_packet()
    except Exception as exc:
        print(f"[FAIL] smoke packet failed: {exc}")
        return 1

    print("\nMidterm student flow smoke packet passed")
    for item in results:
        print(f"[PASS] {item.name}: {item.detail}")
    print(
        "\nCovered modules: auth, student course graph, personalized recommendation, "
        "practice submit/history/stats/wrong/review, resource visit, video progress, quiz submit, "
        "behavior collection, mastery/profile persistence, teacher analytics visibility."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
