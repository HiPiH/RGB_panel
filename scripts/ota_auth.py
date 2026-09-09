"""Подставляет пароль OTA в команду заливки по воздуху.

Скрипт обязан быть post-скриптом. Платформа задаёт флаги espota через
env.Replace уже после того, как отрабатывают pre-скрипты, поэтому пароль,
добавленный раньше, просто теряется: espota получает пустой auth и заливка
падает на аутентификации.

Пароль читается из .env, в platformio.ini и в git он не попадает и нигде
не печатается.
"""

from pathlib import Path

Import("env")  # noqa: F821  - подставляется PlatformIO

if env.subst("$UPLOAD_PROTOCOL") == "espota":  # noqa: F821
    env_file = Path(env["PROJECT_DIR"]) / ".env"  # noqa: F821
    password = ""
    if env_file.is_file():
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if not line.startswith("OTA_PASSWORD="):
                continue
            password = line.split("=", 1)[1].strip()
            if len(password) >= 2 and password[0] == password[-1] and password[0] in "\"'":
                password = password[1:-1]

    if password:
        # Удвоение $ нужно потому, что SCons считает одиночный $ началом
        # своей подстановки.
        env.Append(UPLOADERFLAGS=["--auth=" + password.replace("$", "$$")])  # noqa: F821
        print("ota_auth: password taken from .env")
    else:
        print("ota_auth: OTA_PASSWORD is empty in .env, upload will be refused")
