# LLM / AI 服务全貌（llm-services）

> 讲解本项目「AI 智慧养殖对话 / 实时诊断报告」背后：模块文件、两条调用链、**每次请求真正发给模型的上下文构成**、多方案热切换机制，以及「回答慢」的解剖与优化建议。适用版本：2026-09-04（LLM 多服务自由切换落地后）。

## ⚠️ 2026-09-05 重大变更（下文“旧状态”段为历史参考，请以本块为准）

- **对话与诊断报告已改流式打字机**：`llm_advisor` 新增 `stream_advice/stream_answer`（只发 `content`、丢弃思考）；
  `app.py` 新增 SSE `/chat_ai_stream`、`/get_ai_advice_stream`；前端逐字显示、完成再渲染 Markdown。
  实测（qwen3.5-flash 同题同参）：流式首字 0.99s vs 非流式一次性 13.54s。补丁 `2026-09-05_对话报告流式打字机`。
- **默认关闭思考**：`_extra_no_thinking()` 按模型注入 `extra_body`（deepseek-v4→`thinking.disabled`、qwen→`enable_thinking=false`；
  MiMo-V2.5 无法关闭 → 不传）。效果：DeepSeek 3 次提问约 ¥0.1（省掉的 reasoning token 是烧钱大头）。补丁 `2026-09-05_默认关闭LLM思考`。
- **输出上限配置化**：`config.LLM_REPORT_MAX_TOKENS=4096`、`LLM_CHAT_MAX_TOKENS=2048`（解决思考型模型正文被截断）。补丁 `2026-09-05_提高LLM输出上限`。
- **关键认知**：多家平台 `max_tokens` 是“思考+正文总额”上限 → 思考过长会把正文挤出（content 空、只见草稿、草稿仍计费）。补丁 `2026-09-05_MIMO思考不进正文`；详见 `troubleshooting.md` #11/#12。
- 上述 4 个补丁均有 before/after 与 CHANGES，位于 `docs/patches/2026-09-05_*`。

---

---

## 1. 一句话概览

页面问一句 → 后端把「**规则诊断 + RAG 知识块 + 传感器数据**」拼进 prompt → 发给**当前启用的 LLM 服务**（默认 DeepSeek，可在右上角「LLM 服务设置」弹窗换成小米 MiMo / 任意 OpenAI 兼容服务）→ 整段返回后前端一次性显示。

分层结构：

```mermaid
flowchart LR
    UI[前端 index.html<br/>对话卡片 + LLM 设置弹窗] -->|POST /chat_ai| A
    UI -->|POST /llm_profiles/*, /llm_test, /llm_models| A
    A[app.py 路由层<br/>Bearer 鉴权 + 编排] --> B[core/llm_advisor.py<br/>FisheryAdvisor]
    A --> C[core/llm_settings.py<br/>多方案持久化/热切换]
    B --> D[knowledge/knowledge_base.py<br/>规则诊断 + RAG(TF-IDF)]
    B -->|OpenAI 兼容 SDK| E[启用的 LLM 服务<br/>DeepSeek / 小米 MiMo / 其他]
    C --> F[llm_settings.json<br/>含 Key, gitignore]
```

---

## 2. 相关文件与职责

| 文件 | 职责 | 关键点 |
|---|---|---|
| `core/llm_advisor.py` | 真正的 LLM 调用方 | `FisheryAdvisor`：`get_advice()`（诊断）/ `ask_question()`（自由对话）/ `reconfigure()`（热切换）；持有 OpenAI client、规则引擎 `kb`、RAG 引擎 `rag` |
| `core/llm_settings.py` | 多套服务方案管理 | 方案 CRUD + 启/禁 + 持久化 `llm_settings.json` + Key 脱敏 + 预设表 |
| `app.py` | 路由与全局单例 | 全局 `llm_advisor`；LLM 相关路由见下表；启动时 `_apply_llm_active()` 恢复上次启用方案 |
| `config.py` | **系统默认**三件套 | `LLM_API_KEY`(读 .env) / `LLM_BASE_URL=https://api.deepseek.com` / `LLM_MODEL=deepseek-v4-flash` |
| `knowledge/knowledge_base.py` | 本地知识（不进 LLM 也有的能力） | `EelKnowledgeBase` 规则阈值诊断（`diagnostic_guide`/`get_alarms`）+ `RAGEngine`（TF-IDF，31 个知识块） |
| `knowledge/eel_knowledge.json` | 知识源 | 水质/病害/投喂/环境/问题 等知识条目，RAG 块的唯一数据来源 |
| `templates/index.html` | 页面 | 对话卡片 + 「LLM 服务设置」弹窗（前端逻辑全部内联） |
| `llm_settings.json`（运行时生成） | 用户配置存储 | **含明文 Key，已在 .gitignore，严禁提交** |
| `docs/patches/2026-09-04_LLM服务配置管理/` | 本次改动补丁 | before/after 对照 |

### app.py 中 LLM 相关路由

| 路由 | 方法 | 作用 |
|---|---|---|
| `/chat_ai` | POST | 自由对话（`ask_question`），一次性 JSON 返回 |
| `/get_ai_advice` | POST | 诊断报告（`get_advice`），一次性 JSON 返回 |
| `/llm_profiles` | GET | 方案列表（Key 打码）+ 当前生效状态 + 系统默认 |
| `/llm_profiles/save` | POST | 新增/更新方案；**更新的是当前启用项 → 同步热切换（保存即生效）** |
| `/llm_profiles/activate` | POST | 启用某方案：重建连接 + 持久化 active_id（重启仍生效） |
| `/llm_profiles/disable` | POST | 禁用自定义，回落到 config.py 系统默认 |
| `/llm_profiles/delete` | POST | 删除；若删的是启用项 → 自动回落默认 |
| `/llm_test` | POST | 1-token 探针测试连接，错误翻译成中文 |
| `/llm_models` | POST | 用 地址+Key 调 `GET /models` 拉取真实可用模型列表 |

---

## 3. 两条调用链

### 3.1 自由对话（`/chat_ai` → `ask_question`）

```
用户输入 → chat_ai(鉴权) → llm_advisor.ask_question(question, mcu_data)
        ├─ 规则诊断：kb.diagnostic_guide(temp,ph,oxy)        （本地规则，不进检索）
        ├─ RAG 检索：rag.retrieve(question+传感器, top_k=5)   （31 块 TF-IDF 打分取前 5）
        └─ 组装 messages → OpenAI chat.completions（stream=False, max_tokens=1024）
```

### 3.2 诊断报告（`/get_ai_advice` → `get_advice`）

同上，区别：
- RAG `top_k=4`，检索词固定为「水温X pHX 溶氧X 养殖管理建议」
- 用户消息以「请结合以上数据…综合评估」收尾
- 无 `temperature` 以下额外参数差异：`temperature=0.7, top_p=0.95`

### 3.3 运行时切服务（`/llm_profiles/activate` → `reconfigure`）

```
activate(id) → llm_settings.activate() 写 active_id
             → llm_advisor.reconfigure(base_url, api_key, model)
             → 用新三件套重建 OpenAI client（轻量对象，开销极小）
```
调用方（对话/诊断）始终只依赖 `self.client/self.model`，不感知切换 → **协议层零改动，热切换即生效**。

---

## 4. 每次请求真正发给 LLM 的「上下文」

> 关键认知：当前**没有多轮对话历史**。每次都是「系统提示 + 一次性拼装好的用户消息」，问完即忘（无状态单轮）。想让 AI「记得上文」属于待做功能（见 §6 建议 3）。

### 请求 messages 结构（自由对话为例）

```
system:  「你是一位资深的水产养殖专家…优先使用 Markdown…」     （约 130 字，固定）
user:    (当前环境参考：水温25.7℃, pH7.15, 溶解氧6.0mg/L)        ← 一行
         ---
         ## 当前数据诊断
         - 水温 25.7°C 适宜…                                    ← 规则引擎本地生成
         - pH 7.15 正常 …
         - 溶氧 6.0 mg/L 充足 …
         - 温度适宜范围… | pH 适宜范围… | 溶氧适宜范围…           （约 6~9 行）
         ---
         ## 相关知识库参考（RAG 检索）
         [water_quality] (相关度 0.xx) ……                       ← 5 个知识块
         [disease] (相关度 0.xx) ……
         ---
         用户的问题是：{用户原话}
```

### 规模估算（实测依据）

- 知识库共 **31 个块**（启动日志 `RAG 引擎就绪: 31 个知识块已索引`），由 `eel_knowledge.json` 拆分。
- 单块文本约几十~两三百字 → 对话注入 5 块 ≈ **0.5k~1.5k 字**；诊断注入 4 块 ≈ 0.4k~1.2k 字。
- 加上 system + 规则诊断 + 传感器行 + 用户问题：**单轮输入约 800~2000 token 量级**。
- 结论：输入规模不算大，**不是「慢」的主因**，但每轮都重新检索注入、无历史，输入 token 重复计费。

---

## 5. 「回答显示很慢」解剖

「慢」由 4 个因素叠加，按影响排序：

### 5.1 无流式输出（体感最大元凶）— 结构性
`ask_question`/`get_advice` 都用 `stream=False`，后端必须等 **整段回答生成完** 才一次性返回 JSON；
前端显示「正在思考...」期间一个字符都没有。整段等待时间被 100% 感知。

### 5.2 当前启用的模型是「旗舰/非快速档」
- 系统默认是 `deepseek-v4-flash`（快速低价档）；
- 但你在设置里启用的 **MiMo 方案 model = `mimo-v2.5`**（更接近旗舰推理型，非该平台 flash 档），
  生成速度与价格都高于 flash 档 → 这是本次体感变慢的直接原因之一。

### 5.3 生成长度上限 max_tokens=1024
回答偏长时（尤其 Markdown 报告/列表）生成耗时与长度近似线性。假设 30~50 token/s：
- 300 token ≈ 6~10s
- 800 token ≈ 16~27s

### 5.4 首 token 延迟（TTFT）
服务端排队 + 网络 RTT（国内直连 DeepSeek 通常 1~3s；海外/第三方中转会更慢）。

> 次要项：RAG TF-IDF 检索是本地毫秒级；规则诊断是纯本地——都不是瓶颈。

### 建议（按性价比排序，均为可选项，未擅自改动）

1. **模型换回 flash 档**：在设置里把 MiMo 模型换成该平台 flash 型号，或直接「禁用自定义」用默认 `deepseek-v4-flash` —— 立竿见影且省钱。
2. **对话改流式输出（打字机效果）**：新增 `/chat_ai_stream`（SSE：`stream=True` 逐段 `yield`），前端用 `fetch` 流式读取边收边渲染。这是消除「慢感」的根本手段（和 DeepSeek 官方网页同款体验）。
3. **若要「记住上文」**：加轻量会话历史（内存按会话存最近 N=6~10 轮），messages 前插历史。注意：历史会**线性放大输入** → 更慢更贵，需限制轮数与长度；可配合只保留最近的滑动窗口。
4. **利用输入缓存省钱**：各平台对重复前缀（system + 固定 RAG 注入）有 prompt cache 计费，把稳定前缀放前面、变化内容放后面，命中缓存可降成本（不直接提速度）。

---

## 6. 多方案管理设计要点（理解它，才能复用）

- **三件套抽象**：任意 OpenAI 兼容服务 = `base_url + api_key + model`，一套接口通吃所有服务商。
- **「启用项」持久化**：`llm_settings.json` 里 `active_id` 决定谁生效；启动时 `_apply_llm_active()` 自动恢复（删除失效项自动清理）。
- **明文只在后端**：出网一律 `mask_profile()`（前4 + **** + 后4）打码；编辑回传留空/打码 = 不修改 Key（`upsert` 内判断）。
- **保存即生效**：`save` 接口检测「改的是 active」→ 立即 `reconfigure`；启用/禁用同理。
- **防手填错模型**：`/llm_models` 调服务商 `GET /models` 拉真实列表，前端「获取模型」下拉选择。
- **错误可读化**：`_llm_err_message()` 把 openai 异常（401/403/404/429/连接失败）翻译成中文提示，前端状态条红绿反馈。
- **Key 安全**：`llm_settings.json` 与 `.env` 均已入 `.gitignore`。

> 复用经验：这套「网页填 地址+Key+模型 → 多方案保存/启用/禁用 → 测试连接 → 获取模型」的通用模式，我另写了可迁移的要点总结到 `scratch/LLM服务配置功能复用要点.md`，适合搬到以后任意带 Web 设置的项目。

---

## 7. 运维 / 安全注意事项

- 修改 `core/*.py` 或页面后，**重启 Flask 生效**；方案切换本身不需重启。
- 若手改 `llm_settings.json` 记得保持 UTF-8 合法 JSON（建议走界面，不手改）。
- `config.py` 默认三件套仍可被 `.env`/代码控制 —— 「禁用自定义」即回到它。
- 补丁 `docs/patches/2026-09-04_LLM服务配置管理/` 记录了本次完整 before/after。

---

## 8. 后续可做（供排期）

- [x] 对话流式输出（SSE 打字机）（2026-09-05 已实现，见补丁 `docs/patches/2026-09-05_对话报告流式打字机`；实测流式首字 ~0.99s vs 非流式一次性 ~13.5s）
- [x] 诊断报告也走流式（2026-09-05 一并实现 `/get_ai_advice_stream`）
- [ ] 会话历史记忆（滑动窗口 N 轮）
- [ ] 界面加「当前生效模型」角标（对话卡片顶部），避免忘记用着哪套服务
- [ ] Key 加密落盘（如 DPAPI）或完全走环境变量
