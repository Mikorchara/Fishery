# app.py
import cv2
import time
import os
import threading
import logging
import sys
from functools import wraps
from flask import Flask, render_template, Response, jsonify, request
from flask_sock import Sock

# ---- 日志 ----
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE = "%H:%M:%S"
logging.basicConfig(
    level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATE,
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("app.log", encoding="utf-8")],
)
logging.getLogger("werkzeug").setLevel(logging.WARNING)
log = logging.getLogger("app")

# ---- 模块 ----
import config
config.validate()
from core.video_stream import VideoCaptureThreading
from core.ai_detector import FisheryAI
from core.enhancer import WWEEnhancer
from core.llm_advisor import FisheryAdvisor
from core.storage import Storage
from core.frame_processor import create_frame_processor
from core.ws_handler import register_ws

# ---- Flask ----
app = Flask(__name__)
sock = Sock(app)

def require_auth(f):
    @wraps(f)
    def wrapper(*a, **kw):
        expected = f"Bearer {config.AUTH_TOKEN}"
        if request.headers.get("Authorization", "") != expected:
            return jsonify({"status": "error", "message": "未授权访问"}), 401
        return f(*a, **kw)
    return wrapper

# ---- 全局状态 ----
system_state = {"ai_enabled": True, "enhancement_enabled": False, "seg_enabled": False}
video_stream = VideoCaptureThreading(config.STREAM_URL)
ai_detector = FisheryAI(config.AVAILABLE_MODELS[config.DEFAULT_MODEL_KEY], model_key=config.DEFAULT_MODEL_KEY)
enhancer = WWEEnhancer()
storage = Storage()
llm_advisor = FisheryAdvisor()
mcu_data = {"temp": "--", "ph": "--", "oxygen": "--", "last_update": "未连接"}
recording = False
video_writer = None
record_lock = threading.Lock()
event_log: list = []
last_processed_frame = None  # 截图复用，避免抢流
perf_state = {"fps": 0.0, "last_update": 0}  # 性能快照，frame_processor 每 0.5s 更新

# 注册 H.264 WebSocket
register_ws(sock, video_stream, lambda: create_frame_processor(system_state, enhancer, ai_detector, perf_state))

# 预创建输出目录
ROOT = os.path.dirname(os.path.abspath(__file__))
CAPTURES_DIR = os.path.join(ROOT, 'captures')
RECORDINGS_DIR = os.path.join(ROOT, 'recordings')
os.makedirs(CAPTURES_DIR, exist_ok=True)
os.makedirs(RECORDINGS_DIR, exist_ok=True)


# -- MJPEG 视频流 --

def generate_frames():
    global last_processed_frame
    processor = create_frame_processor(system_state, enhancer, ai_detector, perf_state)
    while True:
        ret, frame = video_stream.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
        display_frame = processor(frame)
        last_processed_frame = display_frame.copy()

        if recording:
            with record_lock:
                if video_writer is not None:
                    video_writer.write(display_frame)

        ret, buffer = cv2.imencode('.jpg', display_frame)
        if not ret:
            continue
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


# -- 路由 --

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/health')
def health():
    return jsonify({
        'stream_ok': video_stream.is_connected(),
        'ai_loaded': ai_detector is not None,
        'enhancer_loaded': enhancer is not None,
        'recording': recording,
    })

@app.route('/perf_snapshot')
def perf_snapshot():
    data = {
        'fps': perf_state['fps'],
        'ai_enabled': system_state['ai_enabled'],
        'enhancement_enabled': system_state['enhancement_enabled'],
        'seg_enabled': system_state['seg_enabled'],
        'model_key': ai_detector._model_key if ai_detector else '--',
        'fish_count': ai_detector.last_count if ai_detector else 0,
        'ts': time.time(),
    }
    # GPU 显存
    try:
        import pynvml
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(h)
        util = pynvml.nvmlDeviceGetUtilizationRates(h)
        data['gpu_mem_mb'] = round(info.used / 1024 / 1024, 1)
        data['gpu_mem_total_mb'] = round(info.total / 1024 / 1024, 1)
        data['gpu_util_pct'] = util.gpu
    except Exception:
        pass
    # CPU / RAM
    try:
        import psutil
        data['cpu_pct'] = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        data['ram_mb'] = round(mem.used / 1024 / 1024, 1)
        data['ram_total_mb'] = round(mem.total / 1024 / 1024, 1)
    except Exception:
        pass
    return jsonify(data)

# -- AI 控制 --

@app.route('/toggle_ai', methods=['POST'])
@require_auth
def toggle_ai():
    system_state["ai_enabled"] = not system_state["ai_enabled"]
    return jsonify({'ai_enabled': system_state["ai_enabled"]})

@app.route('/toggle_enhancement', methods=['POST'])
@require_auth
def toggle_enhancement():
    system_state["enhancement_enabled"] = not system_state["enhancement_enabled"]
    return jsonify({'enhancement_enabled': system_state["enhancement_enabled"]})

@app.route('/toggle_segmentation', methods=['POST'])
@require_auth
def toggle_segmentation():
    system_state["seg_enabled"] = not system_state["seg_enabled"]
    return jsonify({'seg_enabled': system_state["seg_enabled"]})

@app.route('/switch_model', methods=['POST'])
@require_auth
def switch_model():
    data = request.get_json()
    key = data.get('model_key')
    if key not in config.AVAILABLE_MODELS:
        return jsonify({'status': 'error', 'message': '未知模型'}), 400
    try:
        ai_detector.load_model(config.AVAILABLE_MODELS[key], model_key=key)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# -- 传感器 --

@app.route('/update_sensor', methods=['POST'])
@require_auth
def update_sensor():
    try:
        data = request.get_json()
        if not data: return jsonify({'status': 'error'}), 400
        for k in ("temp", "ph", "oxygen"):
            v = data.get(k)
            if v is not None:
                try:
                    fv = float(v)
                    if not (-50 <= fv <= 100):
                        return jsonify({'status': 'error', 'msg': f'{k} 值 {fv} 超出合理范围'}), 400
                except (ValueError, TypeError):
                    return jsonify({'status': 'error', 'msg': f'{k} 值 "{v}" 无效'}), 400
                mcu_data[k] = str(fv)
        mcu_data["last_update"] = time.strftime("%H:%M:%S")
        storage.add_sensor(mcu_data["temp"], mcu_data["ph"], mcu_data["oxygen"])
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500

@app.route('/get_sensor')
def get_sensor():
    return jsonify(mcu_data)

@app.route('/get_sensor_history')
def get_sensor_history():
    return jsonify(storage.get_sensor_history(minutes=120))

# -- 告警 & 事件 --

@app.route('/check_alarm')
def check_alarm():
    alarms = llm_advisor.kb.get_alarms(
        str(mcu_data.get("temp", "--")),
        str(mcu_data.get("ph", "--")),
        str(mcu_data.get("oxygen", "--"))
    )
    now = time.strftime("%m-%d %H:%M:%S")
    recent_keys = {e["message"] for e in event_log if time.time() - e.get("_ts", 0) < 30}
    for level, msg in alarms:
        if level == "critical" and msg not in recent_keys:
            event_log.insert(0, {"time": now, "type": "alarm", "level": level,
                                 "message": msg, "_ts": time.time()})
            recent_keys.add(msg)
            storage.add_event(level, msg)
    now_ts = time.time()
    event_log[:] = [e for e in event_log if (
        e["level"] == "critical" and e.get("_ts", 0) > now_ts - 1800
    ) or (
        e["level"] != "critical" and e.get("_ts", 0) > now_ts - 120
    )][:30]
    return jsonify({"alarms": [{"level": l, "message": m} for l, m in alarms]})

@app.route('/get_events')
def get_events():
    mem = [{k: v for k, v in e.items() if k != "_ts"} for e in event_log[:20]]
    if not mem:
        mem = storage.get_events(20, minutes=30)
    return jsonify({"events": mem})

# -- LLM --

@app.route('/get_ai_advice', methods=['POST'])
@require_auth
def get_ai_advice():
    return jsonify({'advice': llm_advisor.get_advice(mcu_data)})

@app.route('/chat_ai', methods=['POST'])
@require_auth
def chat_ai():
    try:
        data = request.get_json()
        msg = data.get('message', '')
        if not msg:
            return jsonify({'response': '你想问我什么呢？'}), 400
        log.info("收到用户咨询: %s", msg[:100])
        return jsonify({'response': llm_advisor.ask_question(msg, mcu_data)})
    except Exception as e:
        return jsonify({'response': f'对话引擎出了一点小状况: {str(e)}'}), 500

# -- 截图 & 录制 --

@app.route('/capture_frame', methods=['POST'])
@require_auth
def capture_frame():
    global last_processed_frame
    frame = last_processed_frame
    if frame is None:
        return jsonify({'status': 'error', 'message': '暂无已处理帧'}), 500
    ts = time.strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(os.path.join(CAPTURES_DIR, f"capture_{ts}.jpg"), frame)
    return jsonify({'status': 'success', 'filename': f"capture_{ts}.jpg"})

@app.route('/start_recording', methods=['POST'])
@require_auth
def start_recording():
    global video_writer, recording
    with record_lock:
        if recording:
            return jsonify({'status': 'error', 'message': '已在录制中'})
        ret, frame = video_stream.read()
        if not ret or frame is None:
            return jsonify({'status': 'error', 'message': '无法获取视频帧'}), 500
        h, w = frame.shape[:2]
        ts = time.strftime('%Y%m%d_%H%M%S')
        filename = f"record_{ts}.mp4"
        for codec in ['mp4v', 'XVID', 'avc1']:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            video_writer = cv2.VideoWriter(os.path.join(RECORDINGS_DIR, filename), fourcc, 30.0, (w, h))
            if video_writer.isOpened():
                break
        if not video_writer or not video_writer.isOpened():
            video_writer = None
            return jsonify({'status': 'error', 'message': '编码器打开失败'}), 500
        recording = True
        return jsonify({'status': 'success', 'filename': filename})

@app.route('/stop_recording', methods=['POST'])
@require_auth
def stop_recording():
    global video_writer, recording
    with record_lock:
        if not recording:
            return jsonify({'status': 'error', 'message': '未在录制'})
        recording = False
        if video_writer:
            video_writer.release()
            video_writer = None
        return jsonify({'status': 'success'})


# -- 启动 --

if __name__ == '__main__':
    import signal
    import atexit

    def cleanup():
        log.info("正在清理资源...")
        video_stream.stop()
        if video_writer is not None:
            try: video_writer.release()
            except Exception: pass
        storage.close()
        log.info("资源清理完成")

    atexit.register(cleanup)
    def _signal_handler(sig, frame):
        log.info("收到信号 %s，正在退出...", sig)
        cleanup()
        sys.exit(0)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    log.info("系统启动: http://127.0.0.1:%d", config.WEB_PORT)
    log.info("  MJPEG  (HTTP): http://127.0.0.1:%d/video_feed", config.WEB_PORT)
    log.info("  H.264   (WS):  ws://127.0.0.1:%d/ws_video", config.WEB_PORT)
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, threaded=True)

#ffmpeg -re -stream_loop -1 -i test_video_2.mp4 -c copy -rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/mystream
# ffmpeg -re -loop 1 -i optest_img.jpg -c:v libx264 -tune stillimage -pix_fmt yuv420p -rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/mystream