"""YOLOv8n inference and SmartSeg waste-category classification."""
from __future__ import annotations

import logging
import os
import random
from typing import Any

import config

LOGGER = logging.getLogger(__name__)


class WasteDetector:
    def __init__(
        self,
        model_path: str = config.MODEL_PATH,
        mock_mode: bool = config.MOCK_MODE,
    ) -> None:
        self.mapping = config.YOLO_CATEGORY_MAPPING
        self.mock_mode = mock_mode
        self.model: Any | None = None

        # Demo-only selector.
        # CARDBOARD -> BIODEGRADABLE
        # BATTERY   -> HAZARDOUS
        #
        # Sensor readings are STILL read from the real Arduino.
        self.demo_item = os.getenv("SMARTSEG_DEMO_ITEM", "").strip().upper()

        if not mock_mode:
            from ultralytics import YOLO

            self.model = YOLO(model_path)
            LOGGER.info("Loaded YOLO model: %s", model_path)

        if self.demo_item:
            LOGGER.info(
                "SmartSeg demo item mode enabled: %s",
                self.demo_item,
            )

    def classify(
        self,
        frame: Any,
        sensor_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        # =========================================================
        # MOCK MODE
        # =========================================================

        if self.mock_mode:
            category = random.choice(
                ["PLASTIC", "ORGANIC", "METAL", "OTHER"]
            )

            confidence = round(
                random.uniform(0.52, 0.96),
                3,
            )

            return {
                "category": category,
                "confidence_score": confidence,
                "low_confidence": False,
                "raw_detections": [
                    {
                        "class_name": "mock_item",
                        "confidence": confidence,
                    }
                ],
                "sensor_override": None,
            }

        assert self.model is not None

        # =========================================================
        # REAL YOLO INFERENCE
        # =========================================================

        result = self.model(
            frame,
            verbose=False,
        )[0]

        detections: list[dict[str, Any]] = []

        best_category = "OTHER"
        best_confidence = 0.0
        best_class_name = "unknown"

        for box in result.boxes:

            confidence = float(box.conf[0])

            class_name = result.names[
                int(box.cls[0])
            ]

            category = self.mapping.get(
                class_name.lower(),
                "OTHER",
            )

            detections.append(
                {
                    "class_name": class_name,
                    "category": category,
                    "confidence": round(
                        confidence,
                        4,
                    ),
                }
            )

            if (
                category != "OTHER"
                and confidence > best_confidence
            ):
                best_category = category
                best_confidence = confidence
                best_class_name = class_name

        # =========================================================
        # DEMO ITEM
        #
        # This is only used when SMARTSEG_DEMO_ITEM is supplied.
        # Real Arduino sensor values continue to be included.
        # =========================================================

        if self.demo_item == "CARDBOARD":

            best_category = "BIODEGRADABLE"

            # High-confidence demo classification.
            best_confidence = max(
                best_confidence,
                0.94,
            )

            best_class_name = "cardboard"

            LOGGER.info(
                "Demo visual classification: "
                "cardboard -> BIODEGRADABLE"
            )

        elif self.demo_item == "BATTERY":

            best_category = "HAZARDOUS"

            best_confidence = max(
                best_confidence,
                0.94,
            )

            best_class_name = "battery"

            LOGGER.info(
                "Demo visual classification: "
                "battery -> HAZARDOUS"
            )

        else:

            # =====================================================
            # REAL SENSOR CLASSIFICATION
            # =====================================================

            sensor_category = self._classify_from_sensors(
                sensor_context
            )

            if sensor_category is not None:

                if best_confidence > 0:
                    final_confidence = best_confidence
                else:
                    final_confidence = 0.90

                best_category = sensor_category
                best_confidence = final_confidence

        low_confidence = (
            best_confidence
            < config.CONFIDENCE_THRESHOLD
        )

        # Only reject weak results when there is no
        # useful sensor/demo information.
        if low_confidence and not self.demo_item:
            sensor_category = self._classify_from_sensors(
                sensor_context
            )

            if sensor_category is None:
                best_category = "OTHER"

        LOGGER.info(
            "YOLO classification: class=%s "
            "category=%s confidence=%.3f "
            "sensor_context=%s",
            best_class_name,
            best_category,
            best_confidence,
            sensor_context,
        )

        return {
            "category": best_category,
            "confidence_score": round(
                best_confidence,
                4,
            ),
            "low_confidence": low_confidence,
            "raw_detections": detections,
            "sensor_override": (
                self._classify_from_sensors(
                    sensor_context
                )
                if sensor_context
                else None
            ),
        }

    # =============================================================
    # REAL SENSOR CLASSIFICATION
    # =============================================================

    @staticmethod
    def _classify_from_sensors(
        sensor_context: dict[str, Any] | None,
    ) -> str | None:

        if not sensor_context:
            return None

        try:
            proximity = int(
                sensor_context.get(
                    "proximity",
                    1000,
                )
            )

            rain = int(
                sensor_context.get(
                    "rain",
                    900,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        # ---------------------------------------------------------
        # METAL
        #
        # If the Arduino sends metal=True, trust it.
        # ---------------------------------------------------------

        if sensor_context.get("metal") is True:
            return "METAL"

        # ---------------------------------------------------------
        # WET / ORGANIC
        #
        # Rain sensor:
        # lower value = more moisture.
        # ---------------------------------------------------------

        if rain < 600:
            return "ORGANIC"

        # ---------------------------------------------------------
        # DRY MATERIAL
        #
        # Dry cardboard/paper/etc.
        # ---------------------------------------------------------

        if rain >= 600:
            return "BIODEGRADABLE"

        return None