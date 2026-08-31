# Draw.io 批量导出脚本
# 使用方法：
#   1. 安装 draw.io 桌面版: https://github.com/jgraph/drawio-desktop/releases
#   2. 修改 $DrawioExe 路径为实际安装路径
#   3. 运行: pwsh scripts/export_drawio.ps1

param(
    [string]$DrawioExe = "C:\Program Files\draw.io\draw.io.exe",
    [string]$DrawioDir = "thesis-ai-standard\drawio",
    [string]$ExportDir = "thesis-ai-standard\exports"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $DrawioExe)) {
    $altPaths = @(
        "$env:LOCALAPPDATA\Programs\draw.io\draw.io.exe",
        "$env:ProgramFiles\draw.io\draw.io.exe",
        "${env:ProgramFiles(x86)}\draw.io\draw.io.exe"
    )
    $found = $false
    foreach ($p in $altPaths) {
        if (Test-Path $p) {
            $DrawioExe = $p
            $found = $true
            break
        }
    }
    if (-not $found) {
        Write-Host "ERROR: draw.io not found at $DrawioExe"
        Write-Host "Please install draw.io desktop from: https://github.com/jgraph/drawio-desktop/releases"
        Write-Host "Or specify path: pwsh scripts/export_drawio.ps1 -DrawioExe 'C:\path\to\draw.io.exe'"
        exit 1
    }
}

Write-Host "Using draw.io: $DrawioExe"

if (-not (Test-Path $ExportDir)) {
    New-Item -ItemType Directory -Path $ExportDir -Force | Out-Null
}

$drawioFiles = Get-ChildItem -Path $DrawioDir -Filter "*.drawio" | Where-Object { $_.Name -match "^figure-" }

Write-Host "Found $($drawioFiles.Count) figure files to export`n"

foreach ($file in $drawioFiles) {
    $baseName = [IO.Path]::GetFileNameWithoutExtension($file.Name)
    $outputPath = Join-Path $ExportDir "$baseName.png"

    Write-Host "Exporting: $($file.Name) -> $baseName.png"

    & $DrawioExe --export --format png --scale 2 --output $outputPath $file.FullName --no-sandbox 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0 -and (Test-Path $outputPath)) {
        Write-Host "  OK (scale 2x)" -ForegroundColor Green
    } else {
        Write-Host "  Retrying without scale..." -ForegroundColor Yellow
        & $DrawioExe --export --format png --output $outputPath $file.FullName --no-sandbox 2>&1 | Out-Null
        if (Test-Path $outputPath) {
            Write-Host "  OK" -ForegroundColor Green
        } else {
            Write-Host "  FAILED" -ForegroundColor Red
        }
    }
}

Write-Host "`nExport complete. Files in: $ExportDir"
