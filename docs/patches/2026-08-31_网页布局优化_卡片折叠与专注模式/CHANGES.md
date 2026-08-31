# 修改日期：2026-08-31

## 修改文件
- `templates/index.html` — 网页布局优化（卡片折叠 + AI 对话专注模式 + marked.js 本地化 + 渲染兜底；专注按钮文字横排/去变色）--- modify_0
- `static/js/marked.min.js` — 新增：marked.js 本地化（从 CDN 下载 35KB）。注意：Flask 默认静态目录是**项目根 static/**（`/static/...` 路由），不是 templates/static/；验证时曾因放错位置 404，已修正 --- 新增文件
- `AGENTS.md` — 前端行与核心模块表补充 `static/` 目录说明 --- modify_1
- `docs/structure.md` — 结构树补充 `static/js/marked.min.js` --- modify_1

## 修改原因
1. **token 消耗高**（AI 侧）：`core/llm_advisor.py` 的自由对话模式开启了 DeepSeek thinking 思维链且 `reasoning_effort="high"`，隐藏思维链 token 计入计费；每次请求全量注入 RAG(top_k=5)+规则诊断。本次不涉及代码改动，仅记录原因。
2. **网页端 AI 对话显示问题**：
   - 右侧面板固定 420px，堆叠 4 张卡，AI 对话区被挤到底部一小块，长文看不清；
   - marked.js 走 CDN（cn.jsdelivr.net）可能被墙，导致 AI 返回的 Markdown 不渲染。

## 修改内容
- `index.html`：
  - marked.js 引用由 CDN 改为本地 `/static/js/marked.min.js`；
  - 新增 `.card-head`（可点击标题栏）+ `.card-toggle`（折叠按钮 `−`/`+`）+ `.card.collapsed` 折叠样式；
  - 传感器 / 事件日志 / AI 视觉中枢 三张卡包进 `.card-head` + `.card-body`，支持点击标题栏折叠；
  - AI 对话卡加 `chat-card` 类 + 「专注」按钮，专注模式下隐藏左侧视频区 + 其他卡片，对话区占满全屏；
  - 专注按钮按用户反馈调整：文字横排（`white-space: nowrap` + 宽度自适应），仅用「专注」/「退出」文字区分状态，**去掉进入专注时的蓝色高亮**；
  - `addMessage` 增加 `window.marked` 判空，不可用时用 `simpleMd()` 极简 Markdown 兜底渲染。
- `AGENTS.md` / `docs/structure.md`：记录新增 `static/` 静态资源目录。

## 影响范围
- 网页端布局与 AI 对话显示；不影响后端 API 与视频流。

## 附：Token 消耗偏高原因（备忘）
- 主因：`ask_question()` 中 `reasoning_effort="high"` + `extra_body={"thinking":{"type":"enabled"}}` → DeepSeek V4 思维链大量隐藏 token 计入计费。
- 次因：每次请求注入 RAG(top_k=4~5) + 规则诊断 + system prompt，输入偏重。
- 建议：关 thinking 或降为 low，RAG top_k 降至 2~3。暂未改动 `llm_advisor.py`。
