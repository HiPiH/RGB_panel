#pragma once

// Приём кадров по UDP.
//
// Класс держит сокет, вычитывает накопившиеся датаграммы и раскладывает
// пиксели прямо в буфер панели. Наружу отдаёт факт прихода кадра и счётчики.

#include <Arduino.h>
#include <FastLED.h>
#include <WiFiUdp.h>

#include "Config.h"
#include "FrameProtocol.h"
#include "PanelLayout.h"

class FrameReceiver {
 public:
  struct Stats {
    uint32_t packets = 0;   // принято датаграмм
    uint32_t applied = 0;   // кадров разложено в буфер панели
    uint32_t stale = 0;     // отброшено как устаревшие
    uint32_t invalid = 0;   // отброшено как битые
  };

  // Открывает сокет. Вызывать после подключения к сети.
  void begin(uint16_t port);

  // Закрывает сокет, например при потере связи.
  void end();

  bool isListening() const { return _listening; }

  // Вычитывает всё, что накопилось, и пишет пиксели в frame.
  // Возвращает true, если панель надо перерисовать.
  bool poll(uint32_t nowMs, CRGB* frame, uint16_t ledCount);

  // Поток считается живым, пока кадры приходят чаще таймаута.
  bool hasStream(uint32_t nowMs) const;

  const Stats& stats() const { return _stats; }

  // Сбрасывает счётчики, возвращая накопленное за период.
  Stats takeStats();

 private:
  // Разбирает одну датаграмму. true, если кадр разложен в буфер.
  bool handlePacket(int size, uint32_t nowMs, CRGB* frame, uint16_t ledCount);

  WiFiUDP _udp;
  bool _listening = false;
  bool _hasFrame = false;   // хотя бы один кадр уже принят
  uint16_t _lastSeq = 0;
  uint32_t _lastFrameMs = 0;
  Stats _stats;

  // Датаграмма целиком: заголовок плюс пиксели всей панели.
  uint8_t _packet[FrameProtocol::kHeaderSize +
                  LED_COUNT * FrameProtocol::kBytesPerPixel];
};
