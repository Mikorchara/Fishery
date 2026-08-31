# 修改日期：2026-08-31
# 修改人：AI (Copilot)

## 修改文件
- `core/enhancer.py` — `torch.load` 增加 `weights_only=True` ---  modify_0

## 修改原因
运行时打印 FutureWarning：
`torch.load` 默认 `weights_only=False`（走 pickle，可能执行任意代码），PyTorch 将来会翻转默认值为 `weights_only=True`。

## 修改内容
- `WWEEnhancer.__init__` 中 `torch.load(weight_path, map_location=self.device)`
  → `torch.load(weight_path, map_location=self.device, weights_only=True)`

## 验证
- 已实测 `best_model.pth`（`WWE-UIE/output/Fishery_WWE_UIEB/UIEB/20260505_finetune/`）为纯张量 OrderedDict，
  `weights_only=True` 可正常加载，警告消除，权重加载行为不变。

## 影响范围
- WWE-UIE 增强模块的权重加载（仅消除未来兼容性警告，无行为变化）
