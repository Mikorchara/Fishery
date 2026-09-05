# 修改日期：2026-09-05
# 修改人：AI（用户确认）

## 修改文件
- `Z_script/export_drawio.ps1`（已删除）

## 修改原因
- 该脚本是论文项目（thesis-ai-standard）的孤儿工具，引用的 `thesis-ai-standard\drawio`
  与 `thesis-ai-standard\exports` 目录在本项目不存在，且依赖 draw.io 桌面版安装路径，
  与智慧渔业系统无关，混在 `Z_script/` 会造成困惑。

## 修改内容
- 删除 `Z_script/export_drawio.ps1`（完整原文保留于本目录 `before/`）

## 影响范围
- 仅移除无关脚本；其余 `Z_script` 启动/检查脚本不受影响。
- 若论文项目仍需要，可从 `before/` 找回或另行归档。
