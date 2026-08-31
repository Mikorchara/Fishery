"""测试 H264Encoder 的文件级联读写功能。"""
import cv2
import numpy as np
import time
import sys
# 避免 Windows gbk 控制台编码问题
sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, '.')
from core.h264_streamer import H264Encoder

print("[TEST] 创建 H264Encoder...")
frame = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.putText(frame, 'Test Frame', (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 3)

enc = H264Encoder(640, 480, fps=30)
enc.start()

# 等待 init segment
print("[TEST] 等待 init segment...")
for i in range(50):
    if enc.init_segment is not None:
        print(f"  ✓ init segment 就绪 ({i*0.1:.1f}s): {len(enc.init_segment)} 字节")
        break
    # 先喂一帧唤醒编码器
    if i == 5:
        enc.encode_frame(frame)
    time.sleep(0.1)
else:
    print("  ✗ init segment 未就绪，检查 FFmpeg...")
    if enc.process:
        err = enc.process.stderr.read()
        if err:
            print(f"  stderr: {err.decode(errors='replace')[:300]}")
    enc.stop()
    sys.exit(1)

# 检查 init segment 内容
assert len(enc.init_segment) > 40, "init 太短"
# 检查 box 类型
box_type_init = enc.init_segment[4:8].decode('ascii', errors='replace')
# 如果 init segment 是组合的 ftyp+moov，第一个 box 应该是 ftyp
assert box_type_init in ('ftyp', 'moov'), f"意外的 box 类型: {box_type_init}"
print(f"  ✓ 第一个 box: {box_type_init}")

# 编码多帧
print("[TEST] 编码 20 帧...")
for i in range(20):
    # 改变帧内容使编码器产生新输出
    cv2.putText(frame, f'Frame {i}', (50, 240 + i * 5), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    enc.encode_frame(frame)
    time.sleep(0.02)

# 收集 media segments
print("[TEST] 收集 segments...")
segments = []
for _ in range(100):
    seg = enc.get_segment(block=True, timeout=0.3)
    if seg is None:
        break
    segments.append(seg)

print(f"  ✓ 收集到 {len(segments)} 个 media segment")
for i, seg in enumerate(segments[:5]):
    box_type = seg[4:8].decode('ascii', errors='replace')
    print(f"    [{i}] {len(seg)} 字节, type={box_type}")

assert len(segments) > 0, "应收到至少一个 segment"

# 测试 stop
print("[TEST] 停止编码器...")
enc.stop()
print("  ✓ 编码器已停止")

print("\n[SUCCESS] H264Encoder 测试通过！")
