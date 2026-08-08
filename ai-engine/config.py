"""Runtime configuration for the SmartSeg AI engine.

All settings have safe offline defaults so the on-site demo works without cloud
accounts or physical hardware. Environment variables can override deployment values.
"""
from __future__ import annotations

import os
from pathlib import Path

AI_ENGINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AI_ENGINE_DIR.parent
DATABASE_PATH = Path(os.getenv("SMARTSEG_DATABASE_PATH", PROJECT_ROOT / "smartseg.db"))
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"

MOCK_MODE = os.getenv("SMARTSEG_MOCK_MODE", "true").lower() == "true"
SIMULATE_MODE = os.getenv("SMARTSEG_SIMULATE_MODE", "false").lower() == "true"
SIMULATE_INTERVAL_SECONDS = float(os.getenv("SMARTSEG_SIMULATE_INTERVAL", "5"))
SERIAL_PORT = os.getenv("SERIAL_PORT", os.getenv("SMARTSEG_SERIAL_PORT", "COM3"))
SERIAL_BAUD_RATE = int(os.getenv("SMARTSEG_SERIAL_BAUD", "115200"))
SERIAL_TIMEOUT_SECONDS = float(os.getenv("SMARTSEG_SERIAL_TIMEOUT", "1.0"))
SERVO_DONE_TIMEOUT_SECONDS = float(os.getenv("SMARTSEG_SERVO_TIMEOUT", "8.0"))
MOCK_IR_INTERVAL_SECONDS = float(os.getenv("SMARTSEG_MOCK_IR_INTERVAL", "8"))

NFC_SERIAL_PORT = os.getenv("NFC_SERIAL_PORT", os.getenv("SMARTSEG_NFC_SERIAL_PORT", "COM4"))
NFC_SERIAL_BAUD_RATE = int(os.getenv("SMARTSEG_NFC_SERIAL_BAUD", "115200"))
NFC_TAP_TIMEOUT_SECONDS = float(os.getenv("SMARTSEG_NFC_TAP_TIMEOUT", "8"))
NFC_BACKEND_TIMEOUT_SECONDS = float(os.getenv("SMARTSEG_NFC_BACKEND_TIMEOUT", "2"))
BACKEND_URL = os.getenv("SMARTSEG_BACKEND_URL", "http://localhost:8000")
NFC_API_TOKEN = os.getenv("SMARTSEG_NFC_API_TOKEN", "")
BACKEND_API_TOKEN = os.getenv("SMARTSEG_BACKEND_API_TOKEN", NFC_API_TOKEN)
BACKEND_TIMEOUT_SECONDS = float(os.getenv("SMARTSEG_BACKEND_TIMEOUT", "2"))
BACKEND_BRIDGE_INTERVAL_SECONDS = float(os.getenv("SMARTSEG_BACKEND_BRIDGE_INTERVAL", "2"))
BACKEND_BRIDGE_MAX_BACKOFF_SECONDS = int(os.getenv("SMARTSEG_BACKEND_BRIDGE_MAX_BACKOFF", "60"))
SERIAL_RECONNECT_SECONDS = float(os.getenv("SMARTSEG_SERIAL_RECONNECT", "5"))

MODEL_PATH = os.getenv("YOLO_MODEL_PATH", os.getenv("SMARTSEG_MODEL_PATH", "yolov8n.pt"))
CONFIDENCE_THRESHOLD = float(os.getenv("SMARTSEG_CONFIDENCE_THRESHOLD", "0.50"))
# COCO labels are intentionally mapped here rather than embedded in inference code.
YOLO_CATEGORY_MAPPING = {
    "bottle": "PLASTIC", "cup": "PLASTIC", "wine glass": "PLASTIC",
    "banana": "ORGANIC", "apple": "ORGANIC", "orange": "ORGANIC", "broccoli": "ORGANIC",
    "carrot": "ORGANIC", "sandwich": "ORGANIC", "pizza": "ORGANIC", "donut": "ORGANIC",
    "cake": "ORGANIC", "fork": "METAL", "knife": "METAL", "spoon": "METAL",
}

# A high raindrop reading indicates wet waste; override only borderline model results.
WET_RAIN_THRESHOLD = float(os.getenv("SMARTSEG_WET_RAIN_THRESHOLD", "0.70"))
BORDERLINE_CONFIDENCE = float(os.getenv("SMARTSEG_BORDERLINE_CONFIDENCE", "0.65"))

SYNC_ENABLED = os.getenv("SMARTSEG_SYNC_ENABLED", "false").lower() == "true"
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", os.getenv("SMARTSEG_FIREBASE_CREDENTIALS", ""))
SYNC_INTERVAL_SECONDS = int(os.getenv("SMARTSEG_SYNC_INTERVAL", "20"))
SYNC_MAX_BACKOFF_SECONDS = int(os.getenv("SMARTSEG_SYNC_MAX_BACKOFF", "3600"))

SMS_PROVIDER = os.getenv("SMARTSEG_SMS_PROVIDER", "mock").lower()
SMS_REWARD_THRESHOLD = int(os.getenv("SMARTSEG_SMS_REWARD_THRESHOLD", "100"))
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_PHONE = os.getenv("TWILIO_FROM_PHONE", "")
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "")
