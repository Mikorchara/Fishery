# 已知问题与踩坑记录

> 修改代码前必读。遇到问题先来这里查。

## 1. start_all.ps1 必须为 UTF-8 with BOM 编码

- **现象**：脚本一运行就报"字符串缺少终止符"，所有进程都没启动，浏览器打不开。
- **原因**：Windows PowerShell 5.1（`powershell`）会把无 BOM 的 .ps1 按 ANSI(GBK) 读取，中文注释乱码破坏引号，导致整脚本解析失败。
- **解决**：文件保存为 UTF-8 with BOM（或用 pwsh 7 运行）。
- **验证**：用 `powershell -NoProfile -ExecutionPolicy Bypass -File start_all.ps1` 实测（勿只用 pwsh 解析，测不出 5.1 的问题）。

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
