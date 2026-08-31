"""帧处理：增强 + AI + FPS 叠加（MJPEG / H.264 共用）。"""
import cv2
import time


def create_frame_processor(system_state, enhancer, ai_detector, perf_state=None):
    """工厂函数：返回一个闭包，每个流（MJPEG / H.264）拥有独立的 FPS 计数器。"""
    fps_text = "FPS: 0.0"
    last_fps_time = time.time()
    frame_count = 0

    def process(frame):
        nonlocal fps_text, last_fps_time, frame_count

        if system_state["enhancement_enabled"]:
            frame = enhancer.enhance(frame)

        if system_state["ai_enabled"]:
            try:
                display_frame = ai_detector.process_frame(
                    frame, seg_enabled=system_state["seg_enabled"]
                )
            except Exception:
                display_frame = frame.copy()
        else:
            display_frame = frame.copy()

        frame_count += 1
        curr_time = time.time()
        if curr_time - last_fps_time >= 0.5:
            fps = frame_count / (curr_time - last_fps_time)
            fps_text = f"FPS: {fps:.1f}"
            if perf_state is not None:
                perf_state["fps"] = round(fps, 1)
                perf_state["last_update"] = curr_time
            last_fps_time = curr_time
            frame_count = 0

        cv2.putText(display_frame, fps_text, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        if system_state["ai_enabled"] and ai_detector.last_count > 0:
            count_text = f"Fish: {ai_detector.last_count}"
            cv2.putText(display_frame, count_text, (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        return display_frame

    return process
