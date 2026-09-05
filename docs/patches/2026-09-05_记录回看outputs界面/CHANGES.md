# 修改日期：2026-09-05
# 修改人：AI（用户确认）

## 修改文件
- `app.py`（新增 3 个记录回看端点）
- `templates/index.html`（移除底部占位卡、加跳转按钮、新增 outputs 视图 + JS）

> 说明：改动叠加在本会话未提交工作区之上，before/after 以 git diff 为准，本目录仅 CHANGES。

## 修改原因
- 用户否决"占位卡放视频底部"的样式；改为视频区标题栏一个「记录回看」按钮，跳转到独立 outputs 界面。
- 布局：左「对话记录」（本次仅空壳，浏览功能待接入）、右「现场记录」（图片/视频 tab 切换、缩略图、点击用系统默认查看器打开）。
- 用户决策：后端对话/报告自动落盘 **保留**（C 方案），仅页面对话浏览本次不做。

## 修改内容
1. `app.py`：
   - `/media_api/list`：返回 outputs 截图/录像清单（时间倒序，含 name/url/size/time）。
   - `/media/<cat>/<fname>`：白名单目录内文件访问（<img>/<video> 缩略图用；单层文件名防穿越）。
   - `/media/open`（POST）：`os.startfile` 用 Windows 默认查看器打开指定截图/录像。
2. `templates/index.html`：
   - 移除上轮 video-wrapper 下方「记录回看」占位卡。
   - 视频区标题栏（截图/录制旁）新增「记录回看」按钮 → `enterRecordsView()`。
   - 新增 `#recordsView`（独立视图，默认隐藏）：左 `对话记录` 折叠卡（空壳提示）；
     右 `现场记录` 卡：`图片 | 视频` 切换 + `返回监控` 按钮 + 缩略图网格
     （图片 `<img>`、视频 `<video preload=metadata>` 首帧缩略；点击调 `/media/open` 用系统查看器打开）。
   - 相关 CSS（media-grid/media-item/media-tabs）与 JS（enter/exit/switch/render/open）。

## 影响范围
- 实时监控页布局恢复（无底部占位卡）；仅标题栏多一个按钮。
- 新增记录回看视图不影响现有卡片折叠/专注模式；进入时会先退出专注模式。
- 对话/报告继续自动落盘 `outputs/chats/*.md`（未改动）；页面对话区留待后续接入。

## 验证（真机端到端）
- `python -m py_compile app.py` OK；6 个 ps1 AST 0 错误、BOM 保留。
- `Z_script\start_all_with_sensor.ps1` 真实启动：
  - mediamtx 进程路径 = `tools\mediamtx\mediamtx.exe` ✓
  - ffmpeg 进程路径 = `tools\ffmpeg\bin\ffmpeg.exe` ✓（推流 test_video.mp4 无报错）
  - Flask 正常（模型/SAM2/WWE-UIE/RAG 加载成功，`LLM 启用 Q_1 → qwen3.5-flash`，未触发付费调用）
  - `/health` 200；`/media_api/list` 返回迁移的旧截图/录像；`/media/images/xxx.jpg` 200 image/jpeg
  - `POST /capture_frame` 截图 → 新文件写入 `outputs/images/capture_20260905_233809.jpg`（落盘路径正确）
- 测试后已清理：端口 5000/8554 空闲，无 mediamtx/ffmpeg/python 残留。

## 备注
- `outputs/images/capture_20260905_233809.jpg` 为验证时生成的演示截图，可保留展示或删除。
- 待办：左侧「对话记录」浏览（读 outputs/chats/*.md）后续接入。
