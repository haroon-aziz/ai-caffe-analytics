from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from config import Config, get_config
from detection.detections import Detections
from utils import image as img_utils
from utils.image import Color

_PALETTE: Tuple[Color, ...] = (
    (231, 76, 60),
    (46, 204, 113),
    (241, 196, 15),
    (155, 89, 182),
    (26, 188, 156),
    (230, 126, 34),
    (52, 152, 219),
    (149, 165, 166),
)


class DetectionAnnotator:
    def __init__(
        self,
        config: Optional[Config] = None,
        color_by: str = "class",
        show_confidence: bool = True,
        thickness: int = 2,
    ) -> None:
        self.config = config or get_config()
        self.color_by = color_by
        self.show_confidence = show_confidence
        self.thickness = thickness

    def _color_for(self, class_id: int, tracker_id: Optional[int]) -> Color:
        key = tracker_id if (self.color_by == "track" and tracker_id is not None) else class_id
        return _PALETTE[int(key) % len(_PALETTE)]

    def _label_for(self, class_name: Optional[str], class_id: int,
                   confidence: float, tracker_id: Optional[int]) -> str:
        name = class_name or str(class_id)
        parts = []
        if tracker_id is not None:
            parts.append(f"#{tracker_id}")
        parts.append(name)
        if self.show_confidence:
            parts.append(f"{confidence:.2f}")
        return " ".join(parts)

    def annotate(self, frame: np.ndarray, detections: Detections, copy: bool = True) -> np.ndarray:
        canvas = frame.copy() if copy else frame
        import cv2

        for det in detections:
            x1, y1, x2, y2 = (int(v) for v in det.xyxy)
            color = self._color_for(det.class_id, det.tracker_id)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, self.thickness)
            label = self._label_for(det.class_name, det.class_id, det.confidence, det.tracker_id)
            img_utils.draw_label(canvas, label, (x1, max(y1, 14)), color)
        return canvas

    def annotate_count(
        self, frame: np.ndarray, detections: Detections, copy: bool = False
    ) -> np.ndarray:
        canvas = frame if not copy else frame.copy()
        counts: dict[str, int] = {}
        for det in detections:
            name = det.class_name or str(det.class_id)
            counts[name] = counts.get(name, 0) + 1
        y = 24
        for name, n in counts.items():
            img_utils.draw_label(canvas, f"{name}: {n}", (8, y), self.config_primary_bgr)
            y += 26
        return canvas

    @property
    def config_primary_bgr(self) -> Color:
        return img_utils.hex_to_bgr(self.config.dashboard.primary_color)
