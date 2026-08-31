# 修改日期：2026-08-31
# 修改人：AI (Copilot)

## 修改文件
- `templates/index.html` — 前端：AI 报告 Markdown 渲染改为离线安全（CDN 失效时兜底），不再因 marked.js 加载失败而空白/报错
- `core/llm_advisor.py` — 后端：兼容 DeepSeek thinking 模式（content 可能为空），回退到 reasoning_content

## 修改原因
启动后 AI 报告（诊断报告 / 自由对话）在网页上无法正常显示：
1. 前端通过 CDN（cdn.jsdelivr.net）加载 marked.js，若 CDN 被墙/离线则 `marked` 未定义，
   `marked.parse()` 抛错 → AI 消息无法显示（表现为空白或只看到未渲染的原始 Markdown）。
2. 后端 `ask_question` 开启了 DeepSeek thinking 模式，模型可能把内容放到
   `reasoning_content` 而 `content` 为空，导致返回空串，前端显示空白。

## 修改内容
- `index.html`：
  - 新增 `fallbackMarkdown()`：内置轻量 Markdown 渲染（代码块/表格/标题/列表/加粗/斜体/行内代码/换行），完全离线可用
  - 新增 `renderMarkdown()`：优先用 CDN 的 marked，失败自动回退到内置渲染，且全程 try/catch
  - `addMessage()` 中 AI 分支由 `marked.parse(text)` 改为 `renderMarkdown(text)`
- `llm_advisor.py`：
  - 新增 `_extract_reply(completion)`：优先取 `content`，为空则回退 `reasoning_content`，并清除 `<thinking>` 块
  - `get_advice()` / `ask_question()` 返回值改用它

## 影响范围
- AI 诊断报告（网页「生成当前环境实时诊断报告」按钮）
- AI 自由对话（网页聊天框）
- 不涉及视频流 / 传感器等其他功能

## 备注
- 另新建 `start_all.ps1`（一键启动 mediamtx + ffmpeg + Flask），属于新增文件，未改动已有代码，故不入补丁。
