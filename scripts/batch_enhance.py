"""批量增强图片，生成 paired 训练数据。

用法：
  python scripts/batch_enhance.py --input "F:\onedrive\graduation\跟踪数据集\水下\final\images" --output "F:\onedrive\graduation\跟踪数据集\水下\enhanced" --max_images 200
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import argparse
from pathlib import Path
from core.enhancer import WWEEnhancer


def imread_unicode(path):
    """OpenCV imread 不支持中文路径，用 numpy 绕过去。"""
    with open(path, "rb") as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_unicode(path, img):
    """OpenCV imwrite 不支持中文路径，用 imencode 绕过去。"""
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        with open(path, "wb") as f:
            f.write(buf.tobytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="原始图片目录")
    parser.add_argument("--output", required=True, help="增强输出目录")
    parser.add_argument("--max_images", type=int, default=200, help="最多处理多少张")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    print("加载 WWE 增强模型...")
    enhancer = WWEEnhancer()

    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    files = [f for f in sorted(Path(args.input).glob("*")) if f.suffix.lower() in exts]
    files = files[:args.max_images]
    total = len(files)
    print(f"找到 {total} 张图片，开始增强...")

    done = 0
    for f in files:
        img = imread_unicode(str(f))
        if img is None:
            continue
        enhanced = enhancer.enhance(img)
        imwrite_unicode(str(out / f.name), enhanced)
        done += 1
        if done % 10 == 0:
            print(f"  进度: {done}/{total}")

    print(f"完成: {done} 张 → {out}")
    print(f"现在请到输出目录挑选效果好的增强图，与原始图配对后用于 fine-tune。")


if __name__ == "__main__":
    main()
