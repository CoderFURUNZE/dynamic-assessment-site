import csv
from pathlib import Path
from typing import List, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split


DATA_DIR = Path(__file__).resolve().parent / "data"
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def to_feature(row: dict) -> List[float]:
    difficulty = float(row["difficulty"])
    qtype = row["type"].strip().lower()
    type_is_blank = 1.0 if qtype == "blank" else 0.0
    recent_correct_rate = float(row["recent_correct_rate"])
    recent_attempts = min(10.0, float(row["recent_attempts"])) / 10.0
    recent_avg_duration_ms = min(60000.0, float(row["recent_avg_duration_ms"])) / 60000.0
    return [difficulty, type_is_blank, recent_correct_rate, recent_attempts, recent_avg_duration_ms]


class SampleDataset(Dataset):
    def __init__(self, rows: List[dict]):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[idx]
        x = torch.tensor(to_feature(row), dtype=torch.float32)
        y = torch.tensor([float(row["is_correct"])], dtype=torch.float32)
        return x, y


class MLP(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.net(x)


def load_rows() -> List[dict]:
    path = DATA_DIR / "samples.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def main() -> None:
    rows = load_rows()
    if len(rows) < 50:
        print("样本数量太少，建议>=50再训练")
        return

    dataset = SampleDataset(rows)
    n_val = max(1, int(len(dataset) * 0.2))
    n_train = len(dataset) - n_val
    train_ds, val_ds = random_split(dataset, [n_train, n_val])

    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=64)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MLP(input_dim=5).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.BCEWithLogitsLoss()

    for epoch in range(1, 11):
        model.train()
        total_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = loss_fn(logits, y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item() * x.size(0)
        train_loss = total_loss / max(1, len(train_ds))

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                probs = torch.sigmoid(model(x))
                preds = (probs >= 0.5).float()
                correct += (preds == y).sum().item()
                total += y.numel()
        val_acc = correct / max(1, total)
        print(f"Epoch {epoch}: train_loss={train_loss:.4f} val_acc={val_acc:.3f}")

    out_path = MODEL_DIR / "reco_mlp.pt"
    torch.save({"input_dim": 5, "state_dict": model.state_dict()}, out_path)
    print(f"Saved model to {out_path}")


if __name__ == "__main__":
    main()