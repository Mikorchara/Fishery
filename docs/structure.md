# 项目详细结构

```
Fishery_Project/
├── app.py                  # Flask 主入口：路由、全局单例、MJPEG/H.264 流
├── config.py               # 全局配置：模型路径、阈值、LLM、编码器、认证
├── Z_script/                 # PowerShell 启动/工具脚本（须 UTF-8 with BOM）
│   ├── start_all.ps1         # 一键启动：本地视频推流 + Flask
│   ├── start_all_with_sensor.ps1  # 视频 + 传感器模拟数据一键启动（演示最全）
│   ├── start_pc_camera.ps1   # 电脑内置摄像头启动
│   ├── start_usb_camera.ps1  # 外接 USB 摄像头启动
│   ├── check_env.ps1         # 环境就绪自检（只读）
│   ├── clean_outputs.ps1     # 清理运行产出
│   └── export_drawio.ps1     # drawio 批量导出（自 scripts/ 迁入）
├── AGENTS.md               # 项目指南与修改规范
├── README.md               # 开发者指南（环境部分已过时，以 BUILD_RUN.md 为准）
├── .gitignore              # Git 忽略规则
├── .env                    # 密钥配置（gitignore，不提交）
│
├── core/                   # 核心业务模块
│   ├── video_stream.py     # RTSP 双线程异步采集 + 断线重连（指数退避）
│   ├── frame_processor.py  # 帧处理流水线（增强→AI→叠加文字），工厂闭包
│   ├── ai_detector.py      # YOLO 检测/跟踪 + SAM2/YOLO-seg 分割 + MaskTracker
│   ├── custom_yolo.py      # 自定义 YOLO 模型注册
│   ├── mask_tracker.py     # 掩码跨帧跟踪 + ID 绘制
│   ├── enhancer.py         # WWE-UIE 水下图像增强（FP16 + 预热）
│   ├── llm_advisor.py      # DeepSeek 诊断 + 对话（规则诊断 + RAG）
│   ├── storage.py          # SQLite 持久化（传感器历史 / 事件）
│   ├── h264_streamer.py    # FFmpeg 子进程 H.264 fMP4 编码 + MP4 box 解析
│   └── ws_handler.py       # WebSocket 视频推流端点
│
├── knowledge/              # 知识库
│   ├── knowledge_base.py   # EelKnowledgeBase 规则诊断 + RAGEngine(TF-IDF)
│   └── eel_knowledge.json  # 鳗鲡养殖知识图谱（数据源）
│
├── templates/
│   └── index.html          # Web 控制台 SPA（MJPEG/H.264、传感器、AI 对话）
│
├── static/                 # 前端静态资源（Flask 默认静态目录）
│   └── js/
│       └── marked.min.js   # Markdown 渲染库（本地化，避免依赖 CDN 被墙导致不渲染）
│
├── mediamtx/
│   ├── mediamtx.exe        # 本地 RTSP 服务器（gitignore，不提交）
│   └── mediamtx.yml        # RTSP 服务器配置
│
├── models/                 # 模型权重（.pt/.onnx/.om，全部 gitignore）
│   └── sam2_hiera_t.yaml   # SAM2 配置文件（文本，提交）
│
├── scripts/                # 辅助脚本（批量增强、基准测试、PPT 生成等）
├── tests/                  # pytest 测试（LLM / 增强 / H.264）
├── WWE-UIE/                # 水下增强模型仓库（训练 + 推理）
│
└── docs/                   # 项目文档
    ├── ROADMAP.md          # 开发路线图
    ├── troubleshooting.md  # 已知问题与踩坑
    ├── code_review.md      # 代码审查报告
    ├── BUILD_RUN.md        # 环境配置与运行指南
    ├── structure.md        # 本文档
    ├── patches/            # 修改补丁记录（before/after）
    └── deep-dive/          # 分模块深入讲解
```

## 关键调用链

- **视频**：RTSP → `video_stream`（后台抓帧）→ `frame_processor`（增强→AI→叠加文字）→ MJPEG（`/video_feed`）或 H.264（`ws_handler` → `h264_streamer` → `/ws_video`）
- **LLM**：请求 → `llm_advisor`（规则诊断 + RAG 检索）→ 拼 prompt → DeepSeek → 返回
- **传感器**：上报 → `storage`（SQLite）→ 轮询 → 规则告警 → 事件日志

> 深挖某一部分可看 `docs/deep-dive/`。
