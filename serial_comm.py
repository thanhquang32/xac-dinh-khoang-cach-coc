"""
serial_comm.py — Serial communication with ESP32.

Protocol (1 byte per command):
    0x01  →  ALERT ON  (distance < threshold)
    0x00  →  ALERT OFF (distance safe)
    0x50  →  PING / keep-alive
    0xFF  →  RESET
"""

import time
import threading

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("[SERIAL] pyserial not installed. Run: pip install pyserial")


CMD_ALERT_ON  = bytes([0x01])
CMD_ALERT_OFF = bytes([0x00])
CMD_PING      = bytes([0x50])
CMD_RESET     = bytes([0xFF])


class SerialComm:
    """
    Handles serial connection and messaging to ESP32.
    Runs a background keep-alive ping every 2 seconds.
    """

    def __init__(self, port: str | None = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self._ser = None
        self._lock = threading.Lock()
        self._ping_thread = None
        self._running = False

    # ---------------------------------------------------------------
    # Connection management
    # ---------------------------------------------------------------

    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            print("[SERIAL] pyserial unavailable — running without serial.")
            return False

        target_port = self.port or self._auto_detect_esp32()

        if target_port is None:
            print("[SERIAL] No ESP32 port found. Connect ESP32 via USB.")
            print("[SERIAL]   Available ports:")
            for p in serial.tools.list_ports.comports():
                print(f"           {p.device}  —  {p.description}")
            print("[SERIAL]   Start with --port COM3 (Windows) or --port /dev/ttyUSB0 (Linux/Mac)")
            return False

        try:
            self._ser = serial.Serial(
                port=target_port,
                baudrate=self.baudrate,
                timeout=1
            )
            time.sleep(2)  # Wait for ESP32 to reboot after DTR
            self._running = True
            self._start_ping()
            print(f"[SERIAL] Connected to ESP32 on {target_port} @ {self.baudrate} baud")
            return True
        except Exception as e:
            print(f"[SERIAL] Connection failed: {e}")
            return False

    def disconnect(self):
        self._running = False
        if self._ser and self._ser.is_open:
            self.send_raw(CMD_ALERT_OFF)
            self._ser.close()
            print("[SERIAL] Disconnected.")

    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    # ---------------------------------------------------------------
    # Commands
    # ---------------------------------------------------------------

    def send_alert(self, active: bool):
        """Send ALERT ON or ALERT OFF command."""
        cmd = CMD_ALERT_ON if active else CMD_ALERT_OFF
        self.send_raw(cmd)

    def send_raw(self, data: bytes):
        if not self.is_connected():
            return
        with self._lock:
            try:
                self._ser.write(data)
                self._ser.flush()
            except serial.SerialException as e:
                print(f"[SERIAL] Write error: {e}")
                self._ser = None  # Mark as disconnected

    # ---------------------------------------------------------------
    # Background keep-alive
    # ---------------------------------------------------------------

    def _start_ping(self):
        self._ping_thread = threading.Thread(
            target=self._ping_loop, daemon=True, name="SerialPing"
        )
        self._ping_thread.start()

    def _ping_loop(self):
        while self._running and self.is_connected():
            self.send_raw(CMD_PING)
            time.sleep(2.0)

    # ---------------------------------------------------------------
    # Auto-detect ESP32 port
    # ---------------------------------------------------------------

    @staticmethod
    def _auto_detect_esp32() -> str | None:
        if not SERIAL_AVAILABLE:
            return None
        known_ids = [
            "CP210",   # Silicon Labs CP2102 (common on ESP32 boards)
            "CH340",   # CH340 USB chip
            "FTDI",
            "ESP32",
            "USB Serial",
        ]
        for port in serial.tools.list_ports.comports():
            desc = (port.description or "").upper()
            if any(k.upper() in desc for k in known_ids):
                return port.device
        return None
