# config.py
import os
from pathlib import Path

# 自动加载项目根目录的 .env 文件
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                _key, _val = _key.strip(), _val.strip().strip('"').strip("'")
                if _key not in os.environ:
                    os.environ[_key] = _val

# 视频流配置
STREAM_URL = "rtsp://127.0.0.1:8554/mystream" 
WEB_HOST = '0.0.0.0'
WEB_PORT = 5000

# 🌟 新增：多模型配置字典
AVAILABLE_MODELS = {
    "fish_detect_ema": "models/fish_detect_m.pt",   # YOLO 标准鱼群检测 (含 EMA)
    "fish_detect_seam": "models/fish_detect_seam.pt",        # YOLO 改进版鱼群检测 (含 SEAM)
    "fish_onnx": "models/fish_detect.onnx",     # YOLO 鱼群检测 (ONNX opset 11)
    "disease_alert": "models/fish_disease.pt",   # 占位：未来可替换为病鱼模型
    "fish_seg": "models/fish_seg_yolo26.pt",    # YOLO-seg 鳗鱼实例分割 (直出掩码，无需 SAM2)
    "fish_seg_nano": "models/fish_seg_yolo26_nano.pt",  # YOLO-seg nano 轻量版 (PyTorch)
    "fish_seg_yolo11": "models/fish_seg_yolo11n.pt",  # YOLO11 nano seg (PyTorch)
    "fish_seg_yolo11_onnx": "models/fish_seg_yolo11n.onnx",  # YOLO11 nano seg (ONNX)
    "fish_seg_nano_onnx": "models/fish_seg_yolo26_nano.onnx",  # YOLO-seg nano ONNX
    "fish_bifpn": "models/fish_detect_s_ECA_EMA_BIFPN.pt",  # YOLO26s ECA+EMA+BiFPN+P2 检测头
}

# 默认启动时加载的模型
DEFAULT_MODEL_KEY = "fish_detect_ema"

# AI 推理置信度阈值 (0-1)
# 低于此值的检测框将被过滤掉
CONF_THRESHOLD = 0.75
# 1. IOU 阈值 (重叠度)
# 两个框重叠比例超过这个值时，会被认为是一个目标（用于去重）
# 如果您的鱼经常重叠，可以调大这个值 (如 0.6)；如果出现重复框，调小它 (如 0.3)
IOU_THRESHOLD = 0.4
# 2. 推理图片尺寸
# YOLO 默认是 640。调大（如 800）可以提升对小目标的检测能力，但会降低速度
# 必须是 32 的倍数
IMG_SIZE = 640
# 3. 最大检测数量
# 单张画面中最多允许识别出多少条鱼
MAX_DET = 100

# ==========================================
# Per-Model 推理参数（未指定的字段回退到上方全局默认值）
# ==========================================
MODEL_CONFIGS = {
    "fish_detect_ema": {"conf": 0.4},
    "fish_detect_seam": {"conf": 0.25},
    "fish_onnx":     {"conf": 0.4},
    "disease_alert": {"conf": 0.4},
    "fish_seg":      {"conf": 0.5},
    "fish_seg_nano": {"conf": 0.5},
    "fish_seg_yolo11": {"conf": 0.5},
    "fish_seg_yolo11_onnx": {"conf": 0.25},
    "fish_seg_nano_onnx": {"conf": 0.5},
    "fish_bifpn":   {"conf": 0.2},
}

def get_model_config(model_key):
    """获取指定模型的推理参数，缺省字段用全局默认值"""
    defaults = {"conf": CONF_THRESHOLD, "iou": IOU_THRESHOLD, "imgsz": IMG_SIZE, "max_det": MAX_DET}
    overrides = MODEL_CONFIGS.get(model_key, {})
    return {**defaults, **overrides}

# ==========================================
# ==========================================
# SAM 2 分割模型配置
# ==========================================
SAM2_CHECKPOINT = "models/sam2.1_t.pt"
SAM2_CONFIG = "models/sam2_hiera_t.yaml"
MASK_ALPHA = 0.5

# 💡 提示策略优化 (针对鳗鱼等长条形目标)
# 模式支持: 'box' (纯框), 'point' (纯点), 'hybrid' (点框结合)
SAM_PROMPT_MODE = 'point'
BOX_EXPAND_RATIO = 0.5                   # 扩框比例 (在 hybrid 或 box 模式下生效)

# ==========================================
# WWE-UIE 图像增强性能配置
# ==========================================
ENHANCE_FP16 = True           # FP16 推理（约 2x 提速，质量几乎无损）
ENHANCE_MAX_SIDE = 640        # 处理前缩放到此尺寸以内（0 = 不缩放）
ENHANCE_COMPILE = True        # torch.compile JIT（PyTorch 2.0+，首次慢，后续快）

# ==========================================
# DeepSeek LLM 配置
# ==========================================
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
LLM_BASE_URL = "https://api.deepseek.com"
LLM_MODEL = "deepseek-v4-flash"

# LLM 输出 token 上限（max_tokens 限制的是“生成/输出”token，不是输入；输入受上下文窗口总长限制）
# 2026-09-05：原 1024 对“思考型模型 + 长报告”会导致正文被截断（思考 token 也占该预算），故提高并拆两档：
#  - 报告生成通常较长且思考型模型思考占预算 → 4096
#  - 自由对话较短 → 2048（若想更快可再调低）
LLM_REPORT_MAX_TOKENS = 4096
LLM_CHAT_MAX_TOKENS = 2048

# H.264 WebSocket 编码器: "libx264" (CPU软编) 或 "h264_nvenc" (NVIDIA硬编)
H264_ENCODER = os.environ.get("H264_ENCODER", "h264_nvenc")

# 简易 Token 认证（仅保护 POST 写操作，GET 读取和视频流不限制）
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "fishery2026")

def validate():
    """启动时校验配置，失败则抛出明确错误"""
    import sys
    errors = []

    if not LLM_API_KEY:
        errors.append("DEEPSEEK_API_KEY 环境变量未设置，LLM 功能将不可用。请设置: set DEEPSEEK_API_KEY=your_key")

    # 检查模型文件
    model_paths = [
        (AVAILABLE_MODELS.get(DEFAULT_MODEL_KEY, ""), "默认 YOLO 模型"),
        (SAM2_CHECKPOINT, "SAM2 模型"),
        (SAM2_CONFIG, "SAM2 配置文件"),
    ]
    for path, name in model_paths:
        if path and not Path(path).exists():
            errors.append(f"{name}不存在: {path}")

    # 阈值范围检查
    if not (0 <= CONF_THRESHOLD <= 1):
        errors.append(f"CONF_THRESHOLD 需在 [0,1] 范围，当前值: {CONF_THRESHOLD}")
    if not (0 <= IOU_THRESHOLD <= 1):
        errors.append(f"IOU_THRESHOLD 需在 [0,1] 范围，当前值: {IOU_THRESHOLD}")

    if errors:
        
        import logging
        clog = logging.getLogger("config")
        clog.error("配置错误:")
        for e in errors:
            clog.error("  - %s", e)
        fatal = [e for e in errors if "API_KEY" not in e]
        if fatal:
            sys.exit(1)
