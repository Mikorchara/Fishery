# 修改日期：2026-09-05
# 修改人：AI（用户确认）

## 修改文件
- `Z_script/start_all.ps1`
- `Z_script/start_all_with_sensor.ps1`
- `Z_script/start_pc_camera.ps1`
- `Z_script/start_usb_camera.ps1`
- `Z_script/check_env.ps1`
- 新增：`tools/ffmpeg/bin/ffmpeg.exe`（不入 git）

## 修改原因
- 实践中很多用户不知道 / 未安装 ffmpeg，导致推流步骤跑不起来。
- 决定方案 A：项目自带一份 ffmpeg，脚本优先使用本地版本，找不到再回退系统 PATH，
  实现"零额外安装"开箱即用（与 mediamtx 自带 exe 的做法一致）。

## 修改内容
- 从系统 PATH（`D:\FFmpeg\ffmpeg-2026-07-30-git-2ae2413488-full_build\bin\ffmpeg.exe`，
  gyan.dev 每日 full 静态构建，单文件无 DLL 依赖，208MB）复制到
  `tools/ffmpeg/bin/ffmpeg.exe`。
- 5 个脚本新增探测逻辑（置于 `$Root` 定位之后）：
  ```powershell
  # ffmpeg：优先用项目内自带 (tools\ffmpeg\bin)，找不到回退系统 PATH
  if (Test-Path "$Root\tools\ffmpeg\bin\ffmpeg.exe") { $ffmpegExe = "$Root\tools\ffmpeg\bin\ffmpeg.exe" }
  else { $ffmpegExe = "ffmpeg" }
  ```
- `start_all.ps1` / `start_all_with_sensor.ps1`：推流 `Start-Process -FilePath "ffmpeg"` → `$ffmpegExe`
- `start_pc_camera.ps1` / `start_usb_camera.ps1`：`Test-Camera` 内 `& ffmpeg` → `& $ffmpegExe`；
  推流 `Start-Process -FilePath $ffmpegExe`
- `check_env.ps1`：ffmpeg 检测改为"本地 `tools\ffmpeg\bin` → PATH"两级探测；
  摄像头枚举 `& ffmpeg` → `& $ffmpeg`
- `.gitignore` 新增排除 `tools/ffmpeg/`

## 影响范围
- 所有启动/检查脚本在 ffmpeg 缺失环境下仍可运行（回退 PATH），有本地版时自动优先。
- 行为无变化；AST 语法校验 0 错误，BOM 保留。
- 新增约 208MB 本地体积（不入 git，不影响仓库大小）。

## 备注
- ffmpeg 体积提示：gyan.dev 每日 full 构建约 208MB；如需更小可换
  release-essentials 静态版（约 80MB，LGPL，含 libx264，足够本项目推流）。
- mediamtx 位置是否同样迁到 `tools/` 见主对话（未做，保持 `mediamtx/`）。
