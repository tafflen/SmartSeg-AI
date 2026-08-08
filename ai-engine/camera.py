"""Trigger-based webcam access; frames are captured only after an IR event."""
from __future__ import annotations

import logging
from typing import Any

LOGGER = logging.getLogger(__name__)


class Camera:
    def __init__(self, device_index: int = 0, mock_mode: bool = False) -> None:
        self.device_index = device_index
        self.mock_mode = mock_mode
        self._capture: Any | None = None

    def capture_frame(self) -> Any:
        """Return one fresh BGR frame. The real camera is not read continuously."""
        if self.mock_mode:
            import numpy as np
            # A valid image-like frame lets the complete mock pipeline exercise its API.
            return np.full((480, 640, 3), 235, dtype=np.uint8)

        import cv2
        if self._capture is None:
            self._capture = cv2.VideoCapture(self.device_index)
            if not self._capture.isOpened():
                self._capture.release()
                self._capture = None
                raise RuntimeError(f"Cannot open webcam at index {self.device_index}")
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise RuntimeError("Webcam did not return a frame")
        LOGGER.debug("Captured one classification frame")
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
