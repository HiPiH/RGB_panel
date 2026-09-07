#include "DemoSequence.h"

namespace {

// Длины участков маршрута в шагах. Каждый шаг - один кадр заливки.
constexpr uint16_t kStepsFadeIn = 256;   // чёрный -> красный
constexpr uint16_t kStepsHue = 256;      // весь цветовой круг
constexpr uint16_t kStepsToWhite = 256;  // красный -> белый
constexpr uint16_t kStepsHoldWhite = 64; // пауза на белом
constexpr uint16_t kStepsFadeOut = 256;  // белый -> чёрный, цикл замыкается

}  // namespace

DemoSequence::DemoSequence(uint16_t stepDelayMs) { setStepDelayMs(stepDelayMs); }

uint16_t DemoSequence::totalSteps() {
  return kStepsFadeIn + kStepsHue + kStepsToWhite + kStepsHoldWhite +
         kStepsFadeOut;
}

void DemoSequence::setStepDelayMs(uint16_t ms) {
  // Нулевая задержка означала бы бесконечный цикл догона в update().
  _stepDelayMs = (ms == 0) ? 1 : ms;
}

void DemoSequence::begin(uint32_t nowMs) {
  _step = 0;
  _lastStepMs = nowMs;
  _color = colorAt(_step);
}

bool DemoSequence::update(uint32_t nowMs) {
  bool changed = false;

  // Цикл, а не if: если loop() был надолго занят, догоняем расписание.
  while (nowMs - _lastStepMs >= _stepDelayMs) {
    _lastStepMs += _stepDelayMs;
    _step = (_step + 1) % totalSteps();
    changed = true;
  }

  if (changed) {
    _color = colorAt(_step);
  }
  return changed;
}

CHSV DemoSequence::colorAt(uint16_t step) {
  if (step < kStepsFadeIn) {
    // Насыщенный красный, разгорающийся из темноты.
    return CHSV(0, 255, static_cast<uint8_t>(step));
  }
  step -= kStepsFadeIn;

  if (step < kStepsHue) {
    // Полный оборот по цветовому кругу на максимальной яркости.
    return CHSV(static_cast<uint8_t>(step), 255, 255);
  }
  step -= kStepsHue;

  if (step < kStepsToWhite) {
    // Уводим насыщенность в ноль - цвет выцветает в белый.
    return CHSV(0, static_cast<uint8_t>(255 - step), 255);
  }
  step -= kStepsToWhite;

  if (step < kStepsHoldWhite) {
    return CHSV(0, 0, 255);
  }
  step -= kStepsHoldWhite;

  // Гаснем до чёрного, чтобы демо ушло на новый круг без рывка.
  return CHSV(0, 0, static_cast<uint8_t>(255 - step));
}
