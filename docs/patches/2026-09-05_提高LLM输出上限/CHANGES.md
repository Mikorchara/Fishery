# 修改日期：2026-09-05
# 修改人：[AI]

## 修改文件
- `config.py`
- `core/llm_advisor.py`

## 修改原因
- 原 `max_tokens=1024` 对「思考型模型（MiMo-V2.5 / Qwen3.5 默认开思考）+ 长报告」太小：
  思考 token 也占用该输出预算，导致正式正文没写完就被 `finish_reason=length` 截断（用户实测两模型报告均被截断）。
- 把上限提升并拆成「报告 / 对话」两档，且改为 config 常量，便于按模型/场景随时调整。

## 修改内容
- `config.py`：新增两个常量（并注明 max_tokens 限制的是“输出 token”而非输入）
  - `LLM_REPORT_MAX_TOKENS = 4096`  # 诊断报告（思考型模型需给足预算）
  - `LLM_CHAT_MAX_TOKENS = 2048`    # 自由对话
- `core/llm_advisor.py`：
  - `get_advice()`：`max_tokens=1024` → `config.LLM_REPORT_MAX_TOKENS`
  - `ask_question()`：`max_tokens=1024` → `config.LLM_CHAT_MAX_TOKENS`

## 影响范围
- AI 诊断报告与自由对话的输出长度上限（变长）；若某模型回复远超上限仍会截断，可按需调大对应常量或改流式。
- 不改请求方式（仍非流式）、不改模型/服务切换逻辑。

## 备注 / 后续可选
- 若要彻底避免“静默截断”：非流式解析时检查 `completion.choices[0].finish_reason == "length"`，在回答尾部追加“…（内容超长被截断，可让我分点续写）”提示（未实施）。
- 思考型模型想更快：DeepSeek 用 `thinking:{type:disabled}` / `reasoning_effort`；Qwen3.5 用 `extra_body={"enable_thinking": false}` 或 `thinking_budget`（未实施，视需要再加）。
