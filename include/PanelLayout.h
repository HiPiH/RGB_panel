#pragma once

// Раскладка панели: из координат пикселя в номер диода в ленте.
//
// Кадр по сети приходит построчно слева направо и сверху вниз, а лента на
// панели уложена змейкой: каждая вторая строка идёт в обратную сторону.
// Без этого преобразования нечётные строки картинки оказываются зеркальными,
// и на любом несимметричном изображении видно, как строки разъезжаются
// в противоположные стороны.

#include <Arduino.h>

#include "Config.h"

namespace PanelLayout {

// Номер диода для пикселя (x, y). Начало координат - левый верхний угол.
inline uint16_t index(uint16_t x, uint16_t y) {
  uint16_t column = PANEL_FLIP_X ? (PANEL_WIDTH - 1 - x) : x;
  uint16_t row = PANEL_FLIP_Y ? (PANEL_HEIGHT - 1 - y) : y;

  if (PANEL_SERPENTINE && (row & 1)) {
    column = PANEL_WIDTH - 1 - column;
  }
  return row * PANEL_WIDTH + column;
}

// Номер диода для позиции пикселя в кадре, считая построчно.
inline uint16_t indexForPosition(uint16_t position) {
  return index(position % PANEL_WIDTH, position / PANEL_WIDTH);
}

}  // namespace PanelLayout
