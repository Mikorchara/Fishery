# core/ai_detector.py
import logging
from ultralytics import YOLO, SAM
import config
import torch
import numpy as np
from core.custom_yolo import register as _register_custom
from core.mask_tracker import MaskTracker

_register_custom()
_log = logging.getLogger("ai")


class FisheryAI:
    def __init__(self, yolo_path="models/yolov8n.pt", model_key="fish_detect_ema"):
        try:
            self._model_key = model_key
            self._cfg = config.get_model_config(model_key)
            self._model_format = "pt" if yolo_path.endswith(".pt") else "onnx"
            _log.info("加载 YOLO 模型 (%s): %s  |  conf=%.2f iou=%.2f imgsz=%d",
                      self._model_format.upper(), yolo_path,
                      self._cfg["conf"], self._cfg["iou"], self._cfg["imgsz"])
            task = "segment" if "seg" in model_key else "detect"
            self.yolo_model = YOLO(yolo_path, task=task)

            checkpoint = config.SAM2_CHECKPOINT
            _log.info("加载 SAM2 模型: %s", checkpoint)
            self.sam_model = SAM(checkpoint)

            cuda_available = torch.cuda.is_available()
            self._fp16 = cuda_available and self._model_format == "pt"
            if cuda_available:
                try:
                    self.sam_model.model = self.sam_model.model.half()
                    _log.info("SAM2: FP16 推理")
                except Exception:
                    self._fp16 = False

            self.last_count = 0
            self.last_confs = []
            self.tracking_enabled = False
            self.mask_tracker = MaskTracker(iou_thresh=0.3, max_lost=30)
            _log.info("所有 AI 模型加载成功")
        except Exception as e:
            _log.error("模型初始化失败: %s", e)
            raise e

    def load_model(self, model_path, model_key=None):
        """热切换 YOLO 模型"""
        self._model_format = "pt" if model_path.endswith(".pt") else "onnx"
        if model_key is not None:
            self._model_key = model_key
            self._cfg = config.get_model_config(model_key)
        _log.info("切换 YOLO 模型 (%s): %s  |  conf=%.2f iou=%.2f imgsz=%d",
                  self._model_format.upper(), model_path,
                  self._cfg["conf"], self._cfg["iou"], self._cfg["imgsz"])
        task = "segment" if "seg" in (model_key or self._model_key) else "detect"
        self.yolo_model = YOLO(model_path, task=task)
        self._fp16 = torch.cuda.is_available() and self._model_format == "pt"

    def process_frame(self, frame, seg_enabled=False):
        """处理一帧：YOLO 检测/跟踪 + 可选 SAM2 分割。"""

        if self.tracking_enabled and self._model_format == "pt":
            try:
                yolo_results = self.yolo_model.track(
                    frame,
                    conf=self._cfg["conf"],
                    iou=self._cfg["iou"],
                    imgsz=self._cfg["imgsz"],
                    max_det=self._cfg["max_det"],
                    quantize=16 if self._fp16 else None,
                    persist=True,
                    verbose=False,
                )
            except Exception:
                _log.warning("track() 失败，回退到 predict()")
                self.tracking_enabled = False
                yolo_results = self.yolo_model.predict(
                    frame, conf=self._cfg["conf"], iou=self._cfg["iou"],
                    imgsz=self._cfg["imgsz"], max_det=self._cfg["max_det"],
                    quantize=16 if self._fp16 else None, verbose=False,
                )
        else:
            yolo_results = self.yolo_model.predict(
                frame,
                conf=self._cfg["conf"],
                iou=self._cfg["iou"],
                imgsz=self._cfg["imgsz"],
                max_det=self._cfg["max_det"],
                quantize=16 if self._fp16 else None,
                verbose=False,
            )

        boxes = yolo_results[0].boxes
        self.last_count = len(boxes) if boxes is not None else 0
        self.last_confs = boxes.conf.tolist() if boxes is not None and boxes.conf is not None else []

        if not seg_enabled:
            return yolo_results[0].plot()

        img_h, img_w = frame.shape[:2]

        # ---- YOLO-seg 直出掩码：跳过 SAM2 ----
        if yolo_results[0].masks is not None:
            mask_data = yolo_results[0].masks.data.cpu().numpy()
            mask_list = []
            for i, m in enumerate(mask_data):
                m_u8 = (m > 0.5).astype(np.uint8)
                if m_u8.sum() < 20:
                    continue
                # 优先用检测框，否则从掩码推算
                if boxes is not None and i < len(boxes):
                    b = boxes[i].xyxy.tolist()[0]
                else:
                    ys, xs = np.where(m_u8 > 0)
                    b = [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())]
                mask_list.append((m_u8, b))

            tracked = self.mask_tracker.update(mask_list)
            vis = yolo_results[0].plot()             # GPU 渲染掩码+框
            MaskTracker.draw_ids(vis, tracked)        # CPU 叠加 ID
            self.last_count = len(mask_list)
            return vis

        # ---- SAM2 分割（检测模型回退） ----
        boxes_xyxy = boxes.xyxy.tolist() if boxes is not None else []
        if not boxes_xyxy:
            return yolo_results[0].plot()

        mode = getattr(config, "SAM_PROMPT_MODE", "point")
        points = [[(b[0] + b[2]) / 2, (b[1] + b[3]) / 2] for b in boxes_xyxy]
        labels = [1] * len(points)

        if mode == "point":
            sam_results = self.sam_model(frame, points=points, labels=labels, verbose=False)
        elif mode == "hybrid":
            eb = self._expand_boxes(boxes_xyxy, img_h, img_w, ratio=config.BOX_EXPAND_RATIO)
            sam_results = self.sam_model(frame, points=points, labels=labels, bboxes=eb, verbose=False)
        else:
            eb = self._expand_boxes(boxes_xyxy, img_h, img_w, ratio=config.BOX_EXPAND_RATIO)
            sam_results = self.sam_model(frame, bboxes=eb, verbose=False)

        if sam_results[0].masks is not None:
            mask_data = sam_results[0].masks.data.cpu().numpy()
        else:
            mask_data = np.zeros((0, img_h, img_w), dtype=np.uint8)

        mask_list = []
        for m in mask_data:
            m_u8 = (m > 0.5).astype(np.uint8)
            if m_u8.sum() < 20:
                continue
            ys, xs = np.where(m_u8 > 0)
            box = [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())]
            mask_list.append((m_u8, box))

        tracked = self.mask_tracker.update(mask_list)
        vis = sam_results[0].plot()
        MaskTracker.draw_ids(vis, tracked)
        self.last_count = len(mask_list)
        return vis

    def _expand_boxes(self, boxes, img_h, img_w, ratio=0.4):
        expanded = []
        for box in boxes:
            x1, y1, x2, y2 = box
            w, h = x2 - x1, y2 - y1
            dw, dh = w * ratio, h * ratio
            expanded.append([
                max(0, x1 - dw),
                max(0, y1 - dh),
                min(img_w, x2 + dw),
                min(img_h, y2 + dh)
            ])
        return expanded
