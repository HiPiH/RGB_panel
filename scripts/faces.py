"""Смайлики для панели 16 x 16: рисование и анимация.

Каждый смайлик живёт свои 10 секунд, потом карусель переходит к следующему.
Всё считается от прошедшего времени, а не от номера кадра, поэтому на любой
частоте анимация выглядит одинаково.
"""

import math

WIDTH = 16
HEIGHT = 16
PIXELS = WIDTH * HEIGHT

FACE_SECONDS = 10.0

BLACK = (0, 0, 0)
FACE = (255, 190, 20)
DARK = (14, 8, 0)
MOUTH = (120, 20, 30)
TONGUE = (225, 70, 95)
TEETH = (255, 250, 235)
BLUSH = (255, 105, 90)
HEART = (235, 30, 70)
LIPS = (220, 60, 95)
TEAR = (70, 170, 255)
GLASS = (18, 18, 28)
GLINT = (245, 245, 255)

CENTER = (WIDTH - 1) / 2.0
HEAD_RADIUS = 7.4

HEART_BIG = (
    ".#.#.",
    "#####",
    ".###.",
    "..#..",
)
HEART_SMALL = (
    "#.#",
    "###",
    ".#.",
)


class Canvas:
    """Холст 16 x 16 с примитивами, которых хватает на смайлик."""

    def __init__(self):
        self.pixels = [BLACK] * PIXELS

    def put(self, x, y, color):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            self.pixels[y * WIDTH + x] = color

    def get(self, x, y):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            return self.pixels[y * WIDTH + x]
        return None

    def put_over(self, x, y, color, only_on):
        """Кладёт пиксель, только если под ним нужный цвет.

        Так блик не вылезает за пределы очков.
        """
        if self.get(x, y) == only_on:
            self.put(x, y, color)

    def disc(self, cx, cy, radius, color):
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius:
                    self.put(x, y, color)

    def ellipse_points(self, cx, cy, rx, ry):
        points = []
        for y in range(HEIGHT):
            for x in range(WIDTH):
                nx = (x - cx) / rx
                ny = (y - cy) / ry
                if nx * nx + ny * ny <= 1.0:
                    points.append((x, y))
        return points

    def sprite(self, x0, y0, rows, color):
        for dy, row in enumerate(rows):
            for dx, char in enumerate(row):
                if char == "#":
                    self.put(x0 + dx, y0 + dy, color)

    def to_bytes(self):
        return b"".join(bytes(color) for color in self.pixels)


def mix(base, top, amount):
    return tuple(int(b + (t - b) * amount) for b, t in zip(base, top))


def wave(phase, cycles=1.0, offset=0.0):
    """Плавная волна от 0 до 1."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * (phase * cycles + offset))


def head(canvas, bob=0, glow=1.0):
    canvas.disc(CENTER, CENTER + bob, HEAD_RADIUS,
                tuple(min(255, int(c * glow)) for c in FACE))


def eyes(canvas, bob, left_closed=False, right_closed=False, tall=False):
    """Обычные глаза-столбики. Закрытый глаз - только нижняя строка."""
    top = 4 if tall else 5
    for x0, closed in ((4, left_closed), (10, right_closed)):
        for x in (x0, x0 + 1):
            canvas.put(x, 6 + bob, DARK)
            if not closed:
                for y in range(top, 6):
                    canvas.put(x, y + bob, DARK)


def eye_arcs(canvas, bob, happy=True):
    """Закрытые глаза дугой: вверх - смеются, вниз - плачут."""
    if happy:
        shape = ((0, 1), (1, 0), (2, 0), (3, 1))
    else:
        shape = ((0, 0), (1, 1), (2, 1), (3, 0))
    for x0 in (3, 9):
        for dx, dy in shape:
            canvas.put(x0 + dx, 5 + dy + bob, DARK)


def heart_eyes(canvas, bob, big):
    rows = HEART_BIG if big else HEART_SMALL
    offset = 0 if big else 1
    for x0 in (2, 9):
        canvas.sprite(x0 + offset, 4 + offset + bob, rows, HEART)


def smile(canvas, bob, depth, tilt=0.0, thick=False):
    """Улыбка параболой. tilt приподнимает один угол рта."""
    for x in range(3, 13):
        norm = (x - CENTER) / 4.5
        y = 11.0 - depth * norm * norm + tilt * norm
        canvas.put(x, y + bob, DARK)
        if thick and abs(norm) < 0.5:
            canvas.put(x, y - 1 + bob, DARK)


def frown(canvas, bob, depth):
    for x in range(4, 12):
        norm = (x - CENTER) / 4.0
        canvas.put(x, 10.0 + depth * norm * norm + bob, DARK)


def open_mouth(canvas, bob, openness, teeth=True):
    """Открытый рот: эллипс с зубами сверху и языком снизу."""
    # Больше 2.4 рот распирает до подбородка и лицо перестаёт читаться.
    ry = 0.8 + 1.6 * openness
    points = canvas.ellipse_points(CENTER, 10.4 + bob, 3.4, ry)
    if not points:
        return
    for x, y in points:
        canvas.put(x, y, MOUTH)
    top = min(y for _, y in points)
    bottom = max(y for _, y in points)
    if teeth:
        for x, y in points:
            if y == top:
                canvas.put(x, y, TEETH)
    if ry > 1.6:
        for x, y in points:
            if y == bottom:
                canvas.put(x, y, TONGUE)


def round_mouth(canvas, bob, size):
    radius = 0.8 + 1.3 * size
    for x, y in canvas.ellipse_points(CENTER, 10.6 + bob, radius, radius):
        canvas.put(x, y, MOUTH)


def kiss_lips(canvas, bob, pucker):
    rx = 2.0 - 0.6 * pucker
    ry = 0.9 + 0.6 * pucker
    for x, y in canvas.ellipse_points(CENTER, 10.5 + bob, rx, ry):
        canvas.put(x, y, LIPS)
    canvas.put(CENTER, 10.5 + bob, MOUTH)


def blush(canvas, bob, strength):
    color = mix(FACE, BLUSH, strength)
    for x0 in (2, 12):
        for x in (x0, x0 + 1):
            for y in (8, 9):
                if canvas.get(x, y + bob) != BLACK:
                    canvas.put(x, y + bob, color)


def sunglasses(canvas, bob, glint):
    for x0 in (2, 9):
        for x in range(x0, x0 + 5):
            for y in range(5, 8):
                canvas.put(x, y + bob, GLASS)
    for x in (7, 8):
        canvas.put(x, 5 + bob, GLASS)
    # Блик проезжает по стёклам слева направо и за оправу не вылезает.
    gx = -3 + glint * 20
    for step in range(3):
        canvas.put_over(gx + step, 7 - step + bob, GLINT, GLASS)


def tear(canvas, x, y):
    canvas.put(x, y, TEAR)
    canvas.put(x, y + 1, mix(TEAR, (255, 255, 255), 0.4))


# --------------------------------------------------------------- смайлики ---


def face_smile(canvas, phase):
    """Просто улыбается и время от времени моргает."""
    bob = round(math.sin(2 * math.pi * phase) * 0.6)
    head(canvas, bob, 0.85 + 0.15 * math.sin(4 * math.pi * phase))
    blink = 0.33 <= phase < 0.37 or 0.70 <= phase < 0.74
    eyes(canvas, bob, blink, blink)
    smile(canvas, bob, 1.2 + 1.6 * wave(phase), thick=wave(phase) > 0.7)


def face_wink(canvas, phase):
    """Подмигивает правым глазом, ухмылка съезжает вбок."""
    bob = round(math.sin(2 * math.pi * phase) * 0.6)
    head(canvas, bob)
    winking = (phase * 2) % 1.0 < 0.55
    eyes(canvas, bob, right_closed=winking)
    smile(canvas, bob, 1.6, tilt=-0.9 if winking else -0.3)


def face_laugh(canvas, phase):
    """Хохочет: глаза дугами, рот открывается толчками."""
    openness = wave(phase, cycles=5.0)
    bob = 1 if openness > 0.65 else 0
    head(canvas, bob)
    eye_arcs(canvas, bob, happy=True)
    open_mouth(canvas, bob, 0.35 + 0.65 * openness)


def face_surprise(canvas, phase):
    """Удивляется: круглые глаза, рот буквой о, щёки горят."""
    pulse = wave(phase, cycles=3.0)
    head(canvas, 0)
    eyes(canvas, 0, tall=True)
    blush(canvas, 0, 0.55 + 0.45 * pulse)
    round_mouth(canvas, 0, 0.3 + 0.7 * pulse)


def face_kiss(canvas, phase):
    """Целует: губы трубочкой, сердечки улетают вправо."""
    bob = round(math.sin(2 * math.pi * phase) * 0.6)
    head(canvas, bob)
    eyes(canvas, bob, right_closed=True)
    kiss_lips(canvas, bob, wave(phase, cycles=4.0))
    # Сердечко вылетает четыре раза за круг и уходит вверх и вправо.
    flight = (phase * 4) % 1.0
    if flight > 0.15:
        travel = (flight - 0.15) / 0.85
        canvas.sprite(round(9 + travel * 5), round(10 - travel * 8),
                      HEART_SMALL, HEART)


def face_cool(canvas, phase):
    """В солнечных очках: по стёклам пробегает блик."""
    head(canvas, 0)
    sunglasses(canvas, 0, (phase * 3) % 1.0)
    smile(canvas, 0, 1.4, tilt=-0.6 + 0.4 * math.sin(2 * math.pi * phase))


def face_love(canvas, phase):
    """Влюблён: сердечки вместо глаз бьются, улыбка в такт."""
    big = (phase * 5) % 1.0 < 0.5
    bob = 0 if big else 1
    head(canvas, bob)
    heart_eyes(canvas, bob, big)
    smile(canvas, bob, 2.4 if big else 1.8, thick=big)


def face_cry(canvas, phase):
    """Плачет: глаза дугами вниз, рот скорбный, слёзы капают."""
    head(canvas, 0)
    eye_arcs(canvas, 0, happy=False)
    frown(canvas, 0, 1.4 + 0.6 * wave(phase, cycles=2.0))
    for side, delay in ((4, 0.0), (11, 0.5)):
        drop = (phase * 3 + delay) % 1.0
        tear(canvas, side, 7 + drop * 8)


FACES = (
    ("улыбка", face_smile),
    ("подмигивание", face_wink),
    ("хохот", face_laugh),
    ("удивление", face_surprise),
    ("поцелуй", face_kiss),
    ("очки", face_cool),
    ("влюблён", face_love),
    ("слёзы", face_cry),
)

NAMES = tuple(name for name, _ in FACES)
LOOP_SECONDS = FACE_SECONDS * len(FACES)


def face_at(elapsed):
    """Какой смайлик показывать и в какой фазе его анимации."""
    position = elapsed % LOOP_SECONDS
    index = int(position // FACE_SECONDS)
    phase = (position - index * FACE_SECONDS) / FACE_SECONDS
    return index, phase


def render(elapsed, forced=None):
    """Кадр карусели. forced - имя смайлика, если нужен только один."""
    if forced is None:
        index, phase = face_at(elapsed)
    else:
        index = NAMES.index(forced)
        phase = (elapsed % FACE_SECONDS) / FACE_SECONDS
    canvas = Canvas()
    FACES[index][1](canvas, phase)
    return canvas.to_bytes()
