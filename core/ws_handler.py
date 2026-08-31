"""WebSocket H.264 视频流端点。"""
import json
import time
import threading
import logging
import config
from core.h264_streamer import H264Encoder

_log = logging.getLogger("h264")


def register_ws(sock, video_stream, frame_processor):
    """注册 WebSocket 路由到 Flask-Sock 实例。"""

    @sock.route('/ws_video')
    def video_ws(ws):
        ret, frame = video_stream.read()
        if not ret or frame is None:
            ws.send(json.dumps({"type": "error", "message": "无法获取视频源"}))
            return
        height, width = frame.shape[:2]

        try:
            encoder = H264Encoder(width, height, fps=30, encoder=config.H264_ENCODER)
            encoder.start()
        except RuntimeError as e:
            ws.send(json.dumps({"type": "error", "message": str(e)}))
            return

        timeout = 5.0
        while encoder.init_segment is None and timeout > 0:
            time.sleep(0.05)
            timeout -= 0.05
        if encoder.init_segment is None:
            ws.send(json.dumps({"type": "error", "message": "编码器初始化超时"}))
            encoder.stop()
            return

        ws.send(json.dumps({"type": "meta", "width": width, "height": height}))
        ws.send(encoder.init_segment)
        _log.info("[H264] WebSocket 连接: %dx%d, init=%dB", width, height, len(encoder.init_segment))

        processor = frame_processor()
        running = True
        producer_error = []

        def producer():
            nonlocal running
            while running:
                try:
                    ret, frame = video_stream.read()
                    if not ret or frame is None:
                        time.sleep(0.01)
                        continue
                    display_frame = processor(frame)
                    encoder.encode_frame(display_frame)
                except Exception as e:
                    _log.error("[H264] Producer 异常: %s", e)
                    producer_error.append(e)
                    running = False
                    break

        producer_thread = threading.Thread(target=producer, daemon=True)
        producer_thread.start()

        empty_retries = 0
        try:
            while running and not producer_error:
                seg = encoder.get_segment(block=True, timeout=1.0)
                if seg is None:
                    if encoder.running and running and empty_retries < 15:
                        empty_retries += 1
                        continue
                    break
                empty_retries = 0
                try:
                    ws.send(seg)
                except Exception:
                    running = False
                    break

            if producer_error:
                ws.send(json.dumps({
                    "type": "error",
                    "message": f"处理帧异常: {producer_error[0]}"
                }))
        finally:
            running = False
            encoder.stop()
            _log.info("[H264] WebSocket 断开，编码器已释放 (error=%s)", bool(producer_error))
