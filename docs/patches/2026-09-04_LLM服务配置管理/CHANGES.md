# 修改日期：2026-09-04
# 修改人：[AI]

## 修改文件
- `core/llm_advisor.py`
- `app.py`
- `templates/index.html`
- `.gitignore`
- 新增 `core/llm_settings.py`

## 修改原因
- 让用户能像 VS Code AI 插件一样，在网页设置界面「地址 + Key + 模型」即可接入任意 OpenAI 兼容的 LLM 服务（DeepSeek / 小米 MiMo / 其他），
  并可在多套已保存方案间自由切换 / 禁用回落系统默认，全程无需改代码或重启。

## 修改内容
- 新增 `core/llm_settings.py`：多方案(profile)管理 —— 新增/更新/删除/启用/禁用、持久化到
  `llm_settings.json`（含 Key，已在 .gitignore），Key 回传前端一律打码。
- `core/llm_advisor.py`：`__init__` 改为默认三件套；新增 `reconfigure(base_url, api_key, model)`
  支持运行时热切换（api_key 空 → client=None，对话提示“未启用”）。
- `app.py`：新增 6 个接口（全部走 Bearer 鉴权）：
  - `GET /llm_profiles` 列出方案（脱敏）+ 当前生效状态 + 系统默认
  - `POST /llm_profiles/save` 新增/更新；若更新的正是启用项则同步热切换（保存即生效）
  - `POST /llm_profiles/activate` 启用某方案（立即生效并持久化，重启后仍生效）
  - `POST /llm_profiles/disable` 禁用自定义，回落 config.py 系统默认
  - `POST /llm_profiles/delete` 删除（若删的是启用项自动回落默认）
  - `POST /llm_test` 1-token 探针测试连接（openai 异常翻译成中文提示；Key 留空可复用已存 Key）
  - `POST /llm_models` 用 地址+Key 从服务商拉取真实可用模型列表（避免手填错 model）
  - 启动时调用 `_apply_llm_active()` 恢复上次启用的方案。
- `templates/index.html`：页面顶部加「LLM 服务设置」按钮 + 配置弹窗（服务预设下拉 / 名称 /
  Base URL / API Key / 模型 ID + 获取模型 + 测试连接 + 保存 / 保存并启用 / 禁用 + 生效状态提示）。

## 影响范围
- AI 智慧对话 / 实时诊断报告的 LLM 调用（底层仍是 `llm_advisor`，接口不变，无 key 时行为同旧逻辑）。
- 视觉模型（YOLO/分割）配置完全不受影响。
