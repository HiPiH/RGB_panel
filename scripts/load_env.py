"""Готовит параметры Wi-Fi для прошивки: .env -> include/WiFiCredentials.h.

Файл .env лежит рядом с проектом и в git не попадает, сгенерированный
заголовок тоже. В исходниках паролей нет, значения нигде не печатаются.

Почему генерируется заголовок, а не -D флаги: значения проходят через
командную строку компилятора и подстановку SCons, где пробел в имени сети
рвёт аргумент, а $ в пароле съедается как имя переменной. В заголовке
достаточно экранирования по правилам C.

Если .env отсутствует или SSID пуст, сборка не падает: строки становятся
пустыми, а прошивка сообщает об этом в лог и работает без сети.
"""

from pathlib import Path

Import("env")  # noqa: F821  - подставляется PlatformIO

KEYS = ("WIFI_SSID", "WIFI_PASSWORD")

HEADER = """// Сгенерировано scripts/load_env.py из .env при сборке.
// Файл не редактируется руками и не попадает в git.
#pragma once

#define {ssid_key} {ssid}
#define {password_key} {password}
"""


def parse_env_file(path):
    """Разбирает .env: строки KEY=VALUE, комментарии с # и кавычки."""
    values = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def c_string_literal(value):
    """Строковый литерал C: экранируем то, что иначе сломает компиляцию."""
    escaped = []
    for char in value:
        if char in ("\\", '"'):
            escaped.append("\\" + char)
        elif char == "\n":
            escaped.append("\n")
        elif char == "\r":
            escaped.append("\r")
        elif char == "\t":
            escaped.append("\t")
        else:
            escaped.append(char)
    return '"' + "".join(escaped) + '"'


project_dir = Path(env["PROJECT_DIR"])  # noqa: F821
env_file = project_dir / ".env"

if env_file.is_file():
    env_values = parse_env_file(env_file)
    if not env_values.get("WIFI_SSID"):
        print("load_env: WIFI_SSID is empty in .env, Wi-Fi disabled")
else:
    env_values = {}
    print("load_env: .env not found, Wi-Fi disabled (see docs/WIFI.md)")

content = HEADER.format(
    ssid_key=KEYS[0],
    ssid=c_string_literal(env_values.get(KEYS[0], "")),
    password_key=KEYS[1],
    password=c_string_literal(env_values.get(KEYS[1], "")),
)

header_path = project_dir / "include" / "WiFiCredentials.h"
# Перезаписываем только при изменении, иначе каждая сборка была бы полной.
if not header_path.is_file() or header_path.read_text(encoding="utf-8") != content:
    header_path.write_text(content, encoding="utf-8")
    print("load_env: include/WiFiCredentials.h updated")
