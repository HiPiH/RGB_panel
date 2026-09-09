#pragma once

// Подключение платы к Wi-Fi и удержание связи.
//
// Класс не блокирует loop(): подключение и переподключение разложены в
// автомат состояний, который продвигается вызовом update(). Демо-анимация
// при этом продолжает идти.

#include <Arduino.h>
#include <WiFi.h>

#include "Config.h"

class WiFiLink {
 public:
  enum class State : uint8_t {
    Disabled,    // SSID не задан, в сеть не идём
    Connecting,  // попытка подключения в процессе
    Connected,   // связь есть
    Waiting,     // пауза перед следующей попыткой
  };

  // Настраивает радиомодуль и запускает первую попытку подключения.
  void begin(uint32_t nowMs);

  // Вызывать в каждом проходе loop(): следит за таймаутом, обрывом связи
  // и повторными попытками.
  void update(uint32_t nowMs);

  bool isConnected() const { return _state == State::Connected; }
  State state() const { return _state; }
  IPAddress ip() const { return WiFi.localIP(); }

  // Число попыток подключения с момента старта - для логов.
  uint16_t attempts() const { return _attempts; }

  // Короткое название состояния для вывода в лог.
  const char* stateName() const;

 private:
  void startAttempt(uint32_t nowMs);

  // Таймаут текущей попытки: первая обрывается раньше остальных.
  uint32_t attemptTimeoutMs() const;

  State _state = State::Disabled;
  uint32_t _stateSinceMs = 0;
  uint32_t _attemptStartedMs = 0;  // момент первой попытки, для замера
  uint16_t _attempts = 0;
};
