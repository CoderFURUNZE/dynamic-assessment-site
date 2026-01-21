from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset, random_split
except Exception as e:  # pragma: no cover
    raise SystemExit(f"Missing torch: {e}. Install torch in the environment you use to train.") from e

try:
    import cv2  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(f"Missing opencv-python: {e}.") from e


LABELS = ["relaxed", "focused", "neutral", "confused", "strained"]
LABEL_TO_ID = {k: i for i, k in enumerate(LABELS)}


@dataclass(frozen=True)
class Sample:
    path: str
    label: int


class FaceCropDataset(Dataset):
    def __init__(self, base_dir: Path, manifest: Path):
        self.base_dir = base_dir
        self.samples: list[Sample] = []
        with manifest.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                label_name = (row.get("label") or "").strip()
                if label_name not in LABEL_TO_ID:
                    continue
                rel = (row.get("path") or "").strip()
                if not rel:
                    continue
                self.samples.append(Sample(path=rel, label=LABEL_TO_ID[label_name]))

        if not self.samples:
            raise RuntimeError("No samples found in manifest.csv")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        s = self.samples[idx]
        p = (self.base_dir / s.path).resolve()
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise RuntimeError(f"Cannot read image: {p}")
        img = cv2.resize(img, (64, 64), interpolation=cv2.INTER_AREA)
        x = img.astype(np.float32) / 255.0
        x = torch.from_numpy(x).unsqueeze(0)  # 1x64x64
        y = torch.tensor(s.label, dtype=torch.long)
        return x, y


class SmallCNN(nn.Module):
    def __init__(self, num_classes: int = 5):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.head = nn.Linear(64, num_classes)

    def forward(self, x):
        x = self.net(x)
        x = x.view(x.size(0), -1)
        return self.head(x)


def main() -> None:
    base = Path(__file__).resolve().parent / "data"
    manifest = base / "manifest.csv"
    out_dir = Path(__file__).resolve().parents[1] / "models"
    out_dir.mkdir(parents=True, exist_ok=True)

    epochs = int(os.environ.get("EPOCHS", "10"))
    batch_size = int(os.environ.get("BATCH_SIZE", "64"))
    lr = float(os.environ.get("LR", "0.001"))
    val_ratio = float(os.environ.get("VAL_RATIO", "0.2"))

    ds = FaceCropDataset(base_dir=base, manifest=manifest)
    val_n = max(1, int(len(ds) * val_ratio))
    train_n = len(ds) - val_n
    train_ds, val_ds = random_split(ds, [train_n, val_n])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SmallCNN(num_classes=len(LABELS)).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    def eval_acc() -> float:
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for x, y in val_loader:
                x = x.to(device)
                y = y.to(device)
                logits = model(x)
                pred = torch.argmax(logits, dim=1)
                correct += int((pred == y).sum().item())
                total += int(y.numel())
        return correct / max(1, total)

    for ep in range(1, epochs + 1):
        model.train()
        losses = []
        for x, y in train_loader:
            x = x.to(device)
            y = y.to(device)
            opt.zero_grad()
            logits = model(x)
            loss = loss_fn(logits, y)
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))
        acc = eval_acc()
        print(f"Epoch {ep}: train_loss={sum(losses)/max(1,len(losses)):.4f} val_acc={acc:.3f}")

    ckpt = {
        "labels": LABELS,
        "state_dict": model.state_dict(),
    }
    ckpt_path = out_dir / "emotion_custom.pt"
    torch.save(ckpt, ckpt_path)
    print(f"Saved checkpoint: {ckpt_path}")

    # ONNX export (optional)
    export = os.environ.get("EXPORT_ONNX", "1") != "0"
    if export:
        onnx_path = out_dir / "emotion_custom.onnx"
        dummy = torch.zeros(1, 1, 64, 64, device=device)
        model.eval()
        try:
            torch.onnx.export(
                model,
                dummy,
                onnx_path,
                input_names=["input"],
                output_names=["logits"],
                opset_version=12,
                dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
            )
            print(f"Exported ONNX: {onnx_path}")
            print("Run backend with:")
            print('  $env:VISION_BACKEND="dl"')
            print(f'  $env:VISION_MODEL_PATH="{onnx_path}"')
        except Exception as e:
            print(f"ONNX export failed: {e!r}")
            print("You can still use the .pt checkpoint, or install extra ONNX deps and retry.")


if __name__ == "__main__":
    main()

