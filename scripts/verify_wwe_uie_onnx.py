"""验证 WWE-UIE ONNX 导出结果一致性。"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "WWE-UIE"))
import numpy as np
import cv2
import torch
import onnxruntime as ort
from model import myModel

ONNX_PATH = "models/wwe_uie.onnx"
WEIGHTS = "WWE-UIE/output/Fishery_WWE_UIEB/UIEB/20260505_finetune/best_model.pth"
TEST_IMG = "test_video_2.mp4"

def main():
    # 1) 加载测试图（视频第一帧）
    cap = cv2.VideoCapture(TEST_IMG)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("读取视频失败"); return
    h, w = frame.shape[:2]
    # 缩放到640以内保持比例
    scale = 640 / max(h, w)
    frame = cv2.resize(frame, (int(w*scale), int(h*scale)))
    print(f"测试图: {frame.shape[1]}x{frame.shape[0]}")

    # 2) 预处理 — 和 core/enhancer.py 一致
    # BGR → RGB, [0,255] → [0,1] float32, (H,W,3) → (1,3,H,W)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    input_np = np.transpose(rgb, (2, 0, 1))[np.newaxis, ...]  # (1,3,H,W)
    input_pt = torch.from_numpy(input_np.copy())

    # 3) PyTorch 推理
    model_pt = myModel(in_channels=3, feature_channels=32, use_white_balance=True)
    model_pt.eval()
    ckpt = torch.load(WEIGHTS, map_location="cpu")
    ckpt = {k: v for k, v in ckpt.items() if k in model_pt.state_dict()}
    model_pt.load_state_dict(ckpt, strict=False)
    with torch.no_grad():
        out_pt = model_pt(input_pt)
        out_pt = torch.clamp(out_pt, 0.0, 1.0)
    out_pt_np = out_pt.squeeze(0).permute(1, 2, 0).numpy()  # (H,W,3) RGB [0,1]

    # 4) ONNX Runtime 推理
    session = ort.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])
    out_onnx = session.run(["output"], {"input": input_np.astype(np.float32)})[0]
    out_onnx = np.clip(out_onnx, 0.0, 1.0)
    out_onnx_np = out_onnx.squeeze(0).transpose(1, 2, 0)  # (H,W,3) RGB [0,1]

    # 5) 比较
    diff = np.abs(out_pt_np - out_onnx_np)
    print(f"最大像素差: {diff.max():.6f}")
    print(f"平均像素差: {diff.mean():.6f}")

    if diff.max() < 0.01:
        print("[OK] 一致性通过（差异 < 1%）")
    elif diff.max() < 0.05:
        print("△ 轻微差异（< 5%），FP32/ONNX 算子差异导致，通常可接受")
    else:
        print("✗ 差异较大，需检查导出参数或算子兼容性")

    # 6) 保存对比图
    os.makedirs("bench_output", exist_ok=True)
    # PT输出
    pt_bgr = cv2.cvtColor((out_pt_np * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    cv2.imwrite("bench_output/verify_pt_output.jpg", pt_bgr)
    # ONNX输出
    onnx_bgr = cv2.cvtColor((out_onnx_np * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    cv2.imwrite("bench_output/verify_onnx_output.jpg", onnx_bgr)
    # 原图
    cv2.imwrite("bench_output/verify_input.jpg", frame)
    print("对比图已保存: bench_output/verify_*.jpg")


if __name__ == "__main__":
    main()
