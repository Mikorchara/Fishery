"""全模型+增强 综合基准测试 — 同一视频源，遍历所有组合。"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import torch
import config
from core.enhancer import WWEEnhancer
from core.ai_detector import FisheryAI

VIDEO_PATH = "test_video_2.mp4"
N_FRAMES = 100
WARMUP_FRAMES = 5

MODEL_KEYS = ["fish_detect_ema", "fish_detect_seam", "fish_onnx",
              "fish_seg", "fish_seg_nano", "fish_seg_yolo11",
              "fish_seg_nano_onnx", "fish_seg_yolo11_onnx",
              "fish_bifpn"]


def load_frames(path, n):
    cap = cv2.VideoCapture(path)
    frames = []
    for _ in range(n):
        ret, frame = cap.read()
        if not ret: break
        frames.append(frame)
    cap.release()
    return frames


def run_test(frames, ai, enhancer, model_key, do_enhance, do_detect, do_seg):
    if do_detect and model_key:
        model_path = config.AVAILABLE_MODELS.get(model_key)
        if not model_path or not os.path.exists(model_path):
            print(f"    跳过: {model_key}")
            return None
        ai.load_model(model_path, model_key=model_key)

    times, det_counts = [], []
    frames_detail = []

    for i, raw in enumerate(frames):
        frame = raw.copy()
        t0 = time.perf_counter()

        if do_enhance: frame = enhancer.enhance(frame)
        if do_detect:
            seg = do_seg and "seg" not in (model_key or "")
            ai.process_frame(frame, seg_enabled=seg)
        elif torch.cuda.is_available():
            torch.cuda.synchronize()

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        dt = (time.perf_counter() - t0) * 1000

        if i >= WARMUP_FRAMES:
            times.append(dt)
            if do_detect: det_counts.append(ai.last_count)
            detail = {"frame": i - WARMUP_FRAMES, "latency_ms": round(dt, 1)}
            if do_detect:
                detail["detections"] = ai.last_count
                detail["conf_mean"] = round(float(np.mean(ai.last_confs)), 4) if ai.last_confs else 0
                detail["conf_max"] = round(float(np.max(ai.last_confs)), 4) if ai.last_confs else 0
            frames_detail.append(detail)

    if not times: return None

    result = {
        "latency_ms_mean": round(float(np.mean(times)), 1),
        "latency_ms_std": round(float(np.std(times)), 1),
        "fps": round(1000 / float(np.mean(times)), 1) if np.mean(times) > 0 else 0,
        "latency_ms_min": round(float(np.min(times)), 1),
        "latency_ms_max": round(float(np.max(times)), 1),
        "frames": frames_detail,
    }
    if det_counts:
        result["det_mean"] = round(float(np.mean(det_counts)), 1)
        result["det_std"] = round(float(np.std(det_counts)), 1)
        result["det_min"] = int(np.min(det_counts))
        result["det_max"] = int(np.max(det_counts))
    return result


def print_row(label, r):
    lat = f"{r['latency_ms_mean']:.1f}"
    std = f"{r['latency_ms_std']:.1f}"
    fps = f"{r['fps']:.1f}"
    det = f"{r.get('det_mean', '-'):.1f}" if 'det_mean' in r else "  -"
    print(f"{label:<40} {lat:>8}ms {std:>6}  {fps:>7}FPS  det={det}")


def main():
    print(f"视频: {VIDEO_PATH}  |  {N_FRAMES}帧 + {WARMUP_FRAMES}预热")
    print(f"CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    print("\n[1/3] 加载帧...")
    frames = load_frames(VIDEO_PATH, N_FRAMES + WARMUP_FRAMES)
    print(f"  {len(frames)}帧  {frames[0].shape[1]}x{frames[0].shape[0]}")

    print("\n[2/3] 初始化...")
    enhancer = WWEEnhancer()
    ai = FisheryAI()

    results = {}

    print("\n[3/3] 测试...")
    print(f"{'配置':<40} {'延迟':>8} {'±std':>6} {'FPS':>7}  {'检出'}")
    print("-" * 75)

    # 基线
    r = run_test(frames, ai, enhancer, None, False, False, False)
    if r: results["纯传输"] = r; print_row("纯传输", r)

    r = run_test(frames, ai, enhancer, None, True, False, False)
    if r: results["仅增强(WWE-UIE)"] = r; print_row("仅增强(WWE-UIE)", r)

    # 各模型
    for mk in MODEL_KEYS:
        mp = config.AVAILABLE_MODELS.get(mk)
        if not mp or not os.path.exists(mp):
            print(f"  [{mk}] 跳过: 文件不存在")
            continue

        r_off = run_test(frames, ai, enhancer, mk, False, True, False)
        if r_off: results[f"{mk} 无增强"] = r_off; print_row(f"{mk} 无增强", r_off)

        r_on = run_test(frames, ai, enhancer, mk, True, True, False)
        if r_on: results[f"{mk} +增强"] = r_on; print_row(f"{mk} +增强", r_on)

    # SAM2 分割
    for mk in ["fish_detect_ema", "fish_detect_seam"]:
        r_seg = run_test(frames, ai, enhancer, mk, False, True, True)
        if r_seg: results[f"{mk} +SAM2"] = r_seg; print_row(f"{mk} +SAM2", r_seg)

    os.makedirs("bench_output", exist_ok=True)
    out = "bench_output/bench_full_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {out}")


if __name__ == "__main__":
    main()
