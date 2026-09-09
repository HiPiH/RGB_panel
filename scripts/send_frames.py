#!/usr/bin/env python3
"""Тестовый отправитель кадров на панель. Формат в docs/PROTOCOL.md.

Гонит на плату пробную картинку с заданной частотой и печатает, сколько
кадров реально ушло. Потери считаются на стороне платы, они видны в её логе.

Примеры:
    python scripts/send_frames.py 192.168.1.42
    python scripts/send_frames.py 192.168.1.42 --seconds 0
    python scripts/send_frames.py 192.168.1.42 --fps 30 --pattern sweep
"""

import argparse
import colorsys
import math
import socket
import struct
import time

MAGIC = b"RP"
VERSION = 1
FLAG_LAST_PACKET = 0x01
HEADER = struct.Struct(">2sBBHHH")

WIDTH = 16
HEIGHT = 16
PIXELS = WIDTH * HEIGHT

BLACK = (0, 0, 0)

# Смайлик: длительность одного круга анимации и его цвета.
SMILEY_LOOP_SECONDS = 10.0
SMILEY_FACE = (255, 190, 20)
SMILEY_DARK = (12, 6, 0)


def pattern_smiley(frame_index, elapsed):
    """Улыбающийся смайлик во всю панель, цикл 10 секунд.

    За круг лицо дважды моргает, один раз подмигивает правым глазом, улыбка
    успевает разойтись до широкой и вернуться, а само лицо слегка покачивается.
    Всё считается от времени, а не от номера кадра, поэтому на любой частоте
    анимация идёт одинаково.
    """
    phase = (elapsed % SMILEY_LOOP_SECONDS) / SMILEY_LOOP_SECONDS
    wave = 2 * math.pi * phase

    bob = round(math.sin(wave) * 0.6)              # покачивание, ±1 пиксель
    depth = 1.2 + 1.8 * (0.5 - 0.5 * math.cos(wave))  # насколько широкая улыбка
    glow = 0.82 + 0.18 * math.sin(2 * wave)        # лицо «дышит» яркостью
    blink = 0.30 <= phase < 0.34 or 0.62 <= phase < 0.66
    wink = 0.82 <= phase < 0.90

    face = tuple(min(255, int(channel * glow)) for channel in SMILEY_FACE)
    pixels = [BLACK] * PIXELS

    center = (WIDTH - 1) / 2.0
    radius = 7.4
    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx = x - center
            dy = y - center - bob
            if dx * dx + dy * dy <= radius * radius:
                pixels[y * WIDTH + x] = face

    def put_dark(x, y):
        y += bob
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            pixels[y * WIDTH + x] = SMILEY_DARK

    # Глаза: два столбика по два пикселя. Закрытый глаз - нижняя строка.
    for x in (4, 5):
        put_dark(x, 6)
        if not blink:
            put_dark(x, 5)
    for x in (10, 11):
        put_dark(x, 6)
        if not blink and not wink:
            put_dark(x, 5)

    # Улыбка: парабола, концы которой задраны тем выше, чем шире улыбка.
    for x in range(3, 13):
        norm = (x - center) / 4.5
        y = round(11.0 - depth * norm * norm)
        put_dark(x, y)
        # На широкой улыбке рот становится в два пикселя - виден «оскал».
        if depth > 2.2 and abs(norm) < 0.5:
            put_dark(x, y - 1)

    return b"".join(bytes(color) for color in pixels)


def pattern_rainbow(frame_index, elapsed):
    """Радуга, плывущая по диагонали."""
    pixels = bytearray()
    shift = (frame_index * 2) % 256
    for y in range(HEIGHT):
        for x in range(WIDTH):
            hue = ((x + y) * 8 + shift) % 256 / 256.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            pixels += bytes((int(r * 255), int(g * 255), int(b * 255)))
    return bytes(pixels)


def pattern_sweep(frame_index, elapsed):
    """Одна бегущая строка: видно разрывы и пропуски кадров."""
    pixels = bytearray(PIXELS * 3)
    row = (frame_index // 2) % HEIGHT
    for x in range(WIDTH):
        offset = (row * WIDTH + x) * 3
        pixels[offset:offset + 3] = b"\xff\xff\xff"
    return bytes(pixels)


def pattern_checker(frame_index, elapsed):
    """Шахматка, меняющая фазу: заметно любое залипание картинки."""
    pixels = bytearray()
    phase = frame_index % 2
    for y in range(HEIGHT):
        for x in range(WIDTH):
            on = (x + y + phase) % 2 == 0
            pixels += b"\x40\x00\x60" if on else b"\x00\x40\x40"
    return bytes(pixels)


PATTERNS = {
    "smiley": pattern_smiley,
    "rainbow": pattern_rainbow,
    "sweep": pattern_sweep,
    "checker": pattern_checker,
}


def build_datagram(seq, pixels):
    header = HEADER.pack(MAGIC, VERSION, FLAG_LAST_PACKET, seq & 0xFFFF, 0,
                         PIXELS)
    return header + pixels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="IP платы, его видно в её логе")
    parser.add_argument("--port", type=int, default=4210)
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--seconds", type=float, default=10.0,
                        help="0 - гнать бесконечно")
    parser.add_argument("--pattern", choices=sorted(PATTERNS), default="smiley")
    args = parser.parse_args()

    make_pixels = PATTERNS[args.pattern]
    period = 1.0 / args.fps
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"{args.host}:{args.port}, {args.fps:g} кадр/с, картинка "
          f"{args.pattern}, датаграмма {HEADER.size + PIXELS * 3} байт")

    seq = 0
    sent = 0
    started = time.monotonic()
    next_send = started
    try:
        while args.seconds == 0 or time.monotonic() - started < args.seconds:
            elapsed = time.monotonic() - started
            sock.sendto(build_datagram(seq, make_pixels(seq, elapsed)),
                        (args.host, args.port))
            seq = (seq + 1) & 0xFFFF
            sent += 1

            # Расписание считаем от старта, иначе ошибка копится с каждым кадром.
            next_send += period
            delay = next_send - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_send = time.monotonic()
    except KeyboardInterrupt:
        print()

    elapsed = time.monotonic() - started
    print(f"отправлено {sent} кадров за {elapsed:.1f} с, "
          f"фактически {sent / elapsed:.1f} кадр/с")
    print("потери смотрите в логе платы: pio device monitor")


if __name__ == "__main__":
    main()
