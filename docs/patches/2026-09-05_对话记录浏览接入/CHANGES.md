# 修改日期：2026-09-05
# 修改人：AI（用户确认）

## 修改文件
- `app.py`（新增 4 个对话记录管理端点）
- `templates/index.html`（视频状态布局修复 + 记录回看左侧对话浏览 + 右键菜单）

> 说明：改动叠加在本会话未提交工作区之上，before/after 以 git diff 为准，本目录仅 CHANGES。

## 修改原因
- 用户确认记录回看布局符合预期，接入左侧「对话记录」浏览。
- 命名方案：自动存档文件保持 `chat/report_YYYYMMDD_HHMMSS.md`（秒级避免同分钟覆盖）；
  列表默认显示名 = **时间（精确到分钟）**；重命名后显示自定义名；同分钟多条自动加序号。
- 修复：视频标题栏 记录回看/截图/录制 三按钮随状态文字变化左右移动的问题。

## 修改内容
1. 后端（app.py，均在 `outputs/chats` 范围内、文件名 basename 校验防穿越）：
   - `GET /media_api/chats`：列出对话/报告 .md（mtime 倒序，含 time_str/size）。
   - `GET /media_api/chat?name=`：读取单个 .md 原文（Markdown）。
   - `POST /media_api/chat/delete`：删除（前端 confirm 二次确认）。
   - `POST /media_api/chat/rename`：重命名（自动补 .md、拒绝非法字符/重名）。
2. 前端（index.html）：
   - **按钮抖动修复**：把 `#statusIndicator` 从右侧按钮组移到左侧标题旁
     （`.video-status`：nowrap/ellipsis + max-width），右侧按钮组固定、`flex-shrink:0`，
     录制按钮固定宽 78px —— 状态文字变化不再挤压按钮 → 不再左右移动。
   - 记录回看左卡改为 `#chatList` 对话列表：条目显示 默认时间(分钟) + 类型/秒；
     左键查看、右键弹出自定义菜单（重命名 / 删除），Esc/点空白关闭。
   - 右侧卡拆两个面板：`#mediaPane`（图片/视频 tab 网格）与 `#chatPane`（对话文本查看，
     marked 渲染 .md；标题栏含「返回记录列表」回到媒体面板；「返回监控」随时可回主界面）。
   - 进入记录回看时 `exitChatReader()` 复位到媒体面板，并同时加载媒体 + 对话列表。

## 影响范围
- 对话/报告自动落盘行为不变（仍写 outputs/chats）；新增可浏览/重命名/删除。
- 视频标题栏布局调整（状态文字在左），不影响功能；按钮不再随状态文字移动。

## 验证（真机冒烟，未触碰真实记录）
- `python -m py_compile app.py` OK。
- 系统启动后：
  - `/media_api/chats` 返回真实记录 `chat_20260905_234959.md`；
  - `/media_api/chat?name=...` 正确返回 Markdown 原文；
  - 用临时 `_smoke_test.md` 验证 rename → `_smoke_renamed.md`、delete 均 success，临时文件已清理；
  - 浏览器实测：记录回看 → 左侧显示「2026-09-05 23:49 · 对话」，右侧图片缩略图网格正常；
    点对话条目右侧完整渲染 Markdown（表格/列表/标题）。
- 测试后清理：5000/8554 空闲，无 mediamtx/ffmpeg/python 残留。

## 备注
- 视频状态放左侧后若极端长文案可被 ellipsis 截断（max-width 260px），属预期。
- 删除采用直接删文件（无回收站），前端有 confirm；如需回收站可后续加。
