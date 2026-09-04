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
import core.llm_settings as llm_settings_cfg
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

def _llm_default_triple():
    """系统默认三件套（config.py / .env）。"""
    return config.LLM_BASE_URL, config.LLM_API_KEY, config.LLM_MODEL


def _apply_llm_active():
    """启动时若存有已启用方案则热切换，否则保持系统默认。"""
    prof = llm_settings_cfg.get_active_profile()
    if prof:
        llm_advisor.reconfigure(prof["base_url"], prof["api_key"], prof["model"])
        log.info("LLM 已启用保存的方案「%s」→ %s", prof["name"], prof["model"])


def _llm_err_message(e):
    """把 openai SDK 异常翻译成中文可读提示。"""
    import openai
    if isinstance(e, openai.AuthenticationError):
        return "API Key 无效或未授权（401），请检查 Key"
    if isinstance(e, openai.PermissionDeniedError):
        return "该 API Key 无权访问此服务（403）"
    if isinstance(e, openai.NotFoundError):
        return "找不到该模型（404）—— 请点「获取模型」选择服务商真实提供的模型 ID"
    if isinstance(e, openai.RateLimitError):
        return "请求过于频繁或账户余额不足（429）"
    if isinstance(e, openai.APIConnectionError):
        return "无法连接到该地址，请检查 Base URL 是否正确、网络是否可达"
    if isinstance(e, openai.BadRequestError):
        return "请求参数有误（400）：" + str(getattr(e, "message", e))[:120]
    if isinstance(e, openai.APIStatusError):
        return f"服务端异常（HTTP {e.status_code}）：{str(getattr(e, 'message', e))[:120]}"
    return f"连接失败：{str(e)[:160]}"


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


# -- LLM 服务配置管理（新增 / 保存 / 启用 / 禁用，见设置弹窗） --

@app.route('/llm_profiles', methods=['GET'])
@require_auth
def llm_profiles():
    """返回所有已保存方案（Key 打码）与当前生效状态。"""
    profiles, active_id = llm_settings_cfg.list_profiles_masked()
    base_url, _, model = _llm_default_triple()
    return jsonify({
        "profiles": profiles,
        "active_id": active_id,
        "default": {"base_url": base_url, "model": model},
    })


@app.route('/llm_profiles/save', methods=['POST'])
@require_auth
def llm_profile_save():
    """新增或更新一套方案；若更新的正是当前启用项则同步热切换（保存即生效）。"""
    try:
        profile, is_new = llm_settings_cfg.upsert(request.get_json() or {})
        active = llm_settings_cfg.get_active_profile()
        if not is_new and active and profile["id"] == active["id"]:
            llm_advisor.reconfigure(profile["base_url"], profile["api_key"], profile["model"])
        return jsonify({"status": "success", "id": profile["id"], "is_new": is_new})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        log.error("保存 LLM 方案失败: %s", e)
        return jsonify({"status": "error", "message": f"保存失败: {e}"}), 500


@app.route('/llm_profiles/activate', methods=['POST'])
@require_auth
def llm_profile_activate():
    """启用某方案：立即重建连接并持久化 active_id，重启后仍生效。"""
    pid = (request.get_json() or {}).get("id") or ""
    try:
        prof = llm_settings_cfg.activate(pid)
        llm_advisor.reconfigure(prof["base_url"], prof["api_key"], prof["model"])
        return jsonify({"status": "success", "name": prof["name"], "model": prof["model"]})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/llm_profiles/disable', methods=['POST'])
@require_auth
def llm_profile_disable():
    """禁用自定义方案：回落到系统默认（config.py / .env），无需重启。"""
    llm_settings_cfg.deactivate()
    base_url, api_key, model = _llm_default_triple()
    llm_advisor.reconfigure(base_url, api_key, model)
    return jsonify({"status": "success", "model": model, "base_url": base_url})


@app.route('/llm_profiles/delete', methods=['POST'])
@require_auth
def llm_profile_delete():
    """删除方案；若删的正是启用项则自动回落到系统默认。"""
    pid = (request.get_json() or {}).get("id") or ""
    was_active = llm_settings_cfg.delete_profile(pid)
    if was_active:
        base_url, api_key, model = _llm_default_triple()
        llm_advisor.reconfigure(base_url, api_key, model)
    return jsonify({"status": "success"})


@app.route('/llm_test', methods=['POST'])
@require_auth
def llm_test():
    """用界面填写的 地址/Key/模型 做一次 1-token 探针，校验三件套。"""
    d = request.get_json() or {}
    base_url = (d.get("base_url") or "").strip().rstrip("/")
    api_key = (d.get("api_key") or "").strip()
    model = (d.get("model") or "").strip()
    # Key 留空但给了方案 id → 复用已保存的明文 Key（编辑未改 Key 也能测试）
    if not api_key and (d.get("id") or ""):
        saved = llm_settings_cfg.get_profile_by_id(d.get("id"))
        if saved:
            api_key = saved.get("api_key", "")
            base_url = base_url or saved.get("base_url", "")
            model = model or saved.get("model", "")
    if not (base_url and api_key and model):
        return jsonify({"status": "error", "message": "Base URL / API Key / 模型 ID 均需填写（编辑已有方案可留空 Key）"}), 400
    try:
        from openai import OpenAI
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=15)
        client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "ping"}], max_tokens=1)
        return jsonify({"status": "success", "message": f"连接成功，模型可用：{model}"})
    except Exception as e:
        return jsonify({"status": "error", "message": _llm_err_message(e)})


@app.route('/llm_models', methods=['POST'])
@require_auth
def llm_models():
    """用 地址+Key 从服务商拉取该 Key 真实可用的模型列表，避免手填错模型 ID。"""
    d = request.get_json() or {}
    base_url = (d.get("base_url") or "").strip().rstrip("/")
    api_key = (d.get("api_key") or "").strip()
    if not api_key and (d.get("id") or ""):
        saved = llm_settings_cfg.get_profile_by_id(d.get("id"))
        if saved:
            api_key = saved.get("api_key", "")
            base_url = base_url or saved.get("base_url", "")
    if not (base_url and api_key):
        return jsonify({"status": "error", "message": "请先填写 Base URL 与 API Key（编辑已有方案可留空 Key）"}), 400
    try:
        from openai import OpenAI
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=15)
        ids = sorted(m.id for m in client.models.list().data)
        if not ids:
            return jsonify({"status": "error", "message": "该服务未返回任何模型"})
        return jsonify({"status": "success", "models": ids})
    except Exception as e:
        return jsonify({"status": "error", "message": _llm_err_message(e)})


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

    _apply_llm_active()   # 启动时恢复上次启用的 LLM 方案（若存在）
    log.info("系统启动: http://127.0.0.1:%d", config.WEB_PORT)
    log.info("  MJPEG  (HTTP): http://127.0.0.1:%d/video_feed", config.WEB_PORT)
    log.info("  H.264   (WS):  ws://127.0.0.1:%d/ws_video", config.WEB_PORT)
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, threaded=True)

#ffmpeg -re -stream_loop -1 -i test_video_2.mp4 -c copy -rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/mystream
# ffmpeg -re -loop 1 -i optest_img.jpg -c:v libx264 -tune stillimage -pix_fmt yuv420p -rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/mystream