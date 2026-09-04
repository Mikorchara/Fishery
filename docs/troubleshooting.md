# 已知问题与踩坑记录

> 修改代码前必读。遇到问题先来这里查。

## 1. Z_script 下 PowerShell 脚本必须为 UTF-8 with BOM 编码

- **现象**：脚本一运行就报"字符串缺少终止符"，所有进程都没启动，浏览器打不开。
- **原因**：Windows PowerShell 5.1（`powershell`）会把无 BOM 的 .ps1 按 ANSI(GBK) 读取，中文注释乱码破坏引号，导致整脚本解析失败。
- **解决**：文件保存为 UTF-8 with BOM（或用 pwsh 7 运行）。
- **验证**：用 `powershell -NoProfile -ExecutionPolicy Bypass -File Z_script\start_all.ps1` 实测（勿只用 pwsh 解析，测不出 5.1 的问题；`Z_script/` 下所有 .ps1 同理）。

## 2. AI 报告在网页上无法正常显示（部分修复）

- **现象**：AI 诊断/对话内容空白，或只显示 `**加粗**`、`## 标题` 等原始 Markdown。
- **原因与状态**：
  - ✅ **CDN marked.js 被墙**（cdn.jsdelivr.net）→ 已修复（2026-08-31）：marked.min.js 下载到 `static/js/marked.min.js` 本地化，并加 `simpleMd()` 极简兜底渲染。
  - ⏳ **DeepSeek thinking 模式 content 可能为空**（内容在 `reasoning_content`）→ 仍待确认/处理。
- **备注**：曾实现"空 content 回退"修复后已撤销；需要时可按 `docs/patches/2026-08-31_修复AI报告Markdown显示/` 里的方案重新应用。

## 3. ffmpeg 手动安装后新终端找不到

- 每个新终端需先刷新 PATH：
  `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")`
- 一键启动脚本已内置此逻辑。

## 4. 一键启动退出后可能残留 mediamtx / ffmpeg

- **现象**：脚本被强杀（非 Ctrl+C）时，隐藏窗口的 mediamtx/ffmpeg 可能残留，导致端口 8554/5000 被占用。
- **检查/清理**：
  ```powershell
  Get-Process mediamtx,ffmpeg -ErrorAction SilentlyContinue | Stop-Process -Force
  ```

## 5. 敏感文件切勿提交（.env）

- `.env` 含 `DEEPSEEK_API_KEY`，已被 `.gitignore` 排除。
- 注意：`docs/patches/2026-07-30_环境初始化与Bug修复/after/.env` 是真实 .env 的备份，同样含密钥，**不要**为了"完全上传 docs"而放开 `.env` 忽略规则。

## 6. README.md 与 AGENTS.md 环境信息不一致

- README 写的是 conda + Python 3.9（过时）；当前以 AGENTS.md 为准：venv + Python 3.11。

## 7. Flask 默认静态目录是项目根 static/

- **现象**：`<script src="/static/js/xxx.js">` 返回 404。
- **原因**：Flask 默认 static 路由指向**项目根** `static/` 目录，不是 `templates/static/`。
- **解决**：静态文件放项目根 `static/` 下（2026-08-31 已将 marked.min.js 放在 `static/js/marked.min.js`）。

## 8. onnxruntime / ONNX 模型 GPU 运行（已解决 2026-09-03）

- **现象**：网页/脚本加载 `.onnx` 模型崩溃，或报 `onnxruntime ... require CUDA 13 ...` / `There's no data transfer registered`；或被迫走 CPU 极慢。
- **根因**：
  - **onnxruntime-gpu 不捆绑 CUDA 库**——它运行时要找 cublas / cuDNN；PyTorch 是自带 CUDA 运行时的，所以"PyTorch 能 GPU ≠ onnxruntime 能 GPU"。
  - ultralytics 的 **AutoUpdate** 会自动联网补依赖：曾误装**最新 onnxruntime-gpu 1.29（要求 CUDA 13 + cuDNN 9）**，与 CUDA 12 环境不匹配 → CUDA EP 初始化失败 → 崩溃；且污染 `.venv`。
- **✅ 解决（2026-09-03，.venv 内可移植方案）**：
  1. 卸载 AutoUpdate 误装的 `onnxruntime-gpu 1.29` / `onnxruntime` / `onnx`；
  2. 系统装 **CUDA Toolkit 12.6**（`CUDA_PATH`），并在 `.venv` 内 `pip install nvidia-cudnn-cu12 nvidia-cublas-cu12`（cuDNN 9.25 随 .venv 可移植）；
  3. `.venv` 内 `pip install onnxruntime-gpu==1.21.1 onnx`（**1.21.x = CUDA 12 + cuDNN 9**；勿装 ≥1.29 需 CUDA 13）；
  4. 实测：`onnxruntime 1.21.1 with CUDAExecutionProvider`，`fish_detect.onnx` GPU 推理成功。
- **教训**：环境问题不要靠硬编码改业务代码解决（曾尝试在 `ai_detector.py` 强制 ONNX 走 CPU，已回退——那会让有 CUDA 13 的环境也退化成 CPU）。
- 模型与格式分类见 `docs/deep-dive/models-guide.md`。

## 9. PowerShell `$ErrorActionPreference=Stop` 下 ffmpeg stderr 抛 NativeCommandError（2026-09-03）

- **现象**：`Z_script/start_pc_camera.ps1` / `start_usb_camera.ps1` 一运行就报错退出，错误消息是 ffmpeg 的**设备清单第一行**（如 `错误: [in#0 @ ...] "HP Wide Vision HD Camera" (video)`），随后直接进 finally 清理退出，摄像头根本没被用。
- **根因**：脚本顶部 `$ErrorActionPreference="Stop"`；而 `ffmpeg -f dshow -list_devices true -i dummy` 把设备清单写到 **stderr**。Windows PowerShell 5.1 会把原生程序的 stderr 包装成 ErrorRecord，在 `Stop` 模式下**第一条 stderr 即触发 NativeCommandError 终止**（即使 `2> 文件` 重定向也一样会抛）。
- **✅ 解决**：调用 ffmpeg 前临时把 `$ErrorActionPreference` 降为 `Continue`（用完在 `finally` 恢复），再用 `2>&1 | Out-String` 捕获整段文本做设备名匹配：
  ```powershell
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try { $out = & ffmpeg -hide_banner -f dshow -list_devices true -i dummy 2>&1 | Out-String }
  finally { $ErrorActionPreference = $prev }
  return $out -match [regex]::Escape($Name)
  ```
  （注意：降为 `SilentlyContinue` 会把 stderr 一并吞掉导致匹配不到，必须用 `Continue`；或用 `cmd /c '... 2>&1'` 让 cmd 合并 stderr 也能绕开。）
- **验证**：`$ErrorActionPreference='Stop'` 下实测——内置 `HP Wide Vision HD Camera` / 外接 `USB Video Device` 均匹配成功，不存在的设备返回 False，全程不抛错。

## 10. 启动脚本退出：Ctrl+C 正常清理；强杀会残留孤儿进程（2026-09-04）

- **现象**：`start_all_with_sensor.ps1`（及 camera 版）若被**强制结束**（任务管理器 / 杀终端进程 / 调试器 Kill），后台的 mediamtx、ffmpeg、传感器模拟器（`datatran_test.py`）不会自动退出，成为孤儿进程继续占用 8554/5000 端口；`scratch\sensor_sim*.log` 也不被清理。
- **原因**：这些子进程由脚本 `Start-Process` 启动，`finally` 里的清理只在脚本进程**正常收尾**（如收到 `Ctrl+C` 中断）时执行；进程被外部强杀时 `finally` 不会运行。
- **✅ 正常用法**：在脚本自己的窗口按 `Ctrl+C` 退出即可自动清理，无需手动处理。
- **若已残留**，手动清理：
  ```powershell
  Stop-Process -Name ffmpeg,mediamtx -Force
  # 若模拟器仍在跑：结束含 datatran_test 的 python 进程，再删日志
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*datatran_test*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  Remove-Item D:\Fishery_Project\scratch\sensor_sim*.log -ErrorAction SilentlyContinue
  ```
