#pragma once

// Демонстрационная последовательность цветов для стенда.
//
// Панель целиком заливается одним цветом. Цвет идёт по маршруту
// чёрный -> красный -> весь спектр -> белый -> чёрный и повторяется.
// Класс не трогает железо и не блокирует loop(): он только считает,
// какой цвет должен гореть в данный момент времени.

#include <Arduino.h>
#include <FastLED.h>

#include "Config.h"

class DemoSequence {
 public:
  explicit DemoSequence(uint16_t stepDelayMs = DEMO_STEP_DELAY_MS);

  // Запуск последовательности с нулевого шага.
  void begin(uint32_t nowMs);

  // Вызывать в каждом проходе loop(). Возвращает true, если цвет сменился
  // и панель нужно перерисовать.
  bool update(uint32_t nowMs);

  // Текущий цвет заливки.
  CRGB color() const { return _color; }

  // Задержка между соседними цветами. Ноль трактуется как 1 мс.
  void setStepDelayMs(uint16_t ms);
  uint16_t stepDelayMs() const { return _stepDelayMs; }

  // Номер текущего шага и длина полного цикла - для логов и отладки.
  uint16_t step() const { return _step; }
  static uint16_t totalSteps();

 private:
  // Цвет, соответствующий шагу последовательности.
  static CHSV colorAt(uint16_t step);

  uint16_t _stepDelayMs;
  uint16_t _step = 0;
  uint32_t _lastStepMs = 0;
  CRGB _color = CRGB::Black;
};
