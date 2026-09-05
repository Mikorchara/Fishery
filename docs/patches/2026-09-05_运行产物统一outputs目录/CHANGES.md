# 修改日期：2026-09-05
# 修改人：AI（用户确认）

## 修改文件
- `app.py`
- `templates/index.html`
- `Z_script/clean_outputs.ps1`
- `Z_script/start_all.ps1` / `Z_script/start_all_with_sensor.ps1`（推流源目录）
- `.gitignore`
- `docs/structure.md` / `docs/deep-dive/outputs.md` / `docs/env_check_plan.md` / `AGENTS.md`
- 目录：`captures/`、`recordings/` 已迁移删除 → 新建 `outputs/{images,videos,chats}`

> 说明：本次改动叠加在本会话未提交的工作区之上，无法在补丁中完整还原"精确 before"；
> 相关文件修改前状态可参考本会话前几个补丁的 `after/`（如 `2026-09-05_mediamtx迁入tools`），
> 最终以 git diff / git 提交留痕为准。本目录仅保留 CHANGES 记录。

## 修改原因
- 截图（captures/）与录像（recordings/）并存于服务器本地，网页无法浏览回看。
- 顶层输出目录分散，用户希望图片/视频合并在一个目录下用子文件夹分类，并新增存放 AI 对话文本的目录。
- 为后续「记录回看」网页面板与「记忆/参考」功能提供落盘数据。

## 修改内容
1. **目录统一**：新建 `outputs/images`（原 captures/）、`outputs/videos`（原 recordings/）、`outputs/chats`（新增）。
   - `app.py`：`CAPTURES_DIR/RECORDINGS_DIR` 改指向 `outputs/images|videos`，新增 `CHATS_DIR`；
     截图/录制写文件端点无需改（沿用原变量名）。
   - 旧数据已迁移：captures/*、recordings/* → outputs/images、outputs/videos，旧目录已删。
2. **对话/报告落盘 Markdown**：新增 `_save_exchange_md(kind, question, answer, snapshot)`，
   每次对话/诊断报告完成（流式 + 非流式端点均接）后写入 `outputs/chats/chat_{ts}.md` /
   `report_{ts}.md`，含时间、类型、当前模型、环境快照（报告）、用户提问与完整回复。
   `_sse` 增加 kind/question 参数，流式结束时自动落盘。文件默认保留（`clean_outputs -All` 才删）。
3. **前端占位**：`templates/index.html` 视频画面下方新增「记录回看」折叠卡片（占位，待接入），
   供用户确认位置是否合适；暂未实现列表/回放 API 与 UI。
4. **脚本/文档同步**：clean_outputs 改清 `outputs/images|videos`（chats 与 data.db 同走 -All）；
   start_all* 推流源候选 `recordings/` → `outputs/videos/`；.gitignore `captures/ recorders/` → `outputs/`；
   相关文档目录树与产物说明同步。

## 影响范围
- 截图/录像落盘位置变化（captures/recordings → outputs/images/videos），旧文件已迁移；
  页面截图/录制按钮行为不变。
- AI 对话/报告开始自动留档（含模型名与环境快照），属新增行为，不影响回显。
- 「记录回看」占位卡为纯静态占位，不影响现有布局功能（可折叠；专注模式会随视频区隐藏）。

## 验证
- `python -m py_compile app.py`：OK（仅编译，未触发 import / 联网 / LLM 调用）。
- 6 个 ps1：AST 语法 0 错误；BOM 保留。
- app.py 目录常量引用一致（capture→images、record→videos、落盘→chats）。

## 备注（待办）
- 「记录回看」完整功能（文件清单 API + 静态访问白名单 + 前端缩略图/播放/对话查看）未实现，
  占位卡位置待用户确认后可继续。
- 对话/报告 .md 需真实跑一次对话/报告后才会生成（本会话未触发任何付费 LLM 调用）。
