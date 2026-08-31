# deep-dive — 分模块深入讲解

> 用于存放项目某一部分的详细讲解文档（架构、调用链、逐文件分析等），每个主题一个文件。

## 目录

<!-- 在此登记已创建的深入讲解 -->

- `developer_guide.md` — 开发者指南（原 README 详细版迁移至此，环境部分已过时，以 BUILD_RUN.md 为准）
- `outputs.md` — 项目输出内容（产物）全览：每个输出的产生来源 / 用途 / 清理方式

## 建议主题

- `video-pipeline.md` — 视频双通道（MJPEG / H.264）完整链路
- `ai-detector.md` — YOLO 三种分割路径（track / YOLO-seg / SAM2）
- `llm-rag.md` — 规则诊断 + RAG + DeepSeek 的组装过程
- `startup.md` — 启动脚本与进程编排
