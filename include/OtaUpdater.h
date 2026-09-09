#pragma once

// Обновление прошивки по воздуху.
//
// Плата слушает заливку на порту 3232 и во время обновления показывает
// прогресс полосой на самой панели: без экрана иначе непонятно, идёт процесс
// или всё повисло. Без пароля в .env обновление не включается.

#include <Arduino.h>
#include <FastLED.h>

#include "Config.h"

class OtaUpdater {
 public:
  // Запускается после подключения к сети. leds нужны для полосы прогресса.
  void begin(CRGB* leds, uint16_t ledCount);

  // Вызывать в каждом проходе loop(). Пока обновления нет, стоит дёшево.
  void handle();

  bool isReady() const { return _ready; }

  // Пока идёт заливка, панелью распоряжается только этот класс.
  bool isUpdating() const { return _updating; }

 private:
  // Полоса на панели: сколько диодов зажечь и каким цветом.
  void paint(uint8_t percent, const CRGB& color);

  CRGB* _leds = nullptr;
  uint16_t _ledCount = 0;
  bool _ready = false;
  bool _updating = false;
  uint8_t _lastPercent = 255;
};
