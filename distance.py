"""
distance.py — Estimate real-world distance between 2 cups using single camera.

Method: Pinhole camera model
  - Estimate depth Z of each cup: Z = (focal_length * real_width) / pixel_width
  - Convert pixel (x, y) to real-world (X, Y) coordinates
  - Compute 3D Euclidean distance

Run main.py --calibrate to find your FOCAL_LENGTH for your camera.
"""

import math
import numpy as np


class DistanceCalculator:
    """
    Estimates the real-world distance between two detected cups.

    Parameters
    ----------
    focal_length : float
        Camera focal length in pixels. Obtain via calibration mode.
        Typical webcam at 1280x720: ~700-1000 px
    real_cup_width_m : float
        Real physical width (diameter) of the cup in metres. (default 0.08 = 8 cm)
    smoothing_alpha : float
        Exponential smoothing factor (0-1). Lower = smoother but more lag.
    """

    def __init__(self,
                 focal_length: float = 800.0,
                 real_cup_width_m: float = 0.08,
                 smoothing_alpha: float = 0.4):
        self.focal_length = focal_length
        self.real_cup_width_m = real_cup_width_m
        self.alpha = smoothing_alpha
        self._smoothed_distance = None

    def _depth_from_width(self, pixel_width: int) -> float:
        """Estimate depth Z (metres) using apparent width."""
        if pixel_width <= 0:
            return 0.0
        return (self.focal_length * self.real_cup_width_m) / pixel_width

    def estimate_distance(self, cup1: dict, cup2: dict, frame_shape: tuple) -> float | None:
        """
        Estimate the 3D distance between two cups.

        Returns distance in metres, or None if estimation fails.
        """
        try:
            h, w = frame_shape[:2]
            cx = w / 2.0
            cy = h / 2.0
            f = self.focal_length

            # Depth estimation for each cup
            z1 = self._depth_from_width(cup1['width_px'])
            z2 = self._depth_from_width(cup2['width_px'])

            if z1 <= 0 or z2 <= 0:
                return None

            # Convert pixel centers to real-world X, Y (metres)
            # X_real = (x_pixel - cx) * Z / focal_length
            x1_r = (cup1['cx'] - cx) * z1 / f
            y1_r = (cup1['cy'] - cy) * z1 / f
            x2_r = (cup2['cx'] - cx) * z2 / f
            y2_r = (cup2['cy'] - cy) * z2 / f

            # 3D Euclidean distance
            distance = math.sqrt(
                (x2_r - x1_r)**2 +
                (y2_r - y1_r)**2 +
                (z2 - z1)**2
            )

            # Exponential smoothing to reduce jitter
            if self._smoothed_distance is None:
                self._smoothed_distance = distance
            else:
                self._smoothed_distance = (
                    self.alpha * distance +
                    (1 - self.alpha) * self._smoothed_distance
                )

            return round(self._smoothed_distance, 4)

        except Exception as e:
            print(f"[DISTANCE] Error: {e}")
            return None

    def reset_smoothing(self):
        self._smoothed_distance = None
