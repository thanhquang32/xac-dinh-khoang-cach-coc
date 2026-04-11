# Cup Distance Tracker & ESP32 Alarm System

Dự án theo dõi 2 cái cốc qua webcam bằng YOLOv8, tính khoảng cách thực tế, và gửi cảnh báo Serial tới ESP32 khi khoảng cách < 0.3m.

---

## Cấu trúc dự án

```
cup_tracker/
├── python/
│   ├── main.py          # Entry point, vòng lặp chính
│   ├── detector.py      # YOLOv8 cup detection
│   ├── distance.py      # Tính khoảng cách thực tế (pinhole model)
│   ├── serial_comm.py   # Giao tiếp Serial với ESP32
│   ├── config.py        # Cấu hình tập trung
│   └── requirements.txt
└── esp32/
    ├── platformio.ini   # PlatformIO config
    └── src/
        └── main.cpp     # ESP32 firmware (Arduino)
```

---

## Cài đặt Python

```bash
cd cup_tracker/python
pip install -r requirements.txt
```

> Lần đầu chạy, YOLOv8 sẽ tự tải model `yolov8n.pt` (~6MB).

---

## Hiệu chỉnh camera (quan trọng!)

Kết quả khoảng cách phụ thuộc vào `FOCAL_LENGTH` của webcam của bạn.
Chạy chế độ calibration để tính giá trị này:

```bash
python main.py --calibrate
```

1. Đặt 1 cái cốc cách camera đúng **0.5m**
2. Nhấn **SPACE** khi cốc được detect
3. Copy giá trị `FOCAL_LENGTH` được in ra vào `config.py`

---

## Chạy chương trình

```bash
# Tự động detect cổng ESP32
python main.py

# Chỉ định cổng COM (Windows)
python main.py --port COM3

# Chỉ định cổng (Linux/Mac)
python main.py --port /dev/ttyUSB0

# Hiển thị FPS
python main.py --show-fps
```

### Phím tắt
| Phím | Chức năng |
|------|-----------|
| `Q`  | Thoát |
| `R`  | Reset cảnh báo thủ công |

---

## ESP32 Firmware (PlatformIO)

### Yêu cầu
- VSCode + Extension **PlatformIO IDE**

### Nạp firmware
1. Mở thư mục `esp32/` bằng VSCode
2. PlatformIO sẽ tự nhận dạng `platformio.ini`
3. Nhấn nút **Upload** (→) hoặc `Ctrl+Alt+U`
4. Mở Serial Monitor: `Ctrl+Alt+S` (115200 baud)

---

## Kết nối phần cứng

| ESP32 Pin | Kết nối tới             | Mô tả                          |
|-----------|-------------------------|-------------------------------|
| GPIO 25   | 220Ω → Anode LED đỏ    | LED nhấp nháy khi cảnh báo    |
| GPIO 26   | Relay Module → IN       | Relay kích còi 5V lớn hơn     |
| GPIO 27   | Buzzer Module → Signal  | Còi chip beep trực tiếp       |
| 3V3       | Buzzer Module → VCC     | Nguồn cho buzzer module       |
| 5V (VIN)  | Relay Module → VCC      | Nguồn cho relay module        |
| GND       | GND tất cả linh kiện    | Chung GND                     |

### Lưu ý Relay
- Hầu hết module relay 5V là **ACTIVE LOW** (kích khi IN = LOW)
- Nếu relay của bạn kích ở HIGH, đổi `#define RELAY_ACTIVE_LOW false` trong `main.cpp`
- Dây NO (Normally Open) và COM nối vào còi 5V ngoài hoặc nguồn DC khác

---

## Giao thức Serial

| Byte | Lệnh        |
|------|-------------|
| 0x01 | ALERT ON    |
| 0x00 | ALERT OFF   |
| 0x50 | PING (keep-alive mỗi 2s) |
| 0xFF | RESET       |

ESP32 có **watchdog 5 giây**: nếu không nhận được tín hiệu nào trong 5s, tự tắt cảnh báo.

---

## Cấu hình `config.py`

```python
FOCAL_LENGTH     = 800.0   # Đo được từ --calibrate
REAL_CUP_WIDTH_M = 0.08    # Đường kính thực tế của cốc (mét)
ALERT_DISTANCE_M = 0.30    # Ngưỡng cảnh báo (mét)
SERIAL_PORT      = None    # None = tự detect, hoặc "COM3", "/dev/ttyUSB0"
```

---

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| Không detect cốc | Thử model lớn hơn: `MODEL_PATH = "yolov8s.pt"` |
| Khoảng cách sai nhiều | Chạy `--calibrate` lại, đo đúng đường kính cốc |
| Không tìm thấy cổng Serial | Kiểm tra driver CH340/CP2102, thử chỉ định `--port` |
| Relay không kích | Kiểm tra `RELAY_ACTIVE_LOW`, đảm bảo cấp đủ 5V cho relay |
| FPS thấp | Dùng `yolov8n.pt` (nhỏ nhất), giảm `CAP_PROP_FRAME_WIDTH` |
