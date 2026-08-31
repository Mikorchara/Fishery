# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

智慧渔业水下协同控制系统 — a real-time underwater video monitoring and analysis platform. The system captures video (RTSP/local camera), enhances underwater image quality (WWE-UIE), detects fish (YOLOv8), segments targets (SAM2), provides an LLM-powered aquaculture advisor, and displays everything through a web UI.

## Commands

```bash
# Start the system
python app.py

# Test LLM connectivity independently
python tests/test_llm.py

# List available NVIDIA API models
python scripts/list_models.py

# Generate graduation defense PPT
python scripts/generate_ppt.py
```

Dependencies: `pip install flask ultralytics openai` and `pip install -r WWE-UIE/requirements.txt`.

Video source is configured in `config.py` (`STREAM_URL`). Default listens on `http://0.0.0.0:5000`.

For local video file testing without RTSP server, use ffmpeg: `ffmpeg -re -stream_loop -1 -i test_video.mp4 -c copy -rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/mystream`

## Architecture

Data flow: RTSP source → `VideoCaptureThreading` (background thread, non-blocking read) → optional `WWEEnhancer` (color correction) → optional `FisheryAI` (YOLOv8 detect + SAM2 segment) → MJPEG stream → Web browser.

### Core Modules

- **`app.py`** — Flask server, system entry point. Routes: `/video_feed` (MJPEG), `/toggle_ai`, `/toggle_enhancement`, `/toggle_segmentation`, `/switch_model`, `/update_sensor`, `/get_sensor`, `/get_ai_advice`, `/chat_ai`. State held in global `system_state` dict.
- **`config.py`** — All tunable parameters: stream URL, model paths, detection thresholds, SAM2 prompts, LLM endpoint.
- **`core/video_stream.py`** — `VideoCaptureThreading`: daemon thread continuously reads frames into memory; `read()` returns latest frame without blocking. Force TCP transport for RTSP.
- **`core/enhancer.py`** — `WWEEnhancer`: wraps WWE-UIE PyTorch model. BGR→RGB→normalize→infer→denormalize→RGB→BGR. Auto-finds latest trained weights in `WWE-UIE/output/Fishery_WWE_UIEB/`.
- **`core/ai_detector.py`** — `FisheryAI`: loads YOLO + SAM2 models at init. `process_frame()` runs YOLO predict, then optionally SAM2 with configurable prompt mode (`box`/`point`/`hybrid`). `load_model()` hot-swaps YOLO weights without restart.
- **`core/llm_advisor.py`** — `FisheryAdvisor`: OpenAI-compatible SDK calling NVIDIA API (MiniMax-M2.7). Two modes: `get_advice()` (environment diagnosis from sensor data) and `ask_question()` (free chat with sensor context). Non-streaming for Flask compatibility.
- **`templates/index.html`** — Single-page UI: MJPEG video, IoT sensor panel (polled every 2s), AI toggle buttons, model selector, chat window with Markdown rendering (marked.js).

### Key Design Decisions

- **Dual-thread video**: Background thread captures frames independently so AI inference never blocks frame acquisition.
- **Config-driven**: All thresholds, paths, and toggle states in `config.py` — no hardcoded values in core logic.
- **Model hot-swap**: YOLO weights can be changed at runtime via `/switch_model` without restarting the server.
- **SAM2 optional**: Segmentation model only runs when toggled on, saving GPU memory by default.
- **LLM non-streaming**: Using `stream=False` to stay compatible with Flask's synchronous request handling.

### Models

- `models/fish_detect_m.pt` — Custom YOLOv8 model for fish detection (primary model, EMA attention)
- `models/yolov8n.pt` — Fallback generic YOLOv8 nano model
- `models/sam2.1_t.pt` + `models/sam2_hiera_t.yaml` — SAM2 Tiny for instance segmentation
- (WWE-UIE weights are auto-discovered in `WWE-UIE/output/`)
