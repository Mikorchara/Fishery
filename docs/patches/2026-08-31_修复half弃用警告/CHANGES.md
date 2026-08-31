# 修改日期：2026-08-31
# 修改人：AI (Copilot)

## 修改文件
- `core/ai_detector.py` — 弃用的 `half=` 参数改为 ultralytics 8.4.x 推荐的 `quantize=` ---  modify_0

## 修改原因
运行时会持续打印弃用警告：
`WARNING 'half' is deprecated and will be removed in the future. Use 'quantize' instead.`
ultralytics 8.4.112 中 `half=True` 已统一映射为 `quantize=16`（FP16），传 `half=` 会触发 deprecation 警告。

## 修改内容
- `track()` 与两处 `predict()` 调用中 `half=self._fp16` → `quantize=16 if self._fp16 else None`
  - `_fp16=True`（CUDA + pt 模型）→ `quantize=16`（FP16，行为与原来一致）
  - `_fp16=False`（CPU 或 ONNX）→ `quantize=None`（FP32，行为与原来一致）

## 影响范围
- YOLO 检测/跟踪的推理精度模式（FP16/FP32 切换逻辑不变，仅参数名更新）
- 消除运行时的 `half` 弃用警告噪音
