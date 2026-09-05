# 修改日期：2026-09-05
# 修改人：AI（用户确认）

## 修改文件
- `Z_script/start_all.ps1`
- `Z_script/clean_outputs.ps1`
- `Z_script/start_all_with_sensor.ps1`（仅注释）
- `Z_script/start_pc_camera.ps1`（仅注释）
- `Z_script/start_usb_camera.ps1`（仅注释）
- `Z_script/check_env.ps1`（仅注释）

## 修改原因
- 项目可能被拷贝到其它盘符/路径，但部分脚本仍硬编码 `D:\Fishery_Project`，
  造成"强制要求在 D 盘"才能运行。
- `2026-09-03_脚本整理到Z_script` 补丁只统一了一半：当时 4 个 start/check 脚本已用
  `Split-Path $PSScriptRoot -Parent` 自动定位，但 `start_all.ps1`、`clean_outputs.ps1`
  的 `$Root` 仍写死为 `D:\Fishery_Project`。

## 修改内容
- `start_all.ps1`：`$Root = "D:\Fishery_Project"` → `$Root = Split-Path $PSScriptRoot -Parent`
- `clean_outputs.ps1`：同上
- 6 个脚本头部「用法」注释中的 `D:\Fishery_Project / d:\...\Z_script\...` 绝对路径示例，
  统一改为通用相对写法（只影响文档注释，不影响逻辑）。

## 影响范围
- 所有 `Z_script\*.ps1` 现均可从任意盘符/路径运行（前提：脚本仍位于 `Z_script\` 子目录，
  项目根 = `$PSScriptRoot` 上一级）。
- 行为无变化；已验证语法：`$PSScriptRoot` 为脚本内建变量，定位逻辑与其余脚本完全一致。

## 备注
- `export_drawio.ps1` 为论文项目（thesis-ai-standard）的孤儿脚本，引用的
  `thesis-ai-standard\drawio` 目录在本项目不存在，未纳入本次修改（待用户决定去留）。
- Python 源码无硬编码 D 盘路径。
