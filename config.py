"""
config.py — All tunable parameters in one place.
"""


class Config:
    # ── YOLO ──────────────────────────────────────────────────────────
    MODEL_PATH = "yolov8n.pt"        # yolov8n / yolov8s / yolov8m
    DETECTION_CONFIDENCE = 0.45      # Minimum confidence for detection

    # ── Distance ──────────────────────────────────────────────────────
    # Run `python main.py --calibrate` to measure FOCAL_LENGTH for your webcam.
    FOCAL_LENGTH = 800.0             # pixels (update after calibration!)
    REAL_CUP_WIDTH_M = 0.08          # 8 cm — measure your actual cup diameter

    ALERT_DISTANCE_M = 0.30          # metres — alert threshold

    # ── Serial ────────────────────────────────────────────────────────
    SERIAL_PORT = None               # None = auto-detect ESP32
    # SERIAL_PORT = "COM3"           # Windows
    # SERIAL_PORT = "/dev/ttyUSB0"   # Linux
    # SERIAL_PORT = "/dev/cu.usbserial-0001"  # macOS
    BAUD_RATE = 115200

    # ── Alert behaviour ───────────────────────────────────────────────
    ALERT_COOLDOWN_S = 1.0           # Minimum seconds between serial sends
