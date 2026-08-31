"""掩码帧间 IoU 跟踪 — 只匹配 ID，不负责画图。"""
import numpy as np
import cv2


class MaskTracker:
    def __init__(self, iou_thresh: float = 0.3, max_lost: int = 30):
        self.iou_thresh = iou_thresh
        self.max_lost = max_lost
        self._tracks = {}
        self._next_id = 1
        self._frame_idx = 0

    def update(self, mask_list):
        """
        mask_list: [(mask_uint8, box_xyxy), ...]  当前帧的掩码
        返回: [(track_id, mask, box), ...]  ID 分配结果
        """
        self._frame_idx += 1
        assigned = {}

        for i, (mi, _) in enumerate(mask_list):
            best_tid, best_iou = -1, 0.0
            for tid, t in self._tracks.items():
                iou = self._mask_iou(mi, t["mask"])
                if iou > best_iou:
                    best_iou, best_tid = iou, tid
            assigned[i] = best_tid if best_iou >= self.iou_thresh else self._next_id
            if assigned[i] == self._next_id:
                self._next_id += 1

        updated_ids = set(assigned.values())
        for i, (mi, _) in enumerate(mask_list):
            self._tracks[assigned[i]] = {"mask": mi.copy(), "lost": 0}

        for tid in list(self._tracks.keys()):
            if tid not in updated_ids:
                self._tracks[tid]["lost"] += 1
                if self._tracks[tid]["lost"] > self.max_lost:
                    del self._tracks[tid]

        return [(assigned[i], mask_list[i][0], mask_list[i][1]) for i in range(len(mask_list))]

    @staticmethod
    def _mask_iou(a, b):
        aa, bb = a.astype(bool), b.astype(bool)
        inter = np.logical_and(aa, bb).sum()
        union = np.logical_or(aa, bb).sum()
        return float(inter / union) if union > 0 else 0.0

    @staticmethod
    def draw_ids(frame, results):
        """在已有帧上叠加 ID 文字（仅 CPU putText，极快）。"""
        for tid, _, box in results:
            color = _id_color(tid)
            x1, y1 = int(box[0]), int(box[1])
            cv2.putText(frame, str(tid), (x1, max(20, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def _id_color(tid):
    rng = np.random.default_rng(tid * 1009 + 17)
    return tuple(int(v) for v in rng.integers(60, 255, 3))
