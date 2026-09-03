# test_enhancement_sample.py
import cv2
import torch
import numpy as np
from core.enhancer import CIDNetEnhancer

def test():
    print("Testing CIDNet Enhancer...")
    try:
        enhancer = CIDNetEnhancer()
        
        # 创建一个随机噪声图来测试流程
        dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        print("Running enhancement...")
        enhanced = enhancer.enhance(dummy_frame)
        
        if enhanced is not None and enhanced.shape == dummy_frame.shape:
            print("✅ Enhancement pipeline passed!")
        else:
            print("❌ Enhancement failed (shape mismatch or None)")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test()
