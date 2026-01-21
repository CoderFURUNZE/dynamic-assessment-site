from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import cv2  # type: ignore
    import mediapipe as mp  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(f"Missing dependencies: {e}. Install opencv-python + mediapipe.") from e


@dataclass(frozen=True)
class LabelDef:
    key: str
    label: str
    difficulty: float


LABELS: list[LabelDef] = [
    LabelDef("1", "relaxed", 0.15),
    LabelDef("2", "focused", 0.35),
    LabelDef("3", "neutral", 0.50),
    LabelDef("4", "confused", 0.70),
    LabelDef("5", "strained", 0.90),
]


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _crop_face(frame_bgr: np.ndarray, det: mp.framework.formats.detection_pb2.Detection) -> np.ndarray | None:
    h, w = frame_bgr.shape[:2]
    box = det.location_data.relative_bounding_box
    x1 = int(max(0.0, box.xmin) * w)
    y1 = int(max(0.0, box.ymin) * h)
    x2 = int(min(1.0, box.xmin + box.width) * w)
    y2 = int(min(1.0, box.ymin + box.height) * h)

    pad_x = int(0.12 * (x2 - x1))
    pad_y = int(0.18 * (y2 - y1))
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame_bgr[y1:y2, x1:x2]


def main() -> None:
    """
    Capture a small, privacy-minded dataset for training a custom expression model.

    - Only saves face crops (64x64 grayscale), NOT full frames / video.
    - You must label frames manually by pressing keys.

    Keys:
      1 relaxed, 2 focused, 3 neutral, 4 confused, 5 strained
      s save current frame (uses last selected label)
      q quit
    """

    print("=== Collect Dataset (No full-frame saving) ===")
    print("This tool saves ONLY 64x64 face crops for training.")
    print("Press keys: " + " | ".join([f"{d.key}={d.label}" for d in LABELS]))
    print("Press s=save, q=quit")

    base = Path(__file__).resolve().parent / "data"
    img_dir = base / "raw"
    _ensure_dir(img_dir)
    for d in LABELS:
        _ensure_dir(img_dir / d.label)

    manifest = base / "manifest.csv"
    new_file = not manifest.exists()
    f = manifest.open("a", encoding="utf-8", newline="")
    writer = csv.DictWriter(f, fieldnames=["path", "label", "difficulty", "ts_ms"])
    if new_file:
        writer.writeheader()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("Cannot open camera")

    detector = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6)

    selected: LabelDef | None = None
    last_saved = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out = detector.process(rgb)
            det = out.detections[0] if out.detections else None

            hud = frame.copy()
            if det is not None:
                h, w = frame.shape[:2]
                box = det.location_data.relative_bounding_box
                x1 = int(max(0.0, box.xmin) * w)
                y1 = int(max(0.0, box.ymin) * h)
                x2 = int(min(1.0, box.xmin + box.width) * w)
                y2 = int(min(1.0, box.ymin + box.height) * h)
                cv2.rectangle(hud, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label_text = selected.label if selected else "(none)"
            cv2.putText(hud, f"Label: {label_text}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
            cv2.putText(hud, "1-5 select | s save | q quit", (12, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            if last_saved:
                cv2.putText(hud, f"Saved: {last_saved}", (12, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("collect_dataset (face crops only)", hud)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key in [ord(d.key) for d in LABELS]:
                selected = next(d for d in LABELS if ord(d.key) == key)
            if key == ord("s"):
                if selected is None:
                    continue
                if det is None:
                    continue
                face = _crop_face(frame, det)
                if face is None:
                    continue
                gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
                img = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
                ts = int(time.time() * 1000)
                out_path = img_dir / selected.label / f"{ts}.png"
                cv2.imwrite(str(out_path), img)
                writer.writerow({"path": str(out_path.relative_to(base)), "label": selected.label, "difficulty": selected.difficulty, "ts_ms": ts})
                f.flush()
                last_saved += 1
    finally:
        f.close()
        cap.release()
        cv2.destroyAllWindows()

    print(f"Done. Saved {last_saved} samples.")
    print(f"- manifest: {manifest}")
    print(f"- images: {img_dir}")


if __name__ == "__main__":
    main()

