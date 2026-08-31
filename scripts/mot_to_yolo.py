"""MOT 标注 → YOLO 格式转换：用于 YOLO 检测模型微调。

MOT 格式: frame, id, x, y, w, h, conf, class, visibility
YOLO 格式: class x_center y_center width height (归一化到 [0,1])
"""
import os
import cv2

SRC_DIR = r"F:\onedrive\graduation\跟踪数据集\水下跟踪\水下跟踪"
OUT_DIR = r"F:\onedrive\graduation\跟踪数据集\水下跟踪\yolo_dataset"

os.makedirs(f"{OUT_DIR}/images/train", exist_ok=True)
os.makedirs(f"{OUT_DIR}/labels/train", exist_ok=True)

for idx in range(1, 6):
    video_path = os.path.join(SRC_DIR, f"{idx}.mp4")
    label_path = os.path.join(SRC_DIR, f"{idx}.txt")
    if not os.path.exists(video_path) or not os.path.exists(label_path):
        continue

    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    with open(label_path, "r") as f:
        lines = [l.strip() for l in f if l.strip()]

    # 按帧分组
    frames = {}
    for line in lines:
        parts = line.split(",")
        frame_id = int(parts[0])
        x, y, bw, bh = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
        frames.setdefault(frame_id, []).append((x, y, bw, bh))

    print(f"[{idx}.mp4] {len(frames)} 帧有标注, 尺寸 {w}x{h}")

    for frame_id, boxes in frames.items():
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ret, frame = cap.read()
        if not ret:
            continue

        name = f"vid{idx}_{frame_id:06d}"
        cv2.imwrite(f"{OUT_DIR}/images/train/{name}.jpg", frame)

        with open(f"{OUT_DIR}/labels/train/{name}.txt", "w") as lf:
            for x, y, bw, bh in boxes:
                xc = (x + bw / 2) / w
                yc = (y + bh / 2) / h
                nw = bw / w
                nh = bh / h
                lf.write(f"0 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}\n")

    cap.release()

print(f"\n完成。输出: {OUT_DIR}")
print(f"下一步: yolo train data={OUT_DIR}/dataset.yaml model=yolov8n.pt epochs=50")
