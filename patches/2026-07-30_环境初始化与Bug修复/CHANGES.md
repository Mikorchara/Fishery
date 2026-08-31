# 修改日期：2026-07-30

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `.vscode/settings.json` | 修改 | conda → venv/pip |
| `core/llm_advisor.py` | 修改 | OpenAI 客户端容错 |
| `core/video_stream.py` | 修改 | 非阻塞初始化 |
| `.env` | 修改 | 填入 DEEPSEEK_API_KEY |
| `AGENTS.md` | 新增 | 项目指南与修改规范 |

## 环境初始化

- 删除旧 `.venv`（含残渣依赖），重建干净虚拟环境
- 安装 PyTorch 2.5.1+cu121（从官网 `download.pytorch.org/whl/cu121`）
- 安装依赖：`ultralytics opencv-python flask flask-sock openai scikit-learn`
- pip 从 24.0 升级到 26.2

## 修改 1：VS Code 设置 `.vscode/settings.json`

**原因**：系统未安装 conda，VS Code 一直提示安装 conda。

**内容**：
```json
// 改前
"python-envs.defaultEnvManager": "ms-python.python:conda",
"python-envs.defaultPackageManager": "ms-python.python:conda"

// 改后
"python-envs.defaultEnvManager": "ms-python.python:venv",
"python-envs.defaultPackageManager": "ms-python.python:pip",
"python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe"
```

## 修改 2：LLM 容错 `core/llm_advisor.py`

**原因**：`.env` 中 `DEEPSEEK_API_KEY=` 为空时，`openai.OpenAI(api_key="")` 直接抛异常导致系统无法启动。

**内容**：
- `__init__`：判断 `api_key` 是否为空，为空则 `self.client = None`
- `get_advice()` / `ask_question()`：调用前检查 `self.client is None`，返回友好提示

## 修改 3：非阻塞 RTSP `core/video_stream.py`

**原因**：`VideoCaptureThreading.__init__` 在模块导入时同步调用 `cv2.VideoCapture(rtsp_url).read()`，无 RTSP 服务器时会阻塞 30 秒，导致 `app.py` 启动卡死、日志无法输出。

**内容**：
- 将初始化时同步的 `_open_capture()` + `read()` 移至后台线程 `_init_and_update()`
- 主线程立即返回，不影响 Flask 启动

## 修改 4：API Key `.env`

**原因**：用户提供了 DeepSeek API Key。

**内容**：填入 `sk-bf4a0b5612bd4160a8284e683398792b`
