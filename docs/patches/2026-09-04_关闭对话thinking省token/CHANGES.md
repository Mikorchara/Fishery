# 修改日期：2026-09-04
# 修改人：GitHub Copilot（用户确认）

## 修改文件
- `core/llm_advisor.py`（`ask_question` 内）

## 修改原因
自由对话（聊天框提问）调 DeepSeek 时带了 `reasoning_effort="high"` + `extra_body={"thinking": {"type": "enabled"}}`，
思考 token 计费且慢；而养殖问答/诊断场景用不上深度思考，属纯浪费。

## 修改内容
- `ask_question()` 的 `client.chat.completions.create(...)` 中去掉 `reasoning_effort` 与 `extra_body` 两个参数 → 普通模式调用（省 token、更快）。
- 增加注释说明改动原因，并指引 ROADMAP「LLM 模型自由切换」计划。
- 注：诊断报告路径 `get_advice()` 本来就不带 thinking，未改动。

## 影响范围
- 网页「AI 智慧养殖对话」的回答质量基本不受影响（任务简单），token 消耗显著下降。
- `get_advice`（诊断报告）、`config.py`、`app.py` 均未改动。
