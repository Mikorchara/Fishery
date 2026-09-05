# clean_outputs.ps1 — 集中清理项目运行产出文件
#
# 用法（在项目根下执行；脚本用 $PSScriptRoot 自动定位项目根）：
#   .\Z_script\clean_outputs.ps1                     # 清理日志/截图/录像/基准/__pycache__
#   .\Z_script\clean_outputs.ps1 -All                # 额外删除 data.db（传感器历史）
#   .\Z_script\clean_outputs.ps1 -KeepRecordings 3   # 录像保留最新 3 个
#   .\Z_script\clean_outputs.ps1 -WhatIf             # 预览模式：只显示将删除的内容，不执行
#
# 注意：
#   - 本文件必须 UTF-8 with BOM 保存（否则 Windows PowerShell 5.1 中文乱码解析失败）
#   - 绝不会删除 .venv / models / 源码 / test_video*.mp4（推流依赖）

param(
    [switch]$All,               # 同时删除 data.db（传感器历史）
    [switch]$WhatIf,            # 预览模式，不真正删除
    [int]$KeepRecordings = 0    # 保留最新 N 个录像（0 = 全删）
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent   # Z_script 的上一级 = 项目根
Set-Location $Root

$script:count = 0
$script:freed = [long]0

function Remove-Target {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [bool]$IsDir
    )
    if (-not (Test-Path $Path)) { return }
    if ($IsDir) {
        $size = (Get-ChildItem $Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    } else {
        $size = (Get-Item $Path).Length
    }
    $script:count++
    $script:freed += $size
    Write-Host ("  - {0}  ({1:N2} MB)" -f $Path, ($size / 1MB))
    if (-not $WhatIf) {
        if ($IsDir) { Remove-Item $Path -Recurse -Force } else { Remove-Item $Path -Force }
    }
}

Write-Host ("模式: {0} | 保留录像: {1}" -f $(if ($WhatIf) { '预览(不删除)' } else { '实际清理' }), $KeepRecordings) -ForegroundColor Cyan
Write-Host ""

# 1. 日志文件（app.log 等）
Write-Host "[1/4] 日志 *.log" -ForegroundColor Cyan
Get-ChildItem $Root -Filter *.log -File -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Target $_.FullName $false
}

# 2. 截图 + 录像
Write-Host "[2/4] captures / recordings" -ForegroundColor Cyan
Remove-Target "$Root\captures" $true
if ($KeepRecordings -gt 0 -and (Test-Path "$Root\recordings")) {
    Get-ChildItem "$Root\recordings" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip $KeepRecordings |
        ForEach-Object { Remove-Target $_.FullName $false }
} else {
    Remove-Target "$Root\recordings" $true
}

# 3. 基准输出
Write-Host "[3/4] bench_output" -ForegroundColor Cyan
Remove-Target "$Root\bench_output" $true

# 4. SQLite 数据库（可选）
Write-Host "[4/4] data.db" -ForegroundColor Cyan
if ($All) {
    Remove-Target "$Root\data.db" $false
    Remove-Target "$Root\data.db-shm" $false
    Remove-Target "$Root\data.db-wal" $false
} else {
    Write-Host "  - 跳过 data.db（加 -All 才删除）" -ForegroundColor DarkGray
}

# 附加：__pycache__（不碰 .venv 里的）
Write-Host "[附加] __pycache__" -ForegroundColor Cyan
Get-ChildItem $Root -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\.venv' } |
    ForEach-Object { Remove-Target $_.FullName $true }

Write-Host ""
Write-Host ("完成：共 {0} 项，释放 {1:N2} MB" -f $script:count, ($script:freed / 1MB)) -ForegroundColor Green
if ($WhatIf) { Write-Host "（预览模式，未实际删除。去掉 -WhatIf 后执行）" -ForegroundColor Yellow }
