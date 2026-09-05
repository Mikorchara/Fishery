# 修改日期：2026-09-06
# 修改人：AI（用户确认）

## 修改文件
- `app.py`（截图/录像时间命名 + 媒体文件 删除/重命名 端点 + 防穿越修正）
- `templates/index.html`（缩略图右键菜单 + 时间标签）
- `docs/deep-dive/outputs.md`
- 已删除：`outputs/images/`、`outputs/videos/` 下现有截图与录像（用户要求清空重新开始）

> 说明：改动叠加在本会话未提交工作区之上，before/after 以 git diff 为准。

## 修改原因
- 用户希望截图/录像直接用时间命名（去掉 `capture_`/`record_` 前缀），简洁直观、按时间可读。
- 已删除现有图片/视频，重新开始记录。
- 需要像对话记录一样支持对图片/视频缩略图右键「重命名 / 删除」。

## 修改内容
1. 命名：截图 `capture_{ts}.jpg` → `{ts}.jpg`；录像 `record_{ts}.mp4` → `{ts}.mp4`
   （`ts = YYYYMMDD_HHMMSS`，秒级避免同分钟覆盖；列表缩略图下方显示为可读 `YYYY-MM-DD HH:MM:SS`）。
2. 后端（`app.py`，均 basename 校验防穿越）：
   - `POST /media_api/file/delete`：删除指定 cat（images/videos）下的文件。
   - `POST /media_api/file/rename`：重命名（保留原扩展名、拒绝非法字符/重名）。
   - 对话记录的重命名 `/media_api/chat/rename` 同步修正。
3. 前端（`templates/index.html`）：
   - 缩略图「右键」弹出与对话共用的菜单（重命名 / 删除）；左键仍系统查看器打开。
   - 右键菜单改为按上下文分发（对话 or 媒体），操作成功后刷新对应列表。
   - 缩略图下方标签对时间命名显示可读时间。
4. 安全修正：冒烟测试发现重命名端点对含路径分隔的输入（如 `bad/name`）会
   `os.path.basename` 静默剥壳成 `name` 而非拒绝 —— 已改为**显式 400 拒绝**（媒体与对话 rename 都修）。

## 影响范围
- 截图/录像落盘文件名变化（去掉前缀）；记录回看列表自动跟随。
- 图片/视频可右键重命名/删除（删除有确认，直接删文件无回收站）。

## 验证
- `python -m py_compile app.py` OK。
- 真机冒烟：`/media_api/file/rename`（临时文件 → success）、`/media_api/file/delete`（success）均正常；
  非法字符 `bad/name` 修复后离线校验为「拒绝」（`..\x.jpg` 同样拒绝）。
- 清理：测试临时文件已删；仅保留用户运行期间截图 `outputs/images/20260906_002142.jpg`；5000/8554 空闲、无残留进程。

## 备注
- 删除无回收站（前端 confirm 二次确认）；如需回收站可后续加。
