# 环境配置与运行指南

## 环境要求

- Windows（开发环境）
- Python 3.11（venv，非 conda）
- NVIDIA GPU + CUDA（本项目用 RTX 3070 Laptop 8GB，PyTorch 2.5.1+cu121）
- FFmpeg（用于 H.264 编码与视频推流）
- mediamtx（本地 RTSP 服务器）

## 一、环境安装

### 1. 创建虚拟环境

```powershell
cd d:\Fishery_Project
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```powershell
pip install ultralytics opencv-python flask flask-sock openai scikit-learn numpy
# 可选：WWE-UIE 完整训练功能
pip install -r WWE-UIE/requirements.txt
```

> PyTorch 需从官网按 CUDA 版本安装：https://pytorch.org

### 3. 安装 FFmpeg / mediamtx

- **FFmpeg**：从 https://ffmpeg.org/download.html 下载解压，把 `bin` 加入系统 PATH。
- **mediamtx**：从 https://github.com/bluenviron/mediamtx/releases 下载解压到 `mediamtx/`（`mediamtx.exe` 不入 git）。

### 4. 模型文件

放于 `models/`（权重均不入 git）：
- 必需：`fish_detect_m.pt`
- 可选：`fish_detect_seam.pt`、`fish_seg_yolo26.pt`、`fish_seg_yolo11n.pt`、`sam2.1_t.pt` + `sam2_hiera_t.yaml` 等
- WWE-UIE 权重自动从 `WWE-UIE/output/Fishery_WWE_UIEB/UIEB/` 取最新 `best_model.pth`

### 5. 配置密钥

项目根目录 `.env`：

```
DEEPSEEK_API_KEY=你的API密钥
```

不配也能运行，仅 LLM 诊断/对话不可用。

## 二、运行

### 方式一：一键启动（推荐）

```powershell
cd d:\Fishery_Project
.\start_all.ps1
```

自动完成：mediamtx → ffmpeg 推流 → Flask → 8 秒后自动打开浏览器。

### 方式二：手动 3 终端

见 `AGENTS.md`「启动流程 · 方式二」。

## 三、访问

| 地址 | 说明 |
|------|------|
| http://127.0.0.1:5000 | Web 控制台 |
| http://127.0.0.1:5000/video_feed | MJPEG 视频流 |
| ws://127.0.0.1:5000/ws_video | H.264 WebSocket 视频流 |

## 四、停止

- 一键启动：直接 `Ctrl+C`（自动关闭 ffmpeg / mediamtx）
- 手动 3 终端：按顺序停 Flask → ffmpeg → mediamtx

## 五、验证

```powershell
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "from ultralytics import YOLO; print('Ultralytics: OK')"
python -c "import flask; print('Flask:', flask.__version__)"
```
