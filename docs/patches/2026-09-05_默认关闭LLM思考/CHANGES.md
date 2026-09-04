# 修改日期：2026-09-05
# 修改人：[AI]

## 修改文件
- `core/llm_advisor.py`

## 修改原因
- 用户实测：思考型模型（MiMo-V2.5 / Qwen3.5 默认开启思考）在每次问答前先“深度思考”，
  单次耗时 20~50s，且思考 token 也占输出预算；养殖问答用不上深度思考。
- 现阶段统一「默认关闭思考」，节省时间与 token；把“思考做成可选项”放到 ROADMAP 计划中。

## 修改内容
- 新增私有方法 `_extra_no_thinking()`：按 `self.model` 前缀返回“关思考”的 `extra_body`：
  - `deepseek-v4*` → `{"thinking": {"type": "disabled"}}`
  - `qwen*`（Qwen3.x 混合思考）→ `{"enable_thinking": False}`
  - MiMo-V2.5 等暂无公开关闭参数 → 返回 None（保持原样，不传参）
- `get_advice()` / `ask_question()`：调用 create 前取 `_eb = self._extra_no_thinking() or {}`，
  并在请求参数中 `**_eb` 注入（两处均默认关闭思考）。

## 影响范围
- AI 诊断报告与自由对话：对 DeepSeek/Qwen 均不再进入思考阶段 → 更快、更省；
  输出仍从 `content` 读取（思考关闭后平台直接给正文）。
- 不改请求方式（仍非流式）、不改 max_tokens 档位、不改服务切换逻辑。
- 若未来某模型需要思考：在 `_extra_no_thinking()` 加白名单或做 per-方案可选项（见 ROADMAP）。

## 备注
- 验证遵循成本规则：本改动只做了 `py_compile`，未发起任何付费调用；效果由用户页面实测。

## 修复（补发）
- 原实现用 `**_eb` 展开“关思考”字典 → OpenAI SDK 报 `Completions.create() got an unexpected keyword argument 'thinking'`（thinking/enable_thinking 属非标准参数，不能作为顶层关键字）。
- 已改为 `extra_body=self._extra_no_thinking() or {}`，4 处 create 调用（get_advice / ask_question / stream_advice / stream_answer）全部修正。
