# 修改日期：2026-09-05
# 修改人：[AI]

## 修改文件
- `core/llm_advisor.py`

## 修改原因
- 合入流式后用户发现：MIMO（mimo-v2.5，无法“关思考”的深度思考模型）会“立马输出但内容像思考草稿、无完整组织”。
- 一次性真实调用探测证实（`scratch/mimo_probe.py`，用户授权本次）：
  - reasoning_content 先输出 321 字（内心戏草稿），content 仅最后 19 字正式回答。
- 根因：流式解析原来“content 为空则取 reasoning_content 当正文”，于是把“无法关思考”模型的思考过程当回答实时显示了。

## 修改内容
- `stream_advice()` / `stream_answer()` 修订：**只把 `content`（正式正文）发给前端，reasoning/reasoning_content 一律不进正文**；
- 收尾逻辑：
  - `finish_reason == "length"` → 追加“内容超长被截断”提示（保留）；
  - 全程无正文且存在思考 → 追加“该模型未输出正式正文（思考过长…）建议换模型/缩短问题”的诚实提示。

## 影响范围
- 流式对话与报告：DeepSeek/Qwen（已关思考）无感知；MIMO 不再显示思考草稿，
  正式回答（content）开始后才逐字显示；若 MIMO 思考过长吃掉全部预算则给出提示而非“只见草稿”。
- 前端与 SSE 协议未改动（仍逐段收 delta 文本）。

## 备注
- 离线验证：`scratch/verify_extra_body.py` 新增流式用例（假 client：先 reasoning 后 content）——
  断言输出只含“正文一正文二”、不含“思考草稿”；三种模型分支 extra_body 依旧正确。
- 未做其它付费调用（探测仅 1 次）。
- 可后续优化：为 MIMO 等思考型模型增加“思考中…”占位提示（前端事件化），见 ROADMAP 思考可选项。
