# 开发路线图

> 状态标记：✅ 已完成 ｜ 🔄 进行中 ｜ 📋 计划中

## 已完成 ✅

- 环境初始化（venv Python 3.11 + PyTorch 2.5.1+cu121 + RTX 3070）
- 视频双通道：MJPEG（HTTP）+ H.264（WebSocket）实时推流
- YOLO 鱼群检测 / 分割（多模型热切换 + SAM2 / YOLO-seg）
- WWE-UIE 水下图像增强（FP16 + 可选 torch.compile）
- DeepSeek LLM 诊断 + RAG（TF-IDF）对话
- 传感器上报 + SQLite 持久化 + 规则告警
- 一键启动脚本 `start_all.ps1`（mediamtx + ffmpeg + Flask）
- Git 化并上传 GitHub（https://github.com/Mikorchara/Fishery.git）
- docs/ 文档整理（ROADMAP / troubleshooting / code_review / BUILD_RUN / structure / deep-dive）

## 进行中 🔄

- 暂无

## 计划中 📋

- [ ] **修复 AI 报告 Markdown 显示问题**（见 `troubleshooting.md`）：CDN 加载 marked.js 可能被墙；后端 thinking 模式 content 可能为空
- [ ] 补充单元测试与集成测试（pytest），覆盖 `core/` 各模块
- [ ] 传感器真实硬件（MCU）接入联调
- [ ] 模型热切换的异步预加载，避免切换卡顿
- [ ] H.264 / MJPEG 双通道异常自动切换的稳定性测试
- [ ] 部署文档：从本地开发环境迁移到服务器（Linux）

## 待评估（暂缓）

- 全局快捷键（pynput）
- 接入本地 LLM（Ollama / llama.cpp）作为离线备选
