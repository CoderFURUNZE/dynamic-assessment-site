# ML Notes

Practice recommendation uses the rule-based recommender by default.

## Export Training Data

After the system has collected practice attempts, run:

```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe -m ml.export_data
```

Generated files:

- `backend/ml/data/sequence.jsonl`
- `backend/ml/data/samples.csv`

## Train Recommendation Model

```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe -m ml.train_mlp
```

Generated file:

- `backend/ml/models/reco_mlp.pt`

The backend automatically falls back to rule-based recommendation when the model or required runtime is unavailable.

## Expression Signal

The expression signal uses the heuristic Mediapipe-based estimator in `backend/app/services/vision.py`.
Deep-learning expression recognition has been removed from this project.

