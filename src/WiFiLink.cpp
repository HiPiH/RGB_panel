#include "WiFiLink.h"

void WiFiLink::begin(uint32_t nowMs) {
  if (strlen(WIFI_SSID) == 0) {
    _state = State::Disabled;
    _stateSinceMs = nowMs;
    Serial.println("Wi-Fi: SSID не задан, работаем без сети (см. docs/WIFI.md)");
    return;
  }

  WiFi.persistent(false);  // не изнашиваем флеш записью учёток при каждом старте
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(WIFI_HOSTNAME);
  WiFi.setAutoReconnect(false);  // переподключением управляет этот класс
  startAttempt(nowMs);
}

void WiFiLink::startAttempt(uint32_t nowMs) {
  _attempts++;
  if (_attempts == 1) {
    _attemptStartedMs = nowMs;  // от него считаем время до выхода в сеть
  }
  _state = State::Connecting;
  _stateSinceMs = nowMs;
  // Без disconnect перед begin: выключение радиомодуля прямо перед попыткой
  // съедало первую ассоциацию, и стенд выходил в сеть только со второго раза.
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("Wi-Fi: попытка %u подключиться к сети\n", _attempts);
}

void WiFiLink::update(uint32_t nowMs) {
  switch (_state) {
    case State::Disabled:
      break;

    case State::Connecting:
      if (WiFi.status() == WL_CONNECTED) {
        _state = State::Connected;
        _stateSinceMs = nowMs;
        // Сон модема добавляет к задержке до 100 мс, для потока кадров это
        // много. Настройка ложится на уже поднятое соединение.
        WiFi.setSleep(false);
        Serial.printf("Wi-Fi: подключено за %lu мс, IP %s, RSSI %d дБм\n",
                      static_cast<unsigned long>(nowMs - _attemptStartedMs),
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
      } else if (nowMs - _stateSinceMs >= attemptTimeoutMs()) {
        _state = State::Waiting;
        _stateSinceMs = nowMs;
        Serial.printf("Wi-Fi: таймаут подключения, повтор через %d с\n",
                      WIFI_RETRY_DELAY_MS / 1000);
      }
      break;

    case State::Connected:
      if (WiFi.status() != WL_CONNECTED) {
        _state = State::Waiting;
        _stateSinceMs = nowMs;
        Serial.println("Wi-Fi: связь потеряна, переподключаемся");
      }
      break;

    case State::Waiting:
      if (nowMs - _stateSinceMs >= WIFI_RETRY_DELAY_MS) {
        startAttempt(nowMs);
      }
      break;
  }
}

const char* WiFiLink::stateName() const {
  switch (_state) {
    case State::Disabled:
      return "выключен";
    case State::Connecting:
      return "подключение";
    case State::Connected:
      return "подключено";
    case State::Waiting:
      return "ожидание";
  }
  return "?";
}

uint32_t WiFiLink::attemptTimeoutMs() const {
  return _attempts <= 1 ? WIFI_FIRST_ATTEMPT_TIMEOUT_MS : WIFI_CONNECT_TIMEOUT_MS;
}
