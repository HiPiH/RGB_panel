#!/usr/bin/env python3
"""Тестовый отправитель кадров на панель. Формат в docs/PROTOCOL.md.

Гонит на плату пробную картинку с заданной частотой и печатает, сколько
кадров реально ушло. Потери считаются на стороне платы, они видны в её логе.

Примеры:
    python scripts/send_frames.py 192.168.1.42
    python scripts/send_frames.py 192.168.1.42 --fps 30 --seconds 60
    python scripts/send_frames.py 192.168.1.42 --pattern sweep
"""

import argparse
import colorsys
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


def pattern_rainbow(frame_index):
    """Радуга, плывущая по диагонали."""
    pixels = bytearray()
    shift = (frame_index * 2) % 256
    for y in range(HEIGHT):
        for x in range(WIDTH):
            hue = ((x + y) * 8 + shift) % 256 / 256.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            pixels += bytes((int(r * 255), int(g * 255), int(b * 255)))
    return bytes(pixels)


def pattern_sweep(frame_index):
    """Одна бегущая строка: видно разрывы и пропуски кадров."""
    pixels = bytearray(PIXELS * 3)
    row = (frame_index // 2) % HEIGHT
    for x in range(WIDTH):
        offset = (row * WIDTH + x) * 3
        pixels[offset:offset + 3] = b"\xff\xff\xff"
    return bytes(pixels)


def pattern_checker(frame_index):
    """Шахматка, меняющая фазу: заметно любое залипание картинки."""
    pixels = bytearray()
    phase = frame_index % 2
    for y in range(HEIGHT):
        for x in range(WIDTH):
            on = (x + y + phase) % 2 == 0
            pixels += b"\x40\x00\x60" if on else b"\x00\x40\x40"
    return bytes(pixels)


PATTERNS = {
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
    parser.add_argument("--pattern", choices=sorted(PATTERNS), default="rainbow")
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
            sock.sendto(build_datagram(seq, make_pixels(seq)),
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
