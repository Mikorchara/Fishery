# core/enhancer.py
import logging
import torch
import cv2
import numpy as np
import os
import sys
import config

_log = logging.getLogger("enhance")

current_dir = os.path.dirname(os.path.abspath(__file__))
wwe_path = os.path.join(os.path.dirname(current_dir), "WWE-UIE")
if wwe_path not in sys.path:
    sys.path.append(wwe_path)

try:
    from model import myModel
except ImportError as e:
    _log.error("无法导入模型，请检查路径: %s", wwe_path)
    raise e


class WWEEnhancer:
    def __init__(self, weight_path=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_fp16 = config.ENHANCE_FP16 and self.device.type == "cuda"
        self.max_side = config.ENHANCE_MAX_SIDE

        self.model = myModel(
            in_channels=3, feature_channels=32, use_white_balance=True
        ).to(self.device)

        if weight_path is None:
            output_dir = os.path.join(wwe_path, "output", "Fishery_WWE_UIEB", "UIEB")
            if os.path.exists(output_dir):
                subdirs = sorted([
                    os.path.join(output_dir, d) for d in os.listdir(output_dir)
                    if os.path.isdir(os.path.join(output_dir, d))
                ])
                if subdirs:
                    weight_path = os.path.join(subdirs[-1], "best_model.pth")

        if weight_path and os.path.exists(weight_path):
            _log.info("加载 WWE-UIE 权重: %s", weight_path)
            checkpoint = torch.load(weight_path, map_location=self.device)
            model_state = self.model.state_dict()
            missing = [k for k in model_state if k not in checkpoint]
            unexpected = [k for k in checkpoint if k not in model_state]
            if missing:
                _log.warning("权重缺失键 (%d): %s", len(missing), missing[:5])
            if unexpected:
                _log.warning("权重多余键 (%d): %s", len(unexpected), unexpected[:5])
            if not missing or len(missing) < len(model_state) // 2:
                checkpoint = {k: v for k, v in checkpoint.items() if k in model_state}
                model_state.update(checkpoint)
                self.model.load_state_dict(model_state, strict=True)
            else:
                _log.error("权重文件与模型架构严重不匹配，跳过加载")

        self.model.eval()

        if self.use_fp16:
            self.model = self.model.half()
            _log.info("WWE-UIE: FP16 推理 (设备: %s)", self.device)
        else:
            _log.info("WWE-UIE: FP32 推理 (设备: %s)", self.device)

        if self.max_side > 0:
            _log.info("WWE-UIE: 处理分辨率上限 %d px", self.max_side)

        self._compiled = False
        if config.ENHANCE_COMPILE and hasattr(torch, "compile"):
            import platform
            if platform.system() != "Windows":
                try:
                    self.model = torch.compile(self.model, mode="reduce-overhead")
                    self._compiled = True
                    _log.info("WWE-UIE: torch.compile 已启用")
                except Exception as e:
                    _log.warning("WWE-UIE: torch.compile 跳过 (%s)", e)

        _log.info("WWE-UIE: 预热中...")
        dummy = torch.randn(1, 3, 256, 256, device=self.device)
        if self.use_fp16:
            dummy = dummy.half()
        with torch.no_grad():
            _ = self.model(dummy)
        torch.cuda.synchronize() if self.device.type == "cuda" else None
        _log.info("WWE-UIE: 预热完成")

    # ------ BGR↔RGB tensor 变换（GPU 上完成，避免 CPU cvtColor） ------

    @staticmethod
    def _bgr_to_rgb_tensor(frame: np.ndarray, device, fp16: bool):
        """numpy BGR → GPU RGB tensor [1,3,H,W]，值域 [0,1]。"""
        # opencv 读取的是 BGR → tensor[:, [2,1,0], :, :] 就是 RGB
        t = torch.from_numpy(frame).to(device, non_blocking=True)
        t = t.permute(2, 0, 1).unsqueeze(0)  # [1, 3, H, W]
        t = t[:, [2, 1, 0], :, :]            # BGR → RGB
        t = t.float() / 255.0
        if fp16:
            t = t.half()
        return t

    @staticmethod
    def _tensor_to_bgr_numpy(t) -> np.ndarray:
        """GPU RGB tensor [1,3,H,W] → numpy BGR uint8。"""
        t = t[:, [2, 1, 0], :, :]            # RGB → BGR
        t = t.squeeze(0).permute(1, 2, 0)    # [H, W, 3]
        t = t.float() * 255.0
        t = t.clamp(0, 255)
        return t.to(dtype=torch.uint8).cpu().numpy()

    # ------ 主要接口 ------

    def enhance(self, frame):
        if frame is None:
            return None

        H, W = frame.shape[:2]

        # ---- 可选降采样 ----
        scale = 1.0
        if self.max_side > 0:
            longest = max(H, W)
            if longest > self.max_side:
                scale = self.max_side / longest
                new_w = int(W * scale)
                new_h = int(H * scale)
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # ---- 预处理（GPU tensor） ----
        input_tensor = self._bgr_to_rgb_tensor(frame, self.device, self.use_fp16)

        # ---- 推理 ----
        with torch.no_grad():
            output = self.model(input_tensor)
            output = torch.clamp(output, 0.0, 1.0)

        # ---- 后处理 ----
        result = self._tensor_to_bgr_numpy(output)

        # ---- 恢复原始分辨率 ----
        if scale != 1.0:
            result = cv2.resize(result, (W, H), interpolation=cv2.INTER_LINEAR)

        return result


if __name__ == "__main__":
    enhancer = WWEEnhancer()
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # 跑几次获取稳定帧率
    import time
    for _ in range(3):
        enhancer.enhance(test_img)
    t0 = time.time()
    n = 20
    for _ in range(n):
        enhancer.enhance(test_img)
    torch.cuda.synchronize()
    elapsed = time.time() - t0
    print(f"平均 {n / elapsed:.1f} FPS (640x480)")
