# models/ 模型文件速查（分类）

> 按**文件后缀（格式）**与**用途（任务）**对 `models/` 目录下的所有文件分类，说明每个文件的角色、是否被 `config.py` 引用、运行时是否需要。
> 配套经验见 `docs/troubleshooting.md` 第 8 条（onnxruntime / ONNX GPU）。

---

## 一、格式后缀速查

| 后缀 | 格式 | 运行引擎 | 本机（NVIDIA）可否用 |
|------|------|----------|---------------------|
| `.pt` | PyTorch 权重 | PyTorch（**自带** CUDA 运行时） | ✅ GPU |
| `.onnx` | ONNX 可移植模型 | onnxruntime（**不自带** CUDA 库） | ⚠️ 需独立 CUDA 库 |
| `.om` | 华为昇腾 Ascend 离线模型 | 昇腾 NPU 工具链 | ❌ NVIDIA 无法运行 |
| `.yaml` | 模型结构配置（非权重） | — | — |

---

## 二、按用途分类

### 1. 鱼群检测（detect，画框·数鱼）— 运行时主力

| 文件 | 角色 | 网页 key | 必需 |
|------|------|----------|------|
| `fish_detect_m.pt` | 默认模型（EMA 注意力） | fish_detect_ema | ✅ |
| `fish_detect_seam.pt` | SEAM 改进版 | fish_detect_seam | 否 |
| `fish_detect_s_ECA_EMA_BIFPN.pt` | BiFPN 改进版 | fish_bifpn | 否 |
| `fish_detect.onnx` | 上述检测的 ONNX 导出版 | fish_onnx | 否 |
| `fish_detect.pt` | **未被引用**，疑似旧版 / ONNX 的 PyTorch 源 | — | 否 |

### 2. 病害 / 异常告警

| 文件 | 角色 | 网页 key | 必需 |
|------|------|----------|------|
| `fish_disease.pt` | 病害告警（占位，未来可换） | disease_alert | 否 |

### 3. 鳗鱼分割（seg，像素级掩码）

| 文件 | 角色 | 网页 key | 必需 |
|------|------|----------|------|
| `fish_seg_yolo26.pt` | YOLO26-seg 标准版（直出掩码） | fish_seg | 否 |
| `fish_seg_yolo26_nano.pt` | 同上的 nano 轻量版 | fish_seg_nano | 否 |
| `fish_seg_yolo11n.pt` | YOLO11 nano seg | fish_seg_yolo11 | 否 |
| `fish_seg_yolo11n.onnx` | 上述的 ONNX 导出 | fish_seg_yolo11_onnx | 否 |
| `fish_seg_yolo26_nano.onnx` | 上述的 ONNX 导出 | fish_seg_nano_onnx | 否 |

### 4. SAM2 分割（全局辅助，用于 detect→实例分割路径）

| 文件 | 角色 | 必需 |
|------|------|------|
| `sam2.1_t.pt` | SAM2 权重（`config.SAM2_CHECKPOINT` 运行时加载） | ✅（AI 分割开关用） |
| `sam2.1_t_origin.pt` | SAM2 **原始权重备份**（对比/恢复用） | 否 |
| `sam2_hiera_t.yaml` | SAM2 模型结构配置（`config.SAM2_CONFIG`） | ✅ |

### 5. 图像增强（WWE-UIE）

| 文件 | 角色 | 必需 |
|------|------|------|
| `wwe_uie.onnx` | 增强模型 ONNX 导出 | 否 |
> 注：enhancer 运行时实际加载的是 `WWE-UIE/output/Fishery_WWE_UIEB/UIEB/` 下最新 `best_model.pth`（PyTorch 权重），**不是**此 .onnx。

### 6. 昇腾 `.om`（⚠️ 本机跑不了）

`fish_detect.om` / `fish_detect_640.om` / `fish_seg_yolo11n.om` / `best_640.om`
——华为昇腾 NPU 的离线模型格式，与 .pt/.onnx 是同一批模型在**昇腾平台**的导出。NVIDIA 机器无法加载，属历史/跨平台尝试，无运行作用。

### 7. 无关 / 演示

| 文件 | 说明 |
|------|------|
| `yolov8n.pt` | ultralytics 官方通用模型（与项目无关的 demo / 兜底） |

---

## 三、与 `config.py` AVAILABLE_MODELS 的对应

`config.py` 的 `AVAILABLE_MODELS`（网页下拉框数据源）**恰好引用**上面标了"网页 key"的文件（10 项）。`MODEL_CONFIGS` 为每个 key 设独立置信度阈值。

**未被 `config.py` 引用的文件**（纯备份/历史/导出源，删掉不影响运行，但建议保留备查）：
`fish_detect.pt`、`sam2.1_t_origin.pt`、`wwe_uie.onnx`、全部 `.om`、`yolov8n.pt`、`sam2_hiera_t.yaml`（配置，被 config 当文件路径引用，需要保留）。

---

## 四、ONNX GPU 运行须知（重要）

- **`.onnx` 需要 onnxruntime 才能加载**；onnxruntime 分为 CPU 版与 GPU 版。
- **onnxruntime-gpu 不捆绑 CUDA 库**：它运行时要找 cublas / cuDNN。PyTorch 是自带 CUDA 运行时的，所以"PyTorch 能 GPU ≠ onnxruntime 能 GPU"。
- **✅ 本机已跑通的组合（2026-09-03，`.venv` 内可移植）**：
  - 系统：CUDA Toolkit 12.6（`CUDA_PATH`）；
  - `.venv`：`nvidia-cudnn-cu12`(9.25) + `nvidia-cublas-cu12` + `onnxruntime-gpu==1.21.1` + `onnx`；
  - 实测：`onnxruntime 1.21.1 with CUDAExecutionProvider`，ONNX 模型 GPU 推理成功。
- **版本匹配红线**：**onnxruntime-gpu 1.21.x = CUDA 12 + cuDNN 9**；**≥1.29 需 CUDA 13**（会崩）。不同 CUDA 配不同版本，勿让 ultralytics AutoUpdate 自动装最新。
- 详见 `docs/troubleshooting.md` 第 8 条。
