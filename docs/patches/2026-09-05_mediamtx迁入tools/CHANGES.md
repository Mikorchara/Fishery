# 修改日期：2026-09-05
# 修改人：AI（用户确认）

## 修改文件
- 目录迁移：`mediamtx/` → `tools/mediamtx/`（含 exe/yml/License/auto.crt/auto.key，原目录已删）
- `Z_script/start_all.ps1`
- `Z_script/start_all_with_sensor.ps1`
- `Z_script/start_pc_camera.ps1`
- `Z_script/start_usb_camera.ps1`
- `Z_script/check_env.ps1`
- `.gitignore`
- `docs/structure.md` / `docs/BUILD_RUN.md` / `AGENTS.md`

## 修改原因
- 第三方工具统一归拢到 `tools/`：ffmpeg 已在 `tools/ffmpeg/`，mediamtx 归入 `tools/mediamtx/`，
  目录职责更清晰（`tools/` = 所有第三方依赖）。

## 修改内容
- 移动 `mediamtx/` 全部内容到 `tools/mediamtx/`，删除旧目录。
- 5 个脚本中 `$Root\mediamtx\mediamtx.exe` → `$Root\tools\mediamtx\mediamtx.exe`，
  `WorkingDirectory` 同步；check_env 检测路径同步。
- `.gitignore`：`mediamtx/mediamtx.exe` 等 → `tools/mediamtx/mediamtx.exe` / auto.crt / auto.key
  （yml / LICENSE 仍为文本入库）。
- 文档同步：AGENTS 手动终端 1 的 `cd ...\mediamtx` → `cd ...\tools\mediamtx`；
  BUILD_RUN 解压说明 → `tools/mediamtx/`；structure.md 目录树合并为 `tools/`（含 mediamtx + ffmpeg）。

## 影响范围
- mediamtx 从 `$Root\mediamtx` 移到 `$Root\tools\mediamtx`，所有启动/检查脚本已同步；
  `mediamtx.yml` 内 `logFile: mediamtx.log` 为相对路径，随 WorkingDirectory 落盘，不受影响。
- 验证：AST 语法 0 错误；`git check-ignore` 生效；`tools\mediamtx\mediamtx.exe --version` → v1.19.1。
