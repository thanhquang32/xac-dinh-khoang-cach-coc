"""
Cup Distance Tracker - Main Entry Point
Tracks 2 cups via webcam using YOLOv8, calculates real-world distance,
and sends serial warning to ESP32 when distance < 0.3m
"""

import cv2
import time
import argparse
from detector import CupDetector
from distance import DistanceCalculator
from serial_comm import SerialComm
from config import Config

def main():
    parser = argparse.ArgumentParser(description="Cup Distance Tracker")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--port", type=str, default=None, help="Serial port (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument("--calibrate", action="store_true", help="Run calibration mode")
    parser.add_argument("--show-fps", action="store_true", help="Show FPS on screen")
    args = parser.parse_args()

    config = Config()

    # Initialize components
    print("[INIT] Loading YOLOv8 model...")
    detector = CupDetector(
        model_path=config.MODEL_PATH,
        confidence=config.DETECTION_CONFIDENCE
    )

    print("[INIT] Setting up distance calculator...")
    distance_calc = DistanceCalculator(
        focal_length=config.FOCAL_LENGTH,
        real_cup_width_m=config.REAL_CUP_WIDTH_M
    )

    # Serial comm (optional - warning displayed if port not found)
    serial_port = args.port or config.SERIAL_PORT
    serial = SerialComm(port=serial_port, baudrate=config.BAUD_RATE)
    serial_connected = serial.connect()

    # Open webcam
    print(f"[INIT] Opening camera {args.camera}...")
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print("[ERROR] Cannot open camera!")
        return

    # Calibration mode
    if args.calibrate:
        print("\n[CALIBRATE] Hold a cup at exactly 0.5m from the camera.")
        print("            Press SPACE to capture, Q to quit.\n")
        run_calibration(cap, detector, distance_calc)
        cap.release()
        return

    print("\n[RUN] Tracking started. Press Q to quit.\n")

    alert_active = False
    alert_cooldown = 0
    fps_counter = 0
    fps_start = time.time()
    fps_display = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame")
            break

        # Detect cups
        cups = detector.detect(frame)

        distance_m = None
        warning = False

        if len(cups) >= 2:
            # Use the 2 highest-confidence detections
            top2 = sorted(cups, key=lambda x: x['confidence'], reverse=True)[:2]
            cup1, cup2 = top2[0], top2[1]

            # Estimate real-world distance
            distance_m = distance_calc.estimate_distance(cup1, cup2, frame.shape)

            warning = distance_m is not None and distance_m < config.ALERT_DISTANCE_M

            # Draw detections
            frame = draw_overlay(frame, cup1, cup2, distance_m, warning, config)

            # Handle serial alert
            if warning:
                if not alert_active or time.time() - alert_cooldown > config.ALERT_COOLDOWN_S:
                    if serial_connected:
                        serial.send_alert(True)
                    alert_active = True
                    alert_cooldown = time.time()
                    print(f"[ALERT] ⚠️  Distance = {distance_m:.3f}m — ALERT SENT to ESP32!")
            else:
                if alert_active:
                    if serial_connected:
                        serial.send_alert(False)
                    alert_active = False
                    print(f"[INFO] Distance = {distance_m:.3f}m — Clear, alert OFF.")

        elif len(cups) == 1:
            c = cups[0]
            cv2.rectangle(frame, (c['x1'], c['y1']), (c['x2'], c['y2']), (0, 200, 255), 2)
            cv2.putText(frame, "Waiting for 2nd cup...", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
        else:
            cv2.putText(frame, "No cups detected", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)

        # FPS counter
        fps_counter += 1
        if time.time() - fps_start >= 1.0:
            fps_display = fps_counter
            fps_counter = 0
            fps_start = time.time()

        if args.show_fps:
            cv2.putText(frame, f"FPS: {fps_display}", (frame.shape[1]-120, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        # Serial status indicator
        status_color = (0, 255, 0) if serial_connected else (0, 0, 180)
        status_text = f"Serial: {'OK' if serial_connected else 'DISCONNECTED'}"
        cv2.putText(frame, status_text, (20, frame.shape[0]-20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        cv2.imshow("Cup Distance Tracker", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            # Manual alert reset
            if serial_connected:
                serial.send_alert(False)
            alert_active = False

    # Cleanup
    if serial_connected:
        serial.send_alert(False)
        serial.disconnect()
    cap.release()
    cv2.destroyAllWindows()
    print("[EXIT] Program stopped.")


def draw_overlay(frame, cup1, cup2, distance_m, warning, config):
    """Draw bounding boxes, line, and distance label on frame."""
    h, w = frame.shape[:2]

    # Colors
    box_color = (0, 80, 255) if warning else (0, 220, 80)
    line_color = (0, 60, 255) if warning else (255, 200, 0)
    text_bg = (0, 0, 180) if warning else (20, 120, 20)

    for i, cup in enumerate([cup1, cup2], 1):
        x1, y1, x2, y2 = cup['x1'], cup['y1'], cup['x2'], cup['y2']
        cx, cy = cup['cx'], cup['cy']

        # Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

        # Label
        label = f"Cup {i} ({cup['confidence']:.0%})"
        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(frame, (x1, y1-lh-8), (x1+lw+4, y1), box_color, -1)
        cv2.putText(frame, label, (x1+2, y1-4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Center dot
        cv2.circle(frame, (cx, cy), 5, (255, 255, 255), -1)

    # Line between centers
    cx1, cy1 = cup1['cx'], cup1['cy']
    cx2, cy2 = cup2['cx'], cup2['cy']
    cv2.line(frame, (cx1, cy1), (cx2, cy2), line_color, 2)

    # Distance label at midpoint
    mid_x = (cx1 + cx2) // 2
    mid_y = (cy1 + cy2) // 2
    dist_text = f"{distance_m:.3f} m"
    (dw, dh), _ = cv2.getTextSize(dist_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    cv2.rectangle(frame, (mid_x - dw//2 - 6, mid_y - dh - 8),
                  (mid_x + dw//2 + 6, mid_y + 4), text_bg, -1)
    cv2.putText(frame, dist_text, (mid_x - dw//2, mid_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

    # Warning banner
    if warning:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 70), (0, 0, 200), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        cv2.putText(frame, "⚠  CANH BAO: KHOANG CACH QUA GAN!  ⚠",
                    (w//2 - 300, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.95,
                    (255, 255, 255), 2)

    return frame


def run_calibration(cap, detector, distance_calc):
    """Simple calibration: measure pixel width of cup at known distance."""
    known_distance = 0.5  # meters

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cups = detector.detect(frame)
        cv2.putText(frame, f"Place 1 cup at exactly {known_distance}m — SPACE to capture",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)

        for cup in cups:
            cv2.rectangle(frame, (cup['x1'], cup['y1']), (cup['x2'], cup['y2']), (0, 255, 0), 2)
            pixel_w = cup['x2'] - cup['x1']
            cv2.putText(frame, f"Pixel width: {pixel_w}px", (cup['x1'], cup['y1']-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Calibration", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(' ') and cups:
            cup = cups[0]
            pixel_w = cup['x2'] - cup['x1']
            real_w = distance_calc.real_cup_width_m
            focal = (pixel_w * known_distance) / real_w
            print(f"\n[CALIBRATE] Pixel width at {known_distance}m = {pixel_w}px")
            print(f"[CALIBRATE] Calculated FOCAL_LENGTH = {focal:.1f}")
            print(f"[CALIBRATE] Update config.py: FOCAL_LENGTH = {focal:.1f}\n")
            break
        elif key == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
