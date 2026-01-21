# ML 推荐（可选）

练习题推荐默认使用“规则推荐”。如果你希望启用深度学习模型评分（MLP），按下面步骤操作。

## 1) 导出真实训练数据

在你用系统做过一些练习题之后（有 `PracticeAttempt` 记录），执行：

```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe -m ml.export_data
```

会生成：
- `backend/ml/data/sequence.jsonl`
- `backend/ml/data/samples.csv`

## 2) 训练模型

```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe -m ml.train_mlp
```

会生成模型文件：
- `backend/ml/models/reco_mlp.pt`

## 3) 后端推理启用/回退

后端会自动检测 `backend/ml/models/reco_mlp.pt` 是否存在：
- 存在且后端环境安装了 `torch`：启用“模型推荐”
- 否则：自动回退到“规则推荐”

## 表情识别（深度学习，可选）

系统默认使用 Mediapipe FaceMesh 的几何启发式来估计“表情困难度”。如果你希望启用深度学习表情模型（ONNX FER+）：

1) 安装依赖（只需要装一次）
```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2) 下载 ONNX 模型到默认路径 `backend/ml/models/ferplus.onnx`
```powershell
cd D:\Project\Learning\backend
.\scripts\download_emotion_model.ps1
```

3) 设置环境变量并启动后端（推荐用 auto）
- `VISION_BACKEND=auto`：有模型就用 DL，没有就回退启发式
- `VISION_BACKEND=dl`：强制 DL（没模型会报错）
```powershell
$env:VISION_BACKEND="auto"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 自定义表情模型（你的数据）

如果你想用自己的数据训练一个更贴合你的模型（输出 5 类：relaxed/focused/neutral/confused/strained）：

1) 采集数据（只保存 64x64 人脸灰度小图，不保存完整视频帧）
```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe -m ml.vision.collect_dataset
```
按键说明：
- `1~5` 选择标签（relaxed→strained）
- `s` 保存一张（建议每个标签至少 100 张以上）
- `q` 退出

2) 训练并导出 ONNX（需要在你装了 torch 的环境里运行）
```powershell
cd D:\Project\Learning\backend
python -m ml.vision.train_custom_model
```
生成：
- `backend/ml/models/emotion_custom.onnx`

3) 启用你的自定义模型
```powershell
cd D:\Project\Learning\backend
$env:VISION_BACKEND="dl"
$env:VISION_MODEL_PATH="D:\\Project\\Learning\\backend\\ml\\models\\emotion_custom.onnx"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
