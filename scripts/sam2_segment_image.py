"""SAM2 单图分割测试 — 点击图片添加提示点，右键删除。

左键：正点（前景）  右键：负点（背景）
按 s：保存结果  按 r：重置  按 q：退出
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2, numpy as np
from ultralytics import SAM

IMAGE = r"F:\onedrive\graduation\Fishery_Project\test_img.jpg"

# 没有图片就从视频抽一帧
if not os.path.exists(IMAGE):
    cap = cv2.VideoCapture(r"F:\onedrive\graduation\Fishery_Project\test_video.mp4")
    cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(IMAGE, frame)
        print(f"从视频抽取第100帧 → {IMAGE}")
    cap.release()
CHECKPOINT = "models/sam2.1_t.pt"

points, labels = [], []   # 正点=1, 负点=0


def segment():
    sam = SAM(CHECKPOINT)
    img = cv2.imread(IMAGE)
    if img is None:
        print(f"找不到图片: {IMAGE}")
        return

    cv2.namedWindow("SAM2")
    cv2.setMouseCallback("SAM2", _on_mouse)
    print("左键=前景点  右键=背景点  s=保存  r=重置  q=退出")

    display = img.copy()

    while True:
        cv2.imshow("SAM2", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("r"):
            points.clear(); labels.clear()
            display = img.copy()
            print("已重置")
        elif key == ord("s"):
            out = os.path.splitext(IMAGE)[0] + "_seg.jpg"
            cv2.imwrite(out, display)
            print(f"已保存: {out}")
        elif points:
            # 有点就实时分割
            result = sam(img.copy(), points=points.copy(), labels=labels.copy(), verbose=False)
            display = result[0].plot()


def _on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y]); labels.append(1)
        print(f"+ 正点 {len(points)}: ({x},{y})")
    elif event == cv2.EVENT_RBUTTONDOWN:
        points.append([x, y]); labels.append(0)
        print(f"- 负点 {len(points)}: ({x},{y})")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        IMAGE = sys.argv[1]
    segment()
