# -*- coding: utf-8 -*-
"""鱼头检测 + SAM2 全身分割 + 时序跟踪（适配本项目模型）

YOLO fish_detect_m.pt 检测鱼头 → ByteTrack 给 ID
→ 鱼头框扩展为身体候选框 → SAM2 (ultralytics) 分割身体
→ 时序掩码评分 + fallback → 输出追踪视频 + CSV

用法：
  python scripts/head_to_body_track.py --video D:\video.mp4 --output D:\output
"""
from __future__ import annotations

import argparse, csv, os, sys, time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2, numpy as np, torch

# ---- 项目根目录 ----
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.custom_yolo import register as _register_custom
_register_custom()

from ultralytics import YOLO, SAM
import config


# =========================
# 数据结构
# =========================
Box = Tuple[float, float, float, float]


@dataclass
class MaskInfo:
    track_id: int
    mask: np.ndarray
    head_box: Optional[Box]
    mask_box: Box
    score: float
    area: int
    source: str = "yolo"


@dataclass
class TrackState:
    mask: Optional[np.ndarray] = None
    mask_box: Optional[Box] = None
    head_box: Optional[Box] = None
    last_seen: int = -1
    missing: int = 0
    color: Tuple[int, int, int] = field(default_factory=lambda: (0, 255, 0))


# =========================
# 工具函数
# =========================
def clip_box(box: Box, w: int, h: int) -> Box:
    x1, y1, x2, y2 = box
    return (
        max(0, min(x1, w - 1)), max(0, min(y1, h - 1)),
        max(0, min(x2, w - 1)), max(0, min(y2, h - 1)),
    )


def box_center(box: Box) -> Tuple[float, float]:
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def box_iou(a: Box, b: Box) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter) if (area_a + area_b - inter) > 0 else 0


def mask_to_box(mask: np.ndarray) -> Optional[Box]:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    return (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))


def id_color(tid: int) -> Tuple[int, int, int]:
    rng = np.random.default_rng(tid * 1009 + 17)
    return tuple(int(v) for v in rng.integers(60, 255, 3))


def expand_box(box: Box, w: int, h: int, sx: float, sy: float,
               dx: float = 0, dy: float = 0) -> Box:
    bw = max(2, box[2] - box[0])
    bh = max(2, box[3] - box[1])
    cx, cy = box_center(box)
    cx += dx * bw
    cy += dy * bh
    nw, nh = bw * sx, bh * sy
    return clip_box((cx - nw / 2, cy - nh / 2, cx + nw / 2, cy + nh / 2), w, h)


def body_candidates(head_box: Box, w: int, h: int,
                    sx: float, sy: float, shift: float) -> List[Box]:
    """鱼头框 → 9 个候选身体框"""
    cands = [
        expand_box(head_box, w, h, sx, sy, 0, 0),
        expand_box(head_box, w, h, sx, sy, -shift, 0),
        expand_box(head_box, w, h, sx, sy, shift, 0),
        expand_box(head_box, w, h, sx, sy, 0, -shift),
        expand_box(head_box, w, h, sx, sy, 0, shift),
        expand_box(head_box, w, h, sx, sy, -shift * 0.75, -shift * 0.75),
        expand_box(head_box, w, h, sx, sy, shift * 0.75, -shift * 0.75),
        expand_box(head_box, w, h, sx, sy, -shift * 0.75, shift * 0.75),
        expand_box(head_box, w, h, sx, sy, shift * 0.75, shift * 0.75),
    ]
    # 去重
    out = []
    for b in cands:
        if all(box_iou(b, u) < 0.95 for u in out):
            out.append(b)
    return out


def score_mask(mask: np.ndarray, head_box: Optional[Box],
               prev_mask: Optional[np.ndarray],
               min_area: int, max_ratio: float, temp_weight: float) -> float:
    """综合评分：面积 + 鱼头覆盖 + 长条形状 + 时序连续性"""
    h, w = mask.shape[:2]
    area = mask.sum()
    if area < min_area or area > max_ratio * h * w:
        return -1

    # 鱼头区域覆盖率
    head_overlap = 0.0
    if head_box is not None:
        x1, y1, x2, y2 = map(int, clip_box(head_box, w, h))
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 > x1 and y2 > y1:
            head_overlap = mask[y1:y2, x1:x2].mean()

    if head_box is not None and head_overlap < 0.01:
        return -1

    # 长条形状加分
    mb = mask_to_box(mask)
    if mb is None:
        return -1
    bw, bh = mb[2] - mb[0], mb[3] - mb[1]
    elongation = max(bw / max(bh, 1), bh / max(bw, 1))
    elong_bonus = min(1.0, (elongation - 1.0) * 0.15)

    # 时序 IoU
    temporal = 0.0
    if prev_mask is not None:
        inter = np.logical_and(mask, prev_mask).sum()
        union = np.logical_or(mask, prev_mask).sum()
        temporal = inter / union if union > 0 else 0

    return head_overlap * 1.5 + elong_bonus + temporal * temp_weight


# =========================
# 绘制
# =========================
def draw_frame(frame_bgr: np.ndarray, infos: List[MaskInfo],
               alpha: float = 0.4) -> np.ndarray:
    vis = frame_bgr.copy()
    overlay = frame_bgr.copy()
    for info in infos:
        c = id_color(info.track_id)
        overlay[info.mask] = c
    vis = cv2.addWeighted(overlay, alpha, vis, 1 - alpha, 0)

    for info in infos:
        c = id_color(info.track_id)
        cnts, _ = cv2.findContours(info.mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, c, 2)
        x1, y1, x2, y2 = map(int, info.mask_box)
        cv2.rectangle(vis, (x1, y1), (x2, y2), c, 2)
        if info.head_box:
            hx, hy, hx2, hy2 = map(int, info.head_box)
            cv2.rectangle(vis, (hx, hy), (hx2, hy2), (0, 255, 255), 1)
        cv2.putText(vis, f"ID{info.track_id}", (x1, max(20, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, c, 2)
    return vis


# =========================
# 主流程
# =========================
def main():
    ap = argparse.ArgumentParser(description="鱼头检测+SAM2分割+跟踪")
    ap.add_argument("--video", required=True)
    ap.add_argument("--output", default="")
    ap.add_argument("--yolo", default="models/fish_detect_m.pt")
    ap.add_argument("--conf", type=float, default=0.18)
    ap.add_argument("--iou", type=float, default=0.55)
    ap.add_argument("--body-sx", type=float, default=9.0, help="身体框宽/鱼头宽")
    ap.add_argument("--body-sy", type=float, default=6.0, help="身体框高/鱼头高")
    ap.add_argument("--body-shift", type=float, default=2.8, help="候选框偏移量")
    ap.add_argument("--max-missing", type=int, default=10, help="YOLO漏检兜底帧数")
    ap.add_argument("--temp-weight", type=float, default=0.55, help="时序IoU权重")
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(str(video_path))

    out_dir = Path(args.output) if args.output else video_path.parent / f"{video_path.stem}_tracked"
    out_dir.mkdir(parents=True, exist_ok=True)
    video_out = out_dir / f"{video_path.stem}_tracked.mp4"
    csv_out = out_dir / "tracks.csv"

    # 模型
    print(f"加载 YOLO: {args.yolo}")
    yolo = YOLO(str(PROJECT_ROOT / args.yolo))
    print(f"加载 SAM2: {config.SAM2_CHECKPOINT}")
    sam = SAM(str(PROJECT_ROOT / config.SAM2_CHECKPOINT))
    if torch.cuda.is_available():
        sam.model = sam.model.half()

    cap = cv2.VideoCapture(str(video_path))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"视频: {w}x{h}, {fps:.1f}fps, {total}帧")

    writer = cv2.VideoWriter(str(video_out), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    # CSV
    f_csv = open(csv_out, "w", newline="", encoding="utf-8-sig")
    csv_w = csv.writer(f_csv)
    csv_w.writerow(["frame", "track_id", "x1", "y1", "x2", "y2", "area", "source"])

    states: Dict[int, TrackState] = {}
    frame_idx = 0
    t0 = time.time()

    with torch.inference_mode():
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if args.max_frames > 0 and frame_idx >= args.max_frames:
                break

            # 1) YOLO 鱼头检测 + 跟踪
            track_result = yolo.track(frame, persist=True, conf=args.conf,
                                      iou=args.iou, imgsz=960, verbose=False)[0]
            boxes = track_result.boxes
            heads: Dict[int, Box] = {}  # track_id → head_box
            if boxes is not None:
                ids = boxes.id.int().cpu().numpy() if boxes.id is not None else []
                xyxys = boxes.xyxy.cpu().numpy()
                for i, xyxy in enumerate(xyxys):
                    tid = int(ids[i]) if i < len(ids) else -1
                    if tid < 0:
                        continue
                    heads[tid] = tuple(float(v) for v in xyxy)

            # 2) 兜底：上一帧有 mask 但 YOLO 漏了
            for tid, st in states.items():
                if tid not in heads and st.missing < args.max_missing and st.mask_box:
                    heads[tid] = st.mask_box  # 用上一帧的 mask 框

            # 3) SAM2 分割身体
            mask_infos: List[MaskInfo] = []

            for tid, head_box in heads.items():
                st = states.get(tid, TrackState())
                candidates = body_candidates(head_box, w, h, args.body_sx, args.body_sy, args.body_shift)

                best_info = None
                for cand in candidates:
                    try:
                        sam_result = sam(frame, bboxes=[list(cand)], verbose=False)
                    except Exception:
                        continue
                    if sam_result[0].masks is None:
                        continue

                    for m in sam_result[0].masks.data.cpu().numpy():
                        score = score_mask(m > 0.5, head_box, st.mask,
                                           min_area=120, max_ratio=0.35,
                                           temp_weight=args.temp_weight)
                        if score < 0:
                            continue
                        mb = mask_to_box(m > 0.5)
                        if mb is None:
                            continue
                        info = MaskInfo(track_id=tid, mask=m > 0.5, head_box=head_box,
                                        mask_box=mb, score=score, area=int((m > 0.5).sum()))
                        if best_info is None or score > best_info.score:
                            best_info = info

                if best_info is not None:
                    mask_infos.append(best_info)
                    st.mask = best_info.mask.copy()
                    st.mask_box = best_info.mask_box
                    st.head_box = head_box
                    st.last_seen = frame_idx
                    st.missing = 0

            # 4) 更新 missing 计数
            for tid in list(states.keys()):
                if tid not in {m.track_id for m in mask_infos}:
                    states[tid].missing += 1

            for mi in mask_infos:
                states[mi.track_id] = states.get(mi.track_id, TrackState())

            # 5) 输出
            vis = draw_frame(frame, mask_infos)
            writer.write(vis)

            for mi in mask_infos:
                x1, y1, x2, y2 = mi.mask_box
                csv_w.writerow([frame_idx, mi.track_id,
                                f"{x1:.1f}", f"{y1:.1f}", f"{x2:.1f}", f"{y2:.1f}",
                                mi.area, mi.source])

            if frame_idx % 100 == 0:
                elapsed = time.time() - t0
                print(f"  {frame_idx}/{total}  tracks={len(mask_infos)}  "
                      f"fps={frame_idx / max(elapsed, 1):.1f}")

            frame_idx += 1

    cap.release()
    writer.release()
    f_csv.close()

    elapsed = time.time() - t0
    print(f"\n完成: {frame_idx} 帧, {elapsed:.1f}s")
    print(f"视频: {video_out}")
    print(f"CSV:  {csv_out}")


if __name__ == "__main__":
    main()
