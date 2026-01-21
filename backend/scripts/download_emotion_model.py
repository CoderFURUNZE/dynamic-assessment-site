from __future__ import annotations

import os
import urllib.request
from pathlib import Path


DEFAULT_URL = (
    "https://github.com/onnx/models/raw/main/validated/vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
)


def main() -> None:
    url = os.environ.get("EMOTION_MODEL_URL") or DEFAULT_URL
    raw_out = (os.environ.get("EMOTION_MODEL_PATH") or "").strip()
    if raw_out:
        out_path = Path(raw_out)
    else:
        out_path = Path(__file__).resolve().parents[1] / "ml" / "models" / "ferplus.onnx"

    # If a directory is provided, write to the default filename inside it.
    if out_path.exists() and out_path.is_dir():
        out_path = out_path / "ferplus.onnx"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        print(f"Model already exists: {out_path}")
        return

    print(f"Downloading model...\n- url: {url}\n- out: {out_path}")
    urllib.request.urlretrieve(url, out_path)  # noqa: S310
    print("Done.")


if __name__ == "__main__":
    main()
