"""
detector.py — YOLOv8-based cup detection
COCO class 41 = 'cup'
"""

import cv2
import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[WARN] ultralytics not installed. Using fallback color-based detector.")
    print("       Install with: pip install ultralytics")


class CupDetector:
    """
    Detects cups in a frame using YOLOv8.
    Falls back to HSV color segmentation if ultralytics is not installed.
    """

    COCO_CUP_CLASS = 41  # 'cup' in COCO dataset

    def __init__(self, model_path: str = "yolov8n.pt", confidence: float = 0.45):
        self.confidence = confidence
        self.model = None

        if YOLO_AVAILABLE:
            print(f"[DETECTOR] Loading YOLO model: {model_path}")
            try:
                self.model = YOLO(model_path)
                print("[DETECTOR] YOLO model loaded successfully.")
            except Exception as e:
                print(f"[DETECTOR] Failed to load model: {e}")
                self.model = None
        else:
            print("[DETECTOR] Running in fallback (color) mode.")

    def detect(self, frame: np.ndarray) -> list[dict]:
        """
        Detect cups in frame.
        Returns list of dicts: {x1, y1, x2, y2, cx, cy, confidence, width_px, height_px}
        """
        if self.model is not None:
            return self._detect_yolo(frame)
        else:
            return self._detect_color(frame)

    def _detect_yolo(self, frame: np.ndarray) -> list[dict]:
        """YOLOv8 detection."""
        results = self.model(frame, verbose=False, conf=self.confidence,
                              classes=[self.COCO_CUP_CLASS])
        cups = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                cups.append({
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                    'cx': cx, 'cy': cy,
                    'confidence': conf,
                    'width_px': x2 - x1,
                    'height_px': y2 - y1
                })
        return cups

    def _detect_color(self, frame: np.ndarray) -> list[dict]:
        """
        Fallback: detect cup-like objects by color (white/light colored mugs).
        Works best when cups have distinct colors against the background.
        Tune HSV ranges for your specific cups.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # White/light mask (catches white or light-colored cups)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cups = []
        h, w = frame.shape[:2]
        min_area = (w * h) * 0.005  # at least 0.5% of frame

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            # Cups are roughly 0.4–2.0 aspect ratio
            if not (0.3 < aspect < 2.5):
                continue
            cx = x + bw // 2
            cy = y + bh // 2
            cups.append({
                'x1': x, 'y1': y, 'x2': x + bw, 'y2': y + bh,
                'cx': cx, 'cy': cy,
                'confidence': min(area / (w * h * 0.02), 1.0),
                'width_px': bw,
                'height_px': bh
            })

        # Return top 2 by area
        cups.sort(key=lambda c: (c['x2']-c['x1'])*(c['y2']-c['y1']), reverse=True)
        return cups[:2]
# hêllo