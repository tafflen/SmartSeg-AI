"""YOLOv8n inference and its configurable translation to SmartSeg categories."""
from __future__ import annotations

import logging
import random
from typing import Any

import config

LOGGER = logging.getLogger(__name__)


class WasteDetector:
    def __init__(self, model_path: str = config.MODEL_PATH, mock_mode: bool = config.MOCK_MODE) -> None:
        self.mapping = config.YOLO_CATEGORY_MAPPING
        self.mock_mode = mock_mode
        self.model: Any | None = None
        if not mock_mode:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            LOGGER.info("Loaded YOLO model: %s", model_path)

    def classify(self, frame: Any) -> dict[str, Any]:
        if self.mock_mode:
            category = random.choice(["PLASTIC", "ORGANIC", "METAL", "OTHER"])
            confidence = round(random.uniform(0.52, 0.96), 3)
            return {"category": category, "confidence_score": confidence,
                    "low_confidence": False, "raw_detections": [{"class_name": "mock_item", "confidence": confidence}]}

        assert self.model is not None
        result = self.model(frame, verbose=False)[0]
        detections: list[dict[str, Any]] = []
        best_category = "OTHER"
        best_confidence = 0.0
        for box in result.boxes:
            confidence = float(box.conf[0])
            class_name = result.names[int(box.cls[0])]
            category = self.mapping.get(class_name, "OTHER")
            detections.append({"class_name": class_name, "category": category, "confidence": round(confidence, 4)})
            # Prefer the strongest mapped waste label, instead of an unrelated COCO object.
            if category != "OTHER" and confidence > best_confidence:
                best_category, best_confidence = category, confidence

        low_confidence = best_confidence < config.CONFIDENCE_THRESHOLD
        # Unknown or weak detections deliberately fall back to OTHER for safe routing.
        if low_confidence:
            best_category = "OTHER"
        return {"category": best_category, "confidence_score": round(best_confidence, 4),
                "low_confidence": low_confidence, "raw_detections": detections}
