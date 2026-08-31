# 修改日期：2026-08-31

## 修改文件
- `core/ai_detector.py` — ONNX 模型强制 CPU 推理（修复 ONNX Runtime 崩溃）--- modify_0

## 修改原因
- 运行 `scripts/bench_full.py` 时，`fish_detect.onnx` 等 ONNX 模型推理崩溃：
  - ultralytics AutoUpdate 自动安装了 `onnxruntime-gpu 1.29.0`，其要求 **CUDA 13 + cuDNN 9 + 新版 MSVC runtime**；
  - 当前环境驱动虽新（592.82）但**未装独立 CUDA/cuDNN 库**，CUDAExecutionProvider 创建失败；
  - 回退后 onnxruntime 用 CPU provider，但输入 tensor 仍在 GPU → `Error when binding input ... no data transfer registered` 崩溃，导致整个基准脚本中断。
- 修复目标：让 ONNX 模型在当前环境可用（网页端选择 ONNX 模型、基准测试都能跑）。

## 修改内容
- `core/ai_detector.py` `process_frame()` 的 `predict()` 调用：
  - 当 `self._model_format == "onnx"` 时，追加 `**({"device": "cpu"})`，强制 ONNX 走 CPU 推理；
  - PT 模型分支不变（仍用 GPU + fp16）。

## 影响范围
- ONNX 模型（`fish_onnx` / `fish_seg_nano_onnx` / `fish_seg_yolo11_onnx`）：网页端选择时也走 CPU，可用但较慢；
- PT 模型（EMA / SEAM / SEG / YOLO11 / BiFPN）与 SAM2：不受影响。
- 基准测试现在能完整跑完（22 组配置），已生成 `bench_output/bench_full_result.json` 与 4 张图。

## 备注
- 若日后配置好 onnxruntime-gpu 匹配版本（CUDA 13 + cuDNN 9），可去掉此强制 CPU 逻辑，恢复 ONNX GPU 推理。
