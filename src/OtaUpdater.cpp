#include "OtaUpdater.h"

#include <ArduinoOTA.h>

void OtaUpdater::begin(CRGB* leds, uint16_t ledCount) {
  if (_ready) {
    return;
  }
  if (strlen(OTA_PASSWORD) == 0) {
    Serial.println(
        "OTA: пароль не задан, обновление по воздуху выключено (см. docs/OTA.md)");
    return;
  }

  _leds = leds;
  _ledCount = ledCount;

  ArduinoOTA.setHostname(OTA_HOSTNAME);
  ArduinoOTA.setPassword(OTA_PASSWORD);

  ArduinoOTA.onStart([this]() {
    _updating = true;
    _lastPercent = 255;
    Serial.println("OTA: началось обновление");
    paint(0, CRGB::Black);
  });

  ArduinoOTA.onProgress([this](unsigned int done, unsigned int total) {
    if (total == 0) {
      return;
    }
    const uint8_t percent = static_cast<uint8_t>(done * 100ULL / total);
    // Перерисовываем только на смене процента: вывод на ленту стоит 7.7 мс,
    // на каждом пакете заливки это заметно тормозило бы обновление.
    if (percent == _lastPercent) {
      return;
    }
    _lastPercent = percent;
    paint(percent, CRGB(0, 40, 120));
    Serial.printf("OTA: %u %%\n", percent);
  });

  ArduinoOTA.onEnd([this]() {
    Serial.println("OTA: готово, перезагрузка");
    paint(100, CRGB(0, 120, 0));
  });

  ArduinoOTA.onError([this](ota_error_t error) {
    _updating = false;
    const char* reason = "неизвестная ошибка";
    switch (error) {
      case OTA_AUTH_ERROR:
        reason = "не подошёл пароль";
        break;
      case OTA_BEGIN_ERROR:
        reason = "не удалось начать запись";
        break;
      case OTA_CONNECT_ERROR:
        reason = "оборвалось соединение";
        break;
      case OTA_RECEIVE_ERROR:
        reason = "ошибка приёма данных";
        break;
      case OTA_END_ERROR:
        reason = "не удалось завершить запись";
        break;
    }
    Serial.printf("OTA: сбой, %s\n", reason);
    paint(100, CRGB(120, 0, 0));
  });

  ArduinoOTA.begin();
  _ready = true;
  Serial.printf("OTA: ждём обновление, имя %s, порт 3232\n", OTA_HOSTNAME);
}

void OtaUpdater::handle() {
  if (_ready) {
    ArduinoOTA.handle();
  }
}

void OtaUpdater::paint(uint8_t percent, const CRGB& color) {
  if (_leds == nullptr) {
    return;
  }
  const uint16_t lit = static_cast<uint32_t>(_ledCount) * percent / 100;
  for (uint16_t i = 0; i < _ledCount; i++) {
    _leds[i] = (i < lit) ? color : CRGB::Black;
  }
  FastLED.show();
}
