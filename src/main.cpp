/**
 * ESP32 Cup Distance Alarm
 * Firmware for PlatformIO (VSCode extension)
 *
 * Serial Protocol (receive from PC Python):
 *   0x01  → ALERT ON  : activate buzzer + blink LED
 *   0x00  → ALERT OFF : deactivate all
 *   0x50  → PING      : keep-alive, blink LED once briefly
 *   0xFF  → RESET     : force all off
 *
 * Hardware:
 *   GPIO 26 → Relay module IN  (buzzer alarm via relay)
 *   GPIO 27 → Buzzer module signal pin (direct, 3.3V)
 *   GPIO 25 → LED đỏ (qua điện trở 220Ω xuống GND)
 */

#include <Arduino.h>

// ── Pin definitions ─────────────────────────────────────────────────
#define PIN_RELAY     26    // Relay IN (active LOW or HIGH — see RELAY_ACTIVE_LOW)
#define PIN_BUZZER    27    // Buzzer module signal pin
#define PIN_LED       25    // Red LED (through 220Ω resistor to GND)
#define PIN_LED_BUILTIN 2   // ESP32 onboard LED

// ── Relay polarity ──────────────────────────────────────────────────
// Most 5V relay modules are ACTIVE LOW (energize when IN = LOW)
// If your relay activates on HIGH, set to false
#define RELAY_ACTIVE_LOW  true

// ── Timing (milliseconds) ───────────────────────────────────────────
#define BLINK_ON_MS       150
#define BLINK_OFF_MS      150
#define BLINK_FAST_ON     80
#define BLINK_FAST_OFF    80
#define WATCHDOG_TIMEOUT  5000   // ms — if no serial for this long, turn off alarm

// ── State ────────────────────────────────────────────────────────────
bool alertActive = false;
unsigned long lastSerialMs = 0;
unsigned long lastBlinkMs  = 0;
bool ledState = false;
bool buzzerState = false;

// ── Helpers ──────────────────────────────────────────────────────────

void relayOn() {
  digitalWrite(PIN_RELAY, RELAY_ACTIVE_LOW ? LOW : HIGH);
}

void relayOff() {
  digitalWrite(PIN_RELAY, RELAY_ACTIVE_LOW ? HIGH : LOW);
}

void setAlarm(bool on) {
  alertActive = on;
  if (!on) {
    // Immediately silence everything
    digitalWrite(PIN_BUZZER, LOW);
    digitalWrite(PIN_LED, LOW);
    digitalWrite(PIN_LED_BUILTIN, LOW);
    relayOff();
    ledState = false;
    buzzerState = false;
  }
}

void pingBlink() {
  // Single quick blink to confirm comms
  digitalWrite(PIN_LED_BUILTIN, HIGH);
  delay(30);
  digitalWrite(PIN_LED_BUILTIN, LOW);
}

// ── Setup ─────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);

  pinMode(PIN_RELAY,      OUTPUT);
  pinMode(PIN_BUZZER,     OUTPUT);
  pinMode(PIN_LED,        OUTPUT);
  pinMode(PIN_LED_BUILTIN, OUTPUT);

  // Safe default: all off
  setAlarm(false);
  relayOff();

  Serial.println("[ESP32] Cup Distance Alarm ready.");
  Serial.println("[ESP32] Waiting for commands on Serial (115200 baud)...");

  // Startup blink to confirm boot
  for (int i = 0; i < 3; i++) {
    digitalWrite(PIN_LED_BUILTIN, HIGH);
    delay(100);
    digitalWrite(PIN_LED_BUILTIN, LOW);
    delay(100);
  }
}

// ── Main loop ─────────────────────────────────────────────────────────

void loop() {
  unsigned long now = millis();

  // ── Serial receive ──────────────────────────────────────────────
  if (Serial.available()) {
    uint8_t cmd = Serial.read();
    lastSerialMs = now;

    switch (cmd) {
      case 0x01:  // ALERT ON
        setAlarm(true);
        Serial.println("[ESP32] ALERT ON");
        break;

      case 0x00:  // ALERT OFF
        setAlarm(false);
        Serial.println("[ESP32] ALERT OFF");
        break;

      case 0x50:  // PING
        pingBlink();
        break;

      case 0xFF:  // RESET
        setAlarm(false);
        Serial.println("[ESP32] RESET");
        break;

      default:
        Serial.print("[ESP32] Unknown cmd: 0x");
        Serial.println(cmd, HEX);
        break;
    }
  }

  // ── Watchdog: auto-off if PC stops sending ──────────────────────
  if (alertActive && (now - lastSerialMs > WATCHDOG_TIMEOUT)) {
    Serial.println("[ESP32] Watchdog timeout — auto OFF");
    setAlarm(false);
  }

  // ── Alarm pattern: fast blink LED + buzzer pulses ───────────────
  if (alertActive) {
    unsigned long period = BLINK_ON_MS + BLINK_OFF_MS;
    bool phase = ((now % period) < BLINK_ON_MS);

    // LED blink
    if (phase != ledState) {
      ledState = phase;
      digitalWrite(PIN_LED, ledState ? HIGH : LOW);
      digitalWrite(PIN_LED_BUILTIN, ledState ? HIGH : LOW);
    }

    // Buzzer: beep pattern (on for 300ms, off for 200ms)
    unsigned long buzPeriod = 500;
    bool buzPhase = ((now % buzPeriod) < 300);
    if (buzPhase != buzzerState) {
      buzzerState = buzPhase;
      digitalWrite(PIN_BUZZER, buzzerState ? HIGH : LOW);
      // Relay mirrors buzzer (controls external louder buzzer/alarm)
      if (buzzerState) relayOn(); else relayOff();
    }
  }
}
