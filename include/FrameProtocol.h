#pragma once

// Разбор датаграммы с кадром. Формат описан в docs/PROTOCOL.md.
//
// Здесь только чистые функции: ни сокетов, ни состояния. Так разбор можно
// проверить отдельно от железа.

#include <Arduino.h>

namespace FrameProtocol {

constexpr uint8_t kMagic0 = 'R';
constexpr uint8_t kMagic1 = 'P';
constexpr uint8_t kVersion = 1;
constexpr size_t kHeaderSize = 10;
constexpr size_t kBytesPerPixel = 3;

// Бит 0 флагов: пакет закрывает кадр. Пока кадр всегда в одной датаграмме,
// но поле уже учитывается отправителем.
constexpr uint8_t kFlagLastPacket = 0x01;

struct Header {
  uint8_t version;
  uint8_t flags;
  uint16_t seq;     // номер кадра, переполняется по кругу
  uint16_t offset;  // индекс первого пикселя в кадре
  uint16_t count;   // число пикселей в этой датаграмме
};

enum class ParseResult : uint8_t {
  Ok,
  TooShort,      // не хватает даже на заголовок
  BadMagic,      // чужой пакет на нашем порту
  BadVersion,    // отправитель новее прошивки
  BadCount,      // нулевое число пикселей
  SizeMismatch,  // длина датаграммы не сходится с count
  OutOfRange,    // кадр не помещается в панель
};

// Читает big-endian слово из буфера.
inline uint16_t readUint16(const uint8_t* data) {
  return static_cast<uint16_t>((data[0] << 8) | data[1]);
}

// Разбирает заголовок и проверяет, что данные бьются с размером панели.
inline ParseResult parse(const uint8_t* data, size_t size, size_t ledCount,
                         Header& out) {
  if (size < kHeaderSize) {
    return ParseResult::TooShort;
  }
  if (data[0] != kMagic0 || data[1] != kMagic1) {
    return ParseResult::BadMagic;
  }
  if (data[2] != kVersion) {
    return ParseResult::BadVersion;
  }

  out.version = data[2];
  out.flags = data[3];
  out.seq = readUint16(data + 4);
  out.offset = readUint16(data + 6);
  out.count = readUint16(data + 8);

  if (out.count == 0) {
    return ParseResult::BadCount;
  }
  if (size != kHeaderSize + static_cast<size_t>(out.count) * kBytesPerPixel) {
    return ParseResult::SizeMismatch;
  }
  if (static_cast<size_t>(out.offset) + out.count > ledCount) {
    return ParseResult::OutOfRange;
  }
  return ParseResult::Ok;
}

// Кольцевое сравнение номеров: true, если кадр a новее кадра b. Разность в
// знаковом виде переживает переполнение счётчика, простое a > b - нет.
inline bool isNewer(uint16_t a, uint16_t b) {
  return static_cast<int16_t>(a - b) > 0;
}

inline const char* resultName(ParseResult result) {
  switch (result) {
    case ParseResult::Ok:
      return "ok";
    case ParseResult::TooShort:
      return "короткий пакет";
    case ParseResult::BadMagic:
      return "чужой пакет";
    case ParseResult::BadVersion:
      return "другая версия";
    case ParseResult::BadCount:
      return "нулевой count";
    case ParseResult::SizeMismatch:
      return "длина не сходится";
    case ParseResult::OutOfRange:
      return "выход за панель";
  }
  return "?";
}

}  // namespace FrameProtocol
