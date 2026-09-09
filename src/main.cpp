// RGB Panel - адресная светодиодная панель с удалённым управлением.
// Спринт 1: демо-последовательность от чёрного к белому через весь спектр.
// Спринт 2: подключение к Wi-Fi, параметры сети берутся из .env на сборке.
// Спринт 3: приём кадров по UDP, переключение между демо и потоком.

#include <Arduino.h>
#include <FastLED.h>

#include "Config.h"
#include "DemoSequence.h"
#include "FrameReceiver.h"
#include "WiFiLink.h"

namespace {

// Режим панели. Пока кадров нет, играет демо.
enum class Mode : uint8_t { Demo, Live };

CRGB leds[LED_COUNT];
DemoSequence demo(DEMO_STEP_DELAY_MS);
WiFiLink wifi;
FrameReceiver receiver;

Mode mode = Mode::Demo;

// Кадр принят, но ещё не выведен: вывод ограничен сверху по частоте.
bool pendingShow = false;
uint32_t lastShowMs = 0;

// Раз в секунду печатаем состояние стенда.
constexpr uint32_t kLogPeriodMs = 1000;
uint32_t lastLogMs = 0;
uint32_t showsInPeriod = 0;

void show() {
  FastLED.show();
  showsInPeriod++;
}

void showColor(const CRGB& color) {
  fill_solid(leds, LED_COUNT, color);
  show();
}

// Сокет живёт только вместе со связью: без неё слушать нечего.
void followWiFiState() {
  if (wifi.isConnected() && !receiver.isListening()) {
    receiver.begin(FRAME_UDP_PORT);
  } else if (!wifi.isConnected() && receiver.isListening()) {
    receiver.end();
  }
}

void enterMode(Mode next, uint32_t nowMs) {
  if (mode == next) {
    return;
  }
  mode = next;
  if (mode == Mode::Demo) {
    demo.begin(nowMs);
    showColor(demo.color());
    Serial.println("Режим: демо, поток кадров пропал");
  } else {
    Serial.println("Режим: поток кадров");
  }
}

void logStatus(uint32_t nowMs) {
  const FrameReceiver::Stats stats = receiver.takeStats();
  const uint32_t fps = showsInPeriod;
  showsInPeriod = 0;

  if (mode == Mode::Live) {
    Serial.printf(
        "поток: %lu кадр/с  пакетов %lu  старых %lu  битых %lu  сеть: %s %s\n",
        static_cast<unsigned long>(fps),
        static_cast<unsigned long>(stats.packets),
        static_cast<unsigned long>(stats.stale),
        static_cast<unsigned long>(stats.invalid), wifi.stateName(),
        wifi.ip().toString().c_str());
    return;
  }

  const CRGB color = demo.color();
  if (wifi.isConnected()) {
    Serial.printf("демо: шаг %u/%u  RGB %3u %3u %3u  сеть: %s %s\n",
                  demo.step(), DemoSequence::totalSteps(), color.r, color.g,
                  color.b, wifi.stateName(), wifi.ip().toString().c_str());
  } else {
    Serial.printf("демо: шаг %u/%u  RGB %3u %3u %3u  сеть: %s\n", demo.step(),
                  DemoSequence::totalSteps(), color.r, color.g, color.b,
                  wifi.stateName());
  }
  (void)nowMs;
}

}  // namespace

void setup() {
  Serial.begin(115200);

  FastLED.addLeds<LED_CHIPSET, LED_DATA_PIN, LED_COLOR_ORDER>(leds, LED_COUNT)
      .setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(DEFAULT_BRIGHTNESS);
  FastLED.setMaxPowerInVoltsAndMilliamps(POWER_SUPPLY_VOLTS,
                                         POWER_SUPPLY_MILLIAMPS);

  const uint32_t now = millis();
  demo.begin(now);
  lastLogMs = now;
  lastShowMs = now;
  showColor(demo.color());

  Serial.printf("RGB Panel: %d LED, шаг демо %u мс, цикл %u шагов\n", LED_COUNT,
                demo.stepDelayMs(), DemoSequence::totalSteps());

  wifi.begin(now);
}

void loop() {
  const uint32_t now = millis();

  wifi.update(now);
  followWiFiState();

  // Приёмник пишет пиксели прямо в буфер панели, поэтому вычитывать его
  // нужно до того, как демо зальёт буфер своим цветом.
  if (receiver.poll(now, leds, LED_COUNT)) {
    pendingShow = true;
  }

  if (receiver.hasStream(now)) {
    enterMode(Mode::Live, now);
    // Верхний предел частоты: лента всё равно не обновится быстрее.
    if (pendingShow && (now - lastShowMs) >= MIN_FRAME_INTERVAL_MS) {
      show();
      lastShowMs = now;
      pendingShow = false;
    }
  } else {
    enterMode(Mode::Demo, now);
    pendingShow = false;
    if (demo.update(now)) {
      showColor(demo.color());
      lastShowMs = now;
    }
  }

  if (now - lastLogMs >= kLogPeriodMs) {
    lastLogMs = now;
    logStatus(now);
  }
}
