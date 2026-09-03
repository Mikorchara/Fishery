# test_enhancement_sample.py — WWE-UIE 增强器流程自测（2026-09-04 更新）
# 说明：旧版引用 core.enhancer.CIDNetEnhancer（早期遗留，类已不存在），
#       已归档到 docs/deep-dive/_legacy_test_enhancement_CIDNet.py。
#       现改为使用当前 core.enhancer.WWEEnhancer（包装 WWE-UIE 的 myModel）。
# 用法：在项目根运行  python tests/test_enhancement_sample.py
import os
import sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from core.enhancer import WWEEnhancer


def test():
    print("Testing WWE-UIE Enhancer (WWEEnhancer)...")
    try:
        enhancer = WWEEnhancer()   # 自动加载 WWE-UIE/output/.../ 最新 best_model.pth

        # 合成一张"水下感"测试帧（蓝绿渐变 + 低红通道），比纯随机噪声更贴近真实场景
        h, w = 480, 640
        dummy = np.zeros((h, w, 3), dtype=np.uint8)
        dummy[:, :, 0] = np.linspace(60, 150, w, dtype=np.uint8)   # B 渐变（偏蓝）
        dummy[:, :, 1] = np.linspace(40, 130, w, dtype=np.uint8)   # G
        dummy[:, :, 2] = np.full((h, w), 25, dtype=np.uint8)       # R 偏低（水下红衰减）

        print("Running enhancement...")
        enhanced = enhancer.enhance(dummy)

        if (enhanced is not None
                and enhanced.shape == dummy.shape
                and enhanced.dtype == dummy.dtype):
            print("✅ Enhancement pipeline passed!")
            print(f"   input  : {dummy.shape} {dummy.dtype}")
            print(f"   output : {enhanced.shape} {enhanced.dtype}")
        else:
            print("❌ Enhancement failed (shape/dtype mismatch or None)")
            print(f"   got: {None if enhanced is None else (enhanced.shape, enhanced.dtype)}")
    except Exception as e:
        print(f"❌ Error during test: {e}")


if __name__ == "__main__":
    test()
