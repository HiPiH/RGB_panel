// RGB Panel - адресная светодиодная панель с удалённым управлением.
// Спринт 1: демонстрационный стенд, панель непрерывно проходит цвета
// от чёрного к белому через весь спектр.

#include <Arduino.h>
#include <FastLED.h>

#include "Config.h"
#include "DemoSequence.h"

namespace {

CRGB leds[LED_COUNT];
DemoSequence demo(DEMO_STEP_DELAY_MS);

// Раз в секунду печатаем, где находится демо - удобно при отладке стенда.
constexpr uint32_t kLogPeriodMs = 1000;
uint32_t lastLogMs = 0;

void showColor(const CRGB& color) {
  fill_solid(leds, LED_COUNT, color);
  FastLED.show();
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
}

void loop() {
  const uint32_t now = millis();

  if (demo.update(now)) {
    showColor(demo.color());
  }

  if (now - lastLogMs >= kLogPeriodMs) {
    lastLogMs = now;
    const CRGB c = demo.color();
    Serial.printf("шаг %u/%u  RGB %3u %3u %3u\n", demo.step(),
                  DemoSequence::totalSteps(), c.r, c.g, c.b);
  }
}
