# 修改日期：2026-09-05
# 修改人：[AI]

## 修改文件
- `core/llm_advisor.py`
- `app.py`
- `templates/index.html`

## 修改原因
- 用户用「流式 vs 非流式对比工具」实测（qwen3.5-flash，同题同参数）：
  - 非流式：首字/完成均 13.54s（一次性整段返回）
  - 流式：首字 0.99s、完成 8.56s
  结论：流式首字快 ~13 倍、防超时，体验明显更好 → 应用内对话与诊断报告改为流式打字机。

## 修改内容
- `core/llm_advisor.py`：新增两个生成器方法（与上方非流式方法同构，仅 stream=True + yield）：
  - `stream_advice(sensor_data)`：诊断报告流式
  - `stream_answer(question, sensor_data)`：自由对话流式
  - 均兼容“正文在 reasoning_content”的平台；并在 `finish_reason=="length"` 时结尾追加
    “内容超长被截断”提示（顺带实现此前的可选优化）；保留 `get_advice/ask_question` 非流式作回退。
- `app.py`：新增两个 SSE 端点（Bearer 鉴权，`text/event-stream`）：
  - `POST /chat_ai_stream` → `stream_answer`
  - `POST /get_ai_advice_stream` → `stream_advice`
  - 抽 `_sse()` 统一包装：异常也推送，末尾必推 `{"done":true}`，避免前端一直等。
  - 旧 `/chat_ai`、`/get_ai_advice` 保留（回退/兼容）。
- `templates/index.html`：`sendChatMessage` / `getAIAdvice` 改为消费 SSE：
  - 占位气泡 → `fetch` 流式读取 → 逐段 `innerText` 实时追加（打字机）→ 完成后整段 `marked.parse` 渲染。

## 影响范围
- AI 对话与诊断报告的显示方式（体验）；模型调用仍受当前启用方案、默认关思考、max_tokens 档位约束。
- 视觉/传感器等其它功能不受影响。

## 备注
- 未发起任何付费调用验证；`py_compile` 0 错误。需重启 Flask（`.venv\Scripts\python.exe app.py`）后生效。
- 前端若连不上新端点会显示“请求失败”，非流式旧端点仍可用（可手动回退）。

## 修复（补发）
- 四处 create 的“关思考”参数由 `**_eb` 改为 `extra_body=self._extra_no_thinking() or {}`，修复 `unexpected keyword argument 'thinking'`。
