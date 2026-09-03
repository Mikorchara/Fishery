# 修改日期：2026-09-03
# 修改人：GitHub Copilot（用户确认）

## 修改文件
- `start_all.ps1`（移动到 `Z_script/`，内容不变）
- `check_env.ps1`（移动到 `Z_script/`，改动默认根目录逻辑）
- `clean_outputs.ps1`（移动到 `Z_script/`，内容不变）
- `scripts/export_drawio.ps1`（移动到 `Z_script/`，仅改注释路径）
- 新增 `Z_script/start_pc_camera.ps1`、`Z_script/start_usb_camera.ps1`
- 引用更新：`AGENTS.md`、`README.md`、`docs/BUILD_RUN.md`、`docs/env_check_plan.md`、`docs/structure.md`、`docs/troubleshooting.md`、`docs/ROADMAP.md`、`docs/deep-dive/outputs.md`

## 修改原因
用户要求：项目根新建 `Z_script/` 统一收纳所有 PowerShell 脚本，并为真实摄像头（电脑内置 / 外接 USB）各建一个启动脚本。

## 修改内容
- 新建 `Z_script/`，把根目录 3 个 + `scripts/` 1 个共 4 个 .ps1 移入；根目录不再留 .ps1。
- `check_env.ps1`：因脚本移入子目录，默认项目根由 `$PSScriptRoot` 改为 `Split-Path $PSScriptRoot -Parent`（否则找不到 `.venv`/`models`）；用法注释与输出提示同步加 `Z_script\` 前缀。
- 新增 `start_pc_camera.ps1`：默认设备 `HP Wide Vision HD Camera`（720p@30），三步结构与 `start_all.ps1` 一致，但 ffmpeg 用 dshow 实时采集并重编码 H.264。
- 新增 `start_usb_camera.ps1`：默认设备 `USB Video Device`（720p@10），逻辑同上。
- 两个摄像头脚本均带：设备存在性预检（`-DeviceName` 可覆盖）、mediamtx 已在运行则跳过启动（避免误关他人进程）、finally 只清理本次启动的进程。
- 全部文档中的脚本路径引用更新到 `Z_script\`，并登记两个摄像头脚本。

## 影响范围
- 启动/自检/清理命令路径变化：`.\start_all.ps1` → `.\Z_script\start_all.ps1`，`check_env.ps1` → `Z_script\check_env.ps1` 等（各文档已同步）。
- 功能逻辑未变：`start_all.ps1`、`clean_outputs.ps1` 内容原样迁移。
- 新脚本为新增文件，未改动 `app.py` / `core/*` 等 Python 代码。
