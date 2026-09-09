#include "FrameReceiver.h"

void FrameReceiver::begin(uint16_t port) {
  if (_listening) {
    return;
  }
  if (_udp.begin(port) == 1) {
    _listening = true;
    Serial.printf("Кадры: слушаем UDP-порт %u\n", port);
  } else {
    Serial.printf("Кадры: не удалось открыть порт %u\n", port);
  }
}

void FrameReceiver::end() {
  if (!_listening) {
    return;
  }
  _udp.stop();
  _listening = false;
  _hasFrame = false;
  Serial.println("Кадры: сокет закрыт");
}

bool FrameReceiver::poll(uint32_t nowMs, CRGB* frame, uint16_t ledCount) {
  if (!_listening) {
    return false;
  }

  // Пауза в потоке сбрасывает фильтр номеров. Иначе перезапущенный
  // отправитель начинает нумерацию с нуля, его кадры выглядят устаревшими,
  // и панель замирает, пока счётчик не догонит прежнее значение.
  if (_hasFrame && (nowMs - _lastFrameMs) >= FRAME_STREAM_TIMEOUT_MS) {
    _hasFrame = false;
  }

  bool updated = false;
  // Предел на проход: всплеск трафика не должен задержать вывод на панель.
  for (uint8_t i = 0; i < MAX_PACKETS_PER_POLL; i++) {
    const int size = _udp.parsePacket();
    if (size <= 0) {
      break;
    }
    _stats.packets++;
    if (handlePacket(size, nowMs, frame, ledCount)) {
      updated = true;
    }
  }
  return updated;
}

bool FrameReceiver::handlePacket(int size, uint32_t nowMs, CRGB* frame,
                                 uint16_t ledCount) {
  if (static_cast<size_t>(size) > sizeof(_packet)) {
    // Читаем и выбрасываем, иначе остаток датаграммы сдвинет следующую.
    _udp.read(_packet, sizeof(_packet));
    _udp.clear();
    _stats.invalid++;
    return false;
  }

  const int read = _udp.read(_packet, size);
  if (read != size) {
    _stats.invalid++;
    return false;
  }

  FrameProtocol::Header header;
  const FrameProtocol::ParseResult result =
      FrameProtocol::parse(_packet, size, ledCount, header);
  if (result != FrameProtocol::ParseResult::Ok) {
    _stats.invalid++;
    return false;
  }

  // Кадр из прошлого приходит при переупорядочивании пакетов в сети. Такой
  // кадр показывать нельзя: картинка дёрнулась бы назад.
  if (_hasFrame && !FrameProtocol::isNewer(header.seq, _lastSeq) &&
      header.seq != _lastSeq) {
    _stats.stale++;
    return false;
  }

  const uint8_t* pixels = _packet + FrameProtocol::kHeaderSize;
  CRGB* target = frame + header.offset;
  for (uint16_t i = 0; i < header.count; i++) {
    target[i].setRGB(pixels[0], pixels[1], pixels[2]);
    pixels += FrameProtocol::kBytesPerPixel;
  }

  _hasFrame = true;
  _lastSeq = header.seq;
  _lastFrameMs = nowMs;
  _stats.applied++;
  return true;
}

bool FrameReceiver::hasStream(uint32_t nowMs) const {
  return _hasFrame && (nowMs - _lastFrameMs) < FRAME_STREAM_TIMEOUT_MS;
}

FrameReceiver::Stats FrameReceiver::takeStats() {
  const Stats snapshot = _stats;
  _stats = Stats();
  return snapshot;
}
