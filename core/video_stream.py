# core/video_stream.py
import cv2
import threading
import time
import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|max_delay;5000000|buffer_size;20480000"


class VideoCaptureThreading:
    """双线程读取流，含断线重连和指数退避"""

    def __init__(self, src):
        self.src = src
        self._open_capture()
        self.ret, self.frame = self.cap.read()
        self.running = True
        self.connected = self.ret
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def _open_capture(self):
        if isinstance(self.src, int):
            self.cap = cv2.VideoCapture(self.src)
        else:
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)

    def update(self):
        fail_count = 0
        backoff = 0.5

        while self.running:
            if not self.cap.isOpened():
                fail_count += 1
                backoff = min(backoff * 2, 10.0)
                time.sleep(backoff)
                self._open_capture()
                continue

            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
                self.ret = True
                self.connected = True
                fail_count = 0
                backoff = 0.5
            else:
                self.ret = False
                self.connected = False
                fail_count += 1
                backoff = min(backoff * 2, 10.0)
                time.sleep(backoff)
                self.cap.release()

    def read(self):
        return self.ret, self.frame

    def is_connected(self):
        return self.connected

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()
