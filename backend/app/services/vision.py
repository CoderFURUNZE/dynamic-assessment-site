from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from collections import deque

import numpy as np

try:
    import cv2
    import mediapipe as mp
except Exception:  # pragma: no cover
    cv2 = None
    mp = None

try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover
    ort = None


@dataclass
class VisionResult:
    label: str
    confidence: float
    difficulty: float


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _bbox_from_facemesh(lm, *, w: int, h: int) -> tuple[int, int, int, int]:
    xs = [p.x for p in lm]
    ys = [p.y for p in lm]
    x1 = int(max(0.0, min(xs)) * w)
    x2 = int(min(1.0, max(xs)) * w)
    y1 = int(max(0.0, min(ys)) * h)
    y2 = int(min(1.0, max(ys)) * h)
    return x1, y1, x2, y2


def _hand_near_head(
    *,
    hand_landmarks,
    face_bbox: tuple[int, int, int, int],
    w: int,
    h: int,
) -> bool:
    """
    Detect "抓耳挠腮/挠头" roughly as: hand landmarks entering ear/head regions.
    This is a weak, heuristic signal (no frame saving).
    """
    x1, y1, x2, y2 = face_bbox
    fw = max(1, x2 - x1)
    fh = max(1, y2 - y1)

    # Regions: left ear, right ear, top of head.
    ear_w = int(0.18 * fw)
    top_h = int(0.22 * fh)

    left = (max(0, x1 - ear_w), max(0, y1 - top_h), min(w, x1 + ear_w), min(h, y2))
    right = (max(0, x2 - ear_w), max(0, y1 - top_h), min(w, x2 + ear_w), min(h, y2))
    top = (max(0, x1), max(0, y1 - top_h), min(w, x2), min(h, y1 + int(0.10 * fh)))

    def in_rect(px: float, py: float, rect: tuple[int, int, int, int]) -> bool:
        rx1, ry1, rx2, ry2 = rect
        return (rx1 <= px <= rx2) and (ry1 <= py <= ry2)

    # Check a few salient landmarks (tips + wrist).
    ids = [0, 4, 8, 12, 16, 20]
    for i in ids:
        p = hand_landmarks.landmark[i]
        px = float(p.x) * w
        py = float(p.y) * h
        if in_rect(px, py, left) or in_rect(px, py, right) or in_rect(px, py, top):
            return True
    return False


def _hand_fidget_without_face(*, hand_landmarks, w: int, h: int) -> bool:
    """
    If face is not detected, we still treat "hand near head" as a weak difficulty signal.

    Heuristic: at least one salient hand point (wrist / fingertips) stays in the upper half
    and close to left/right sides (common ear/head regions in webcam framing).
    """

    def in_region(px: float, py: float) -> bool:
        # upper half + near left/right sides
        if py > 0.55 * h:
            return False
        return (px < 0.35 * w) or (px > 0.65 * w)

    ids = [0, 4, 8, 12, 16, 20]
    hit = 0
    for i in ids:
        p = hand_landmarks.landmark[i]
        px = float(p.x) * w
        py = float(p.y) * h
        if in_region(px, py):
            hit += 1
    return hit >= 2


def _hand_near_mouth(
    *,
    hand_landmarks,
    face_bbox: tuple[int, int, int, int],
    w: int,
    h: int,
) -> bool:
    """
    Detect "吃东西/分心" as hand landmarks around mouth region.
    """
    x1, y1, x2, y2 = face_bbox
    fw = max(1, x2 - x1)
    fh = max(1, y2 - y1)

    mouth = (
        int(x1 + 0.30 * fw),
        int(y1 + 0.55 * fh),
        int(x1 + 0.70 * fw),
        int(y1 + 0.85 * fh),
    )

    def in_rect(px: float, py: float, rect: tuple[int, int, int, int]) -> bool:
        rx1, ry1, rx2, ry2 = rect
        return (rx1 <= px <= rx2) and (ry1 <= py <= ry2)

    ids = [0, 4, 8, 12, 16, 20]
    for i in ids:
        p = hand_landmarks.landmark[i]
        px = float(p.x) * w
        py = float(p.y) * h
        if in_rect(px, py, mouth):
            return True
    return False


class HeuristicExpressionEstimator:
    def __init__(self) -> None:
        if cv2 is None or mp is None:
            raise RuntimeError("Vision dependencies not available: install opencv-python + mediapipe")
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            refine_landmarks=True,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._fidget_hist = deque(maxlen=10)

    def analyze_bgr(self, frame_bgr: np.ndarray) -> VisionResult:
        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        out = self._mesh.process(frame_rgb)
        hands_out = self._hands.process(frame_rgb)
        if not out.multi_face_landmarks:
            # No face, but still treat "抓耳挠腮/挠头" as difficulty if hands suggest it.
            near = False
            if hands_out.multi_hand_landmarks:
                for hlm in hands_out.multi_hand_landmarks:
                    if _hand_fidget_without_face(hand_landmarks=hlm, w=w, h=h):
                        near = True
                        break
            self._fidget_hist.append(1 if near else 0)
            fidget = (sum(self._fidget_hist) / max(1, len(self._fidget_hist))) >= 0.35
            if fidget:
                return VisionResult(label="fidgeting", confidence=0.55, difficulty=0.75)
            return VisionResult(label="no_face", confidence=0.05, difficulty=0.5)

        lm = out.multi_face_landmarks[0].landmark
        face_bbox = _bbox_from_facemesh(lm, w=w, h=h)

        def p(i: int):
            return np.array([lm[i].x * w, lm[i].y * h], dtype=np.float32)

        brow_inner_dist = np.linalg.norm(p(70) - p(300)) / max(w, h)
        left_eye_open = np.linalg.norm(p(159) - p(145)) / max(w, h)
        right_eye_open = np.linalg.norm(p(386) - p(374)) / max(w, h)
        eye_open = (left_eye_open + right_eye_open) / 2.0
        mouth_width = np.linalg.norm(p(61) - p(291)) / max(w, h)
        mouth_open = np.linalg.norm(p(13) - p(14)) / max(w, h)

        frown = _clamp01((0.18 - brow_inner_dist) / 0.10) * 0.6 + _clamp01((0.018 - eye_open) / 0.012) * 0.4
        ease = _clamp01((mouth_width - 0.20) / 0.10) * 0.4 + _clamp01((0.03 - mouth_open) / 0.03) * 0.6

        difficulty = _clamp01(0.65 * frown + 0.35 * (1.0 - ease))
        confidence = _clamp01(0.3 + 0.7 * max(frown, ease))

        if difficulty >= 0.8:
            label = "strained"
        elif difficulty >= 0.65:
            label = "confused"
        elif difficulty >= 0.5:
            label = "neutral"
        elif difficulty >= 0.35:
            label = "focused"
        else:
            label = "relaxed"

        # Optional: detect "吃东西/分心" (hand near mouth) and "抓耳挠腮/挠头".
        near = False
        eat = False
        if hands_out.multi_hand_landmarks:
            for hlm in hands_out.multi_hand_landmarks:
                if _hand_near_mouth(hand_landmarks=hlm, face_bbox=face_bbox, w=w, h=h):
                    eat = True
                if _hand_near_head(hand_landmarks=hlm, face_bbox=face_bbox, w=w, h=h):
                    near = True
                if eat and near:
                    break
        self._fidget_hist.append(1 if near else 0)
        fidget = (sum(self._fidget_hist) / max(1, len(self._fidget_hist))) >= 0.35
        if eat:
            # Prompt only: do not change difficulty/confidence.
            label = "distracted"
        if fidget:
            label = "fidgeting"
            # Keep a mild influence on difficulty; smaller than before.
            difficulty = _clamp01(max(difficulty, 0.62))
            confidence = _clamp01(max(confidence, 0.45))

        return VisionResult(label=label, confidence=confidence, difficulty=difficulty)


class DLEmotionEstimator:
    """
    ONNX FER (emotion) model based estimator.

    Notes:
    - Does NOT save frames.
    - Requires: onnxruntime + opencv-python + mediapipe.
    - Expects a FER-style model that takes 64x64 grayscale.
    """

    # Common FER+ label set (8 classes)
    _labels_ferplus8 = ["neutral", "happy", "surprise", "sad", "angry", "disgust", "fear", "contempt"]
    # Project label set (5 classes) for custom models
    _labels_project5 = ["relaxed", "focused", "neutral", "confused", "strained"]

    def __init__(self, model_path: Path) -> None:
        if cv2 is None or mp is None:
            raise RuntimeError("Vision dependencies not available: install opencv-python + mediapipe")
        if ort is None:
            raise RuntimeError("onnxruntime not available: install onnxruntime")
        if not model_path.exists():
            raise RuntimeError(f"Emotion model not found: {model_path}")

        # Use FaceMesh to obtain a tight face bounding box.
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            refine_landmarks=True,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._fidget_hist = deque(maxlen=10)

        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = max(1, int(os.environ.get("ORT_NUM_THREADS", "2")))
        available = ort.get_available_providers()
        providers: list[str] = []
        if "CUDAExecutionProvider" in available:
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")
        print(f"[vision] ONNX providers available: {available}")
        print(f"[vision] ONNX providers used: {providers}")
        self._sess = ort.InferenceSession(str(model_path), sess_options=sess_opts, providers=providers)
        self._input_name = self._sess.get_inputs()[0].name
        self._input_shape = self._sess.get_inputs()[0].shape

    def _crop_face(self, frame_bgr: np.ndarray) -> np.ndarray | None:
        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        out = self._mesh.process(frame_rgb)
        if not out.multi_face_landmarks:
            return None
        lm = out.multi_face_landmarks[0].landmark
        x1, y1, x2, y2 = _bbox_from_facemesh(lm, w=w, h=h)

        # Expand a bit for stability.
        pad_x = int(0.25 * (x2 - x1))
        pad_y = int(0.30 * (y2 - y1))
        x1 = max(0, x1 - pad_x)
        x2 = min(w, x2 + pad_x)
        y1 = max(0, y1 - pad_y)
        y2 = min(h, y2 + pad_y)

        if x2 <= x1 or y2 <= y1:
            return None
        return frame_bgr[y1:y2, x1:x2]

    def _preprocess(self, face_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        img = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
        x = img.astype(np.float32) / 255.0
        # Try to honor model layout (NCHW vs NHWC) by inspecting input shape.
        shape = self._input_shape or []
        # common: [None, 1, 64, 64]
        if len(shape) == 4 and (shape[1] == 1 or shape[1] is None):
            x = x[None, None, :, :]  # NCHW
        # common: [None, 64, 64, 1]
        elif len(shape) == 4 and (shape[3] == 1 or shape[3] is None):
            x = x[None, :, :, None]  # NHWC
        else:
            # fallback: NCHW
            x = x[None, None, :, :]
        return x

    def analyze_bgr(self, frame_bgr: np.ndarray) -> VisionResult:
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        hands_out = self._hands.process(rgb)

        face = self._crop_face(frame_bgr)
        if face is None:
            # No face crop, still allow fidget signal.
            near = False
            if hands_out.multi_hand_landmarks:
                for hlm in hands_out.multi_hand_landmarks:
                    if _hand_fidget_without_face(hand_landmarks=hlm, w=w, h=h):
                        near = True
                        break
            self._fidget_hist.append(1 if near else 0)
            fidget = (sum(self._fidget_hist) / max(1, len(self._fidget_hist))) >= 0.35
            if fidget:
                return VisionResult(label="fidgeting", confidence=0.55, difficulty=0.75)
            return VisionResult(label="no_face", confidence=0.05, difficulty=0.5)

        mesh_out = self._mesh.process(rgb)
        face_bbox = None
        if mesh_out.multi_face_landmarks:
            face_bbox = _bbox_from_facemesh(mesh_out.multi_face_landmarks[0].landmark, w=w, h=h)

        x = self._preprocess(face)
        y = self._sess.run(None, {self._input_name: x})[0]
        probs = np.asarray(y, dtype=np.float32).reshape(-1)
        if probs.size == 0:
            return VisionResult(label="neutral", confidence=0.1, difficulty=0.5)

        # Ensure probabilities.
        probs = probs - np.max(probs)
        probs = np.exp(probs) / max(1e-9, float(np.sum(np.exp(probs))))

        idx = int(np.argmax(probs))
        conf = float(np.max(probs))

        # Custom 5-class model: outputs directly align with project labels.
        if probs.size == 5:
            label = self._labels_project5[idx] if idx < 5 else "neutral"
            difficulty_map = {
                "relaxed": 0.15,
                "focused": 0.35,
                "neutral": 0.50,
                "confused": 0.70,
                "strained": 0.90,
            }
            difficulty = float(difficulty_map.get(label, 0.5))
            confidence = _clamp01(0.2 + 0.8 * conf)
            return VisionResult(label=label, confidence=confidence, difficulty=difficulty)

        # FER+ (8-class) mapping
        labels = self._labels_ferplus8
        emotion = labels[idx] if idx < len(labels) else "neutral"
        p = {labels[i]: float(probs[i]) for i in range(min(len(labels), probs.size))}
        positive = p.get("happy", 0.0)
        negative = p.get("angry", 0.0) + p.get("sad", 0.0) + p.get("fear", 0.0) + p.get("disgust", 0.0)
        surprise = p.get("surprise", 0.0)

        # Map to difficulty: negative drives up, positive drives down; surprise treated as medium-high.
        difficulty = _clamp01(0.75 * negative + 0.25 * (1.0 - positive) + 0.15 * surprise)

        if emotion in {"angry", "fear", "disgust"} or difficulty >= 0.8:
            label = "strained"
        elif emotion in {"sad"} or difficulty >= 0.65:
            label = "confused"
        elif emotion in {"surprise"}:
            label = "focused" if difficulty < 0.6 else "confused"
        elif emotion in {"happy"} and positive >= 0.45:
            label = "relaxed"
        elif difficulty >= 0.5:
            label = "neutral"
        elif difficulty >= 0.35:
            label = "focused"
        else:
            label = "relaxed"

        confidence = _clamp01(0.2 + 0.8 * conf)

        near = False
        eat = False
        if face_bbox is not None:
            if hands_out.multi_hand_landmarks:
                for hlm in hands_out.multi_hand_landmarks:
                    if _hand_near_mouth(hand_landmarks=hlm, face_bbox=face_bbox, w=w, h=h):
                        eat = True
                    if _hand_near_head(hand_landmarks=hlm, face_bbox=face_bbox, w=w, h=h):
                        near = True
                    if eat and near:
                        break
        else:
            if hands_out.multi_hand_landmarks:
                for hlm in hands_out.multi_hand_landmarks:
                    if _hand_fidget_without_face(hand_landmarks=hlm, w=w, h=h):
                        near = True
                        break
        self._fidget_hist.append(1 if near else 0)
        fidget = (sum(self._fidget_hist) / max(1, len(self._fidget_hist))) >= 0.35
        if eat:
            # Prompt only: do not change difficulty/confidence.
            label = "distracted"
        if fidget:
            label = "fidgeting"
            # Keep a mild influence on difficulty; smaller than before.
            difficulty = _clamp01(max(difficulty, 0.62))
            confidence = _clamp01(max(confidence, 0.45))

        return VisionResult(label=label, confidence=confidence, difficulty=difficulty)


_DL_SINGLETON: DLEmotionEstimator | None = None


class ExpressionEstimator:
    """
    Wrapper that selects the best available estimator.

    - VISION_BACKEND=auto|heuristic|dl (default: auto)
    - VISION_MODEL_PATH=<path to onnx model> (default: backend/ml/models/ferplus.onnx)
    """

    def __init__(self) -> None:
        backend = (os.environ.get("VISION_BACKEND") or "auto").strip().lower()
        model_path = Path(os.environ.get("VISION_MODEL_PATH") or "") if os.environ.get("VISION_MODEL_PATH") else None
        if model_path is None:
            model_path = Path(__file__).resolve().parents[2] / "ml" / "models" / "ferplus.onnx"

        if backend == "heuristic":
            self._impl = HeuristicExpressionEstimator()
            return

        if backend in {"dl", "auto"}:
            global _DL_SINGLETON
            if _DL_SINGLETON is None:
                try:
                    _DL_SINGLETON = DLEmotionEstimator(model_path=model_path)
                except Exception:
                    _DL_SINGLETON = None
            if _DL_SINGLETON is not None:
                self._impl = _DL_SINGLETON
                return
            if backend == "dl":
                raise RuntimeError(
                    f"DL backend requested but not available. Check onnxruntime + model: {model_path}"
                )

        self._impl = HeuristicExpressionEstimator()

    def analyze_bgr(self, frame_bgr: np.ndarray) -> VisionResult:
        return self._impl.analyze_bgr(frame_bgr)


def decode_base64_image_to_bgr(image_b64: str) -> np.ndarray:
    if cv2 is None:
        raise RuntimeError("OpenCV not available")
    raw = base64.b64decode(image_b64)
    data = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image bytes")
    return img
