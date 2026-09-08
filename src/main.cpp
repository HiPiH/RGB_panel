// RGB Panel - адресная светодиодная панель с удалённым управлением.
// Спринт 1: демонстрационный стенд, панель проходит цвета от чёрного к
//           белому через весь спектр.
// Спринт 2: подключение к Wi-Fi, параметры сети берутся из .env на сборке.

#include <Arduino.h>
#include <FastLED.h>

#include "Config.h"
#include "DemoSequence.h"
#include "WiFiLink.h"

namespace {

CRGB leds[LED_COUNT];
DemoSequence demo(DEMO_STEP_DELAY_MS);
WiFiLink wifi;

// Раз в секунду печатаем состояние стенда - удобно при отладке.
constexpr uint32_t kLogPeriodMs = 1000;
uint32_t lastLogMs = 0;

void showColor(const CRGB& color) {
  fill_solid(leds, LED_COUNT, color);
  FastLED.show();
}

void logStatus() {
  const CRGB c = demo.color();
  if (wifi.isConnected()) {
    Serial.printf("шаг %u/%u  RGB %3u %3u %3u  сеть: %s %s\n", demo.step(),
                  DemoSequence::totalSteps(), c.r, c.g, c.b, wifi.stateName(),
                  wifi.ip().toString().c_str());
  } else {
    Serial.printf("шаг %u/%u  RGB %3u %3u %3u  сеть: %s\n", demo.step(),
                  DemoSequence::totalSteps(), c.r, c.g, c.b, wifi.stateName());
  }
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
  showColor(demo.color());

  Serial.printf("RGB Panel: %d LED, шаг %u мс, цикл %u шагов\n", LED_COUNT,
                demo.stepDelayMs(), DemoSequence::totalSteps());

  wifi.begin(now);
}

void loop() {
  const uint32_t now = millis();

  wifi.update(now);

  if (demo.update(now)) {
    showColor(demo.color());
  }

  if (now - lastLogMs >= kLogPeriodMs) {
    lastLogMs = now;
    logStatus();
  }
}
