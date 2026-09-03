# 智慧渔业视频分析系统 — 开发者指南

## 前言
运行需要搭建一下环境。不太熟悉的话有问题可以多问问AI,也可以问我


系统启动方法：
需要从一个RTSP服务器拉取视频流，目前采用的方式是安装mediamtx 用于在本地创建RTSP服务器,然后用FFmpeg将视频本地视频test_video.mp4推流到服务器上，系统再进行拉流。
准备好视频流后，运行app.py就能启动系统



## 一、环境安装

### 1.1 基础环境

- CUDA 11.8+
- FFmpeg 用于H.264视频编码
- Conda 用于管理虚拟环境
- mediamtx 用于在本地创建RTSP服务器 https://github.com/bluenviron/mediamtx/releases/tag/v1.19.1

### 1.2 创建虚拟环境

```bash
conda create -n fishery python=3.9
conda activate fishery
```

### 1.3 安装依赖

需要安装pytorch，具体教程上网搜索
剩下的包可以用以下命令安装，
```bash
pip install ultralytics opencv-python flask flask-sock openai scikit-learn numpy
```

如需 WWE-UIE 图像增强模块的完整训练功能，还需安装：

```bash
pip install -r WWE-UIE/requirements.txt
```

### 1.4 安装 FFmpeg

可以自行搜索安装教程

**Windows**：从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载，解压后将 `bin` 目录加入系统 PATH。

**Linux**：`sudo apt install ffmpeg`。

**macOS**：`brew install ffmpeg`。

验证安装：`ffmpeg -version`。

### 1.5 获取模型文件

鳗鱼的模型都在这个文件夹下：

| 文件 | 用途 | 必需 |
|------|------|------|
| `fish_detect_m.pt` | YOLO 标准鱼群检测（EMA 注意力） | 是 |
| `fish_detect_seam.pt` | YOLO SEAM 改进版检测 | 否 |
| `fish_detect.onnx` | ONNX 导出检测模型 | 否 |
| `fish_seg_yolo26.pt` | YOLO26-seg 鳗鱼分割 | 否 |
| `fish_seg_yolo11n.pt` | YOLO11-seg 分割 | 否 |
| `sam2.1_t.pt` | SAM2 分割基础模型 | 否 |
| `sam2_hiera_t.yaml` | SAM2 配置文件 | 否 |

> **ONNX 模型运行须知**：`.onnx` 需要 onnxruntime 库；onnxruntime-gpu **不捆绑 CUDA 库**，需自行安装**匹配的独立 CUDA Toolkit + cuDNN**（本项目 PyTorch 为 cu121 / CUDA 12，应装 onnxruntime-gpu **1.21.x**，配 `.venv` 内 cuDNN）。若缺失，ultralytics 会**自动联网装最新版**（1.29 需 CUDA 13）导致不匹配。详细经验见 `docs/troubleshooting.md` 第 8 条，模型分类见 `docs/deep-dive/models-guide.md`。

水下图像增强的模型在这里：
WWE-UIE 增强权重会自动从 `WWE-UIE/output/Fishery_WWE_UIEB/UIEB/` 目录中按日期选取最新的 `best_model.pth`。

### 1.6 配置 DeepSeek API Key

在项目根目录 `.env` 文件中加入你自己的apikey

```
DEEPSEEK_API_KEY=你的API密钥
```

`config.py` 启动时自动加载。不配也不影响系统运行，只是 大语言模型诊断和对话功能不可用。

### 1.7 验证安装

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "from ultralytics import YOLO; print('Ultralytics: OK')"
python -c "import flask; print('Flask:', flask.__version__)"
```

---

## 二、启动系统

### 2.1 准备视频源

**方式一：真实 RTSP 摄像头**

修改 `config.py` 中的 `STREAM_URL` 为摄像头 RTSP 地址。

**方式二：本地视频文件模拟 RTSP 流**

开一个终端推送本地视频为 RTSP 流：

```bash
ffmpeg -re -stream_loop -1 -i test_video.mp4 -c copy \
-rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/mystream
```

`config.py` 中 `STREAM_URL` 保持默认 `rtsp://127.0.0.1:8554/mystream`。

**方式三：静态图片模拟 RTSP 流**

```bash
ffmpeg -re -loop 1 -i test_image.jpg -c:v libx264 -tune stillimage \ 
  -pix_fmt yuv420p -rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/mystream
```

### 2.2 启动服务

```bash
python app.py
```

正常启动日志示例：

```
[12:30:01] [INFO] app: WWE-UIE 权重: .../best_model.pth
[12:30:02] [INFO] ai: 加载 YOLO 模型 (PT): models/fish_detect_m.pt | conf=0.40 iou=0.40 imgsz=640
[12:30:05] [INFO] ai: SAM2: FP16 推理
[12:30:05] [INFO] ai: 所有 AI 模型加载成功
[12:30:05] [INFO] advisor: RAG 引擎就绪: 29 个知识块已索引
[12:30:05] [INFO] enhancer: WWE-UIE 预热完成
```

访问 `http://127.0.0.1:5000`。

### 2.3 启动参数

在 `config.py` 中可调整：

```python
WEB_HOST = '0.0.0.0'    # 监听地址，0.0.0.0 允许局域网其他设备访问
WEB_PORT = 5000          # 监听端口
STREAM_URL = "rtsp://..." # 视频源地址
ENHANCE_MAX_SIDE = 640   # 增强处理分辨率上限
ENHANCE_FP16 = True      # 增强 FP16 加速
ENHANCE_COMPILE = True   # torch.compile 加速（Linux 下生效）
AUTH_TOKEN = "fishery2026"  # Web API 认证 Token
```

---

## 三、项目结构

```
Fishery_Project/
├── app.py                  # Flask 主入口，路由定义
├── config.py               # 全局配置：模型路径、推理参数、API 密钥
├── .env                    # DeepSeek API Key（不入 git）
├── core/
│   ├── ai_detector.py      # FisheryAI：YOLO 检测/分割 + SAM2 + 追踪
│   ├── custom_yolo.py      # SEAM、EMA 自定义模块注册
│   ├── enhancer.py         # WWEEnhancer：水下图像增强
│   ├── video_stream.py     # VideoCaptureThreading：RTSP 双线程异步采集
│   ├── frame_processor.py  # create_frame_processor：帧处理流水线闭包
│   ├── mask_tracker.py     # MaskTracker：掩码 IoU 帧间追踪
│   ├── h264_streamer.py    # H264Encoder：FFmpeg 子进程 fMP4 编码
│   ├── ws_handler.py       # WebSocket 视频推流注册
│   ├── llm_advisor.py      # FisheryAdvisor：LLM 诊断 + 对话
│   └── storage.py          # Storage：SQLite 传感器与事件持久化
├── knowledge/
│   ├── eel_knowledge.json  # 鳗鲡养殖知识图谱（RAG 知识库源数据）
│   └── knowledge_base.py   # EelKnowledgeBase + RAGEngine
├── models/                 # 模型权重文件（.pt / .onnx / .om）
├── templates/
│   └── index.html          # Web 控制台 SPA
├── tests/                  # 单元测试和基准测试
├── scripts/                # 辅助脚本
├── WWE-UIE/                # 水下增强模型（训练+推理）
├── docs/                   # 文档
└── data.db                 # SQLite 数据库文件（运行时自动生成）
```

---

## 四、核心 API 路由

### 4.1 视频流

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/video_feed` | MJPEG 推流，直接从 `<img>` 标签播放 |
| WS | `/ws_video` | H.264 WebSocket 推流，需 MSE API 支持 |

### 4.2 AI 控制（认证：Bearer Token）

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/toggle_ai` | 开关 AI 检测 |
| POST | `/toggle_enhancement` | 开关图像增强 |
| POST | `/toggle_segmentation` | 开关实例分割 |
| POST | `/switch_model` | 热切换 YOLO 模型，body: `{"model_key": "fish_seg"}` |

### 4.3 传感器

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/update_sensor` | 上报传感器数据（认证），body: `{"temp":28.5, "ph":7.2, "oxygen":5.8}` |
| GET | `/get_sensor` | 获取最新传感器读数 |
| GET | `/get_sensor_history` | 获取最近 N 分钟历史数据，参数：`?minutes=120` |

### 4.4 告警

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/check_alarm` | 检查当前传感器值是否触发告警阈值 |
| GET | `/get_events` | 获取最近告警事件（内存优先，回退 SQLite） |

### 4.5 LLM

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/get_ai_advice` | 诊断模式：自动读取传感器值，返回结构化报告 |
| POST | `/chat_ai` | 对话模式，body: `{"message": "水温32度鱼不吃料怎么办"}` |

### 4.6 截图与录制

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/capture_frame` | 保存当前帧为 JPEG 到 `captures/` 目录（认证） |
| POST | `/start_recording` | 开始 FFmpeg 录像（认证） |
| POST | `/stop_recording` | 停止录像（认证） |

### 4.7 状态

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/health` | 视频流连接状态 + AI 加载状态 |
| GET | `/perf_snapshot` | 当前 FPS、GPU 显存、CPU 占用、启用状态 |

---

## 五、继续开发指南

### 5.1 添加新的检测模型

**步骤 1**：将模型权重文件（.pt 或 .onnx）放入 `models/` 目录。

**步骤 2**：在 `config.py` 的 `AVAILABLE_MODELS` 和 `MODEL_CONFIGS` 中各添加一行：

```python
AVAILABLE_MODELS = {
    ...
    "my_new_model": "models/my_new_model.pt",
}

MODEL_CONFIGS = {
    ...
    "my_new_model": {"conf": 0.3, "iou": 0.5},
}
```

key 中含 "seg" 会自动按分割模型加载。

**步骤 3**：在 `templates/index.html` 的模型下拉菜单中增加一个 `<option>`：

```html
<option value="my_new_model">模型：我的新模型</option>
```

无需修改任何 Python 逻辑代码。

### 5.2 扩展 RAG 知识库

编辑 `knowledge/eel_knowledge.json`，在对应知识域下添加新条目。字段格式与已有条目保持一致。添加后无需重新索引——`RAGEngine` 在 `FisheryAdvisor.__init__()` 时自动重建索引。

如需增加新的知识域，同时修改 `knowledge/knowledge_base.py` 中的 `_chunk_knowledge()` 函数，为新域编写文本拼接逻辑。

### 5.3 调整告警阈值

编辑 `knowledge/knowledge_base.py` 中的 `ALARM_RULES` 列表。每条规则是 `(级别, 条件lambda, 消息模板)` 三元组。新增或修改规则后重启服务即可生效，无需改前端。

### 5.4 添加新的 API 路由

在 `app.py` 中添加新的 `@app.route()`。如需认证，套上 `@require_auth` 装饰器。GET 类路由通常不加认证。添加后在 `templates/index.html` 中增加对应的 `authFetch()` 或直接 `fetch()` 调用。

### 5.5 修改增强模块

增强权重默认从 `WWE-UIE/output/Fishery_WWE_UIEB/UIEB/` 按日期自动选取最新。如需使用指定权重，在 `app.py` 初始化 `WWEEnhancer(weight_path="你的路径")` 时传入。

微调新数据时使用 `scripts/finetune_enhancer.py`，数据目录结构需包含 `trainA/`（原始水下图像）、`trainB/`（参考增强图像）、`valA/`、`valB/` 四个子目录。

### 5.6 调整前端布局

所有 CSS 变量定义在 `templates/index.html` 的 `<style>` 区域 `:root` 选择器中。修改颜色主题时只需改这些变量：

```css
:root {
    --bg-color: #f1f5f9;
    --panel-bg: #ffffff;
    --accent: #334155;
    --success: #16a34a;
    --danger: #dc2626;
}
```

右侧面板默认宽度 420px，调整范围在 JS 中 `Math.max(320, Math.min(700, w))` 处修改。

### 5.7 关键数据流路径

理解系统时按以下数据流看代码：

**视频帧路径**：`VideoCaptureThreading.update()` → `video_stream.read()` → `FrameProcessor.process()` → `cv2.imencode()`（MJPEG）或 `H264Encoder.encode_frame()`（H.264）→ 浏览器

**AI 推理路径**：`FrameProcessor.process()` → `FisheryAI.process_frame()` → `YOLO.predict()` → 可选 `SAM2()` → `yolo_results.plot()` → 返回标注帧

**增强路径**：`WWEEnhancer.enhance()` → `_bgr_to_rgb_tensor()` → `model(input_tensor)` → `_tensor_to_bgr_numpy()` → 返回增强帧

**LLM 路径**：前端点击 → `authFetch('/get_ai_advice')` → `FisheryAdvisor.get_advice()` → `kb.diagnostic_guide()` + `rag.retrieve()` → DeepSeek API → 返回 Markdown → `marked.js` 渲染

### 5.8 性能调优

- GPU 显存不足时：关闭 SAM2（不开启分割开关）、使用 ONNX 模型替代 PyTorch 模型
- MJPEG 带宽过大时：优先使用 H.264 WebSocket 推流
- 无明显目标时：关闭 AI 检测开关降低 GPU 负载
- 首次推理慢：WWE-UIE 预热阶段已处理 CUDA 冷启动，首次真实帧后延迟稳定

### 5.9 常见问题

**Q: 启动后画面黑屏？**
检查 `STREAM_URL` 是否能正常访问。用 VLC 或 `ffplay` 测试 RTSP 地址是否通。确认防火墙未阻止 5000 端口。

**Q: AI 模型加载失败？**
检查 `models/` 目录下是否有对应权重文件。确认 PyTorch 和 ultralytics 版本兼容。`fish_detect.onnx` 需要 `onnxruntime` 包。

**Q: H.264 推流无法使用？**
检查 FFmpeg 是否正确安装且 `ffmpeg` 命令可在终端执行。Windows 下确认 FFmpeg 的 bin 目录已加入系统 PATH。

**Q: LLM 对话报错？**
检查 `.env` 文件中 `DEEPSEEK_API_KEY` 是否正确。确认网络可访问 `api.deepseek.com`。

**Q: 增强模块报错？**
检查 `WWE-UIE/output/Fishery_WWE_UIEB/UIEB/` 目录下是否有 `best_model.pth` 权重文件。无权重时不加载增强但系统不报错。
