"""导出 WWE-UIE 为 ONNX — opset=11, dynamic=False, simplify=True。"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "WWE-UIE"))
import torch
import onnx
import onnxslim
from model import myModel

WEIGHTS = "WWE-UIE/output/Fishery_WWE_UIEB/UIEB/20260505_finetune/best_model.pth"
OUTPUT = "models/wwe_uie.onnx"

print(f"权重: {WEIGHTS}")

model = myModel(in_channels=3, feature_channels=32, use_white_balance=True)
model.eval()

ckpt = torch.load(WEIGHTS, map_location="cpu")
ckpt = {k: v for k, v in ckpt.items() if k in model.state_dict()}
model.load_state_dict(ckpt, strict=False)

# 固定输入 (1, 3, 640, 360)，无动态轴
dummy = torch.randn(1, 3, 360, 640)

print("导出 (opset=11, dynamic=False)...")
torch.onnx.export(
    model, dummy, OUTPUT,
    opset_version=11,
    input_names=["input"],
    output_names=["output"],
)

# simplify 暂时跳过（InstanceNorm train=True 导致 onnxslim 形状推断错误）
# 模型已通过 onnx.checker 校验，可直接用于 ATC 转换
print("skip simplify (InstanceNorm 兼容性问题)")
onnx_model = onnx.load(OUTPUT)
onnx.checker.check_model(onnx_model)
print(f"完成  |  {os.path.getsize(OUTPUT)/1e6:.1f} MB  |  {OUTPUT}")
