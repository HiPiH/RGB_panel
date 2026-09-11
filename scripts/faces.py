"""Смайлики для панели 16 x 16: рисование и анимация.

Каждый смайлик живёт свои 10 секунд, потом карусель переходит к следующему.
Всё считается от прошедшего времени, а не от номера кадра, поэтому на любой
частоте анимация выглядит одинаково.

Объём набирается тремя приёмами. Голова считается как освещённый шар: у каждого
пикселя берётся нормаль сферы, по ней диффузная составляющая и блик. Края всех
фигур сглаживаются по покрытию пикселя, отсюда полутона вместо лесенки. Черты
лица красятся с оглядкой на освещённость в этой точке, поэтому на теневой
стороне они темнее.

Полутона при этом не должны съедать контраст: ядро мазка ложится в полную силу,
и только края уходят в прозрачность.
"""

import math

WIDTH = 16
HEIGHT = 16
PIXELS = WIDTH * HEIGHT

FACE_SECONDS = 10.0

BLACK = (0, 0, 0)
FACE = (255, 176, 26)
DARK = (6, 2, 0)
MOUTH = (74, 10, 20)
TONGUE = (214, 74, 96)
TEETH = (250, 244, 226)
BLUSH = (255, 92, 84)
HEART = (232, 28, 68)
LIPS = (214, 52, 92)
TEAR = (86, 176, 255)
GLASS = (8, 8, 16)
GLINT = (240, 246, 255)
WHITE = (255, 255, 255)

CENTER = (WIDTH - 1) / 2.0
HEAD_RADIUS = 7.3

# Свет падает сверху слева и немного спереди.
LIGHT = (-0.52, -0.62, 0.59)
AMBIENT = 0.55          # сколько света достаётся теневой стороне
SHADING_GAMMA = 1.7     # круче спад света, объём заметнее без потери яркости
SPECULAR = 0.45         # сила блика
SPECULAR_HARDNESS = 18  # чем больше, тем блик компактнее


def clamp(value, low=0.0, high=1.0):
    return low if value < low else high if value > high else value


def scale(color, factor):
    return tuple(min(255, max(0, int(channel * factor))) for channel in color)


def mix(base, top, amount):
    amount = clamp(amount)
    return tuple(int(b + (t - b) * amount) for b, t in zip(base, top))


def luminance(color):
    return 0.30 * color[0] + 0.59 * color[1] + 0.11 * color[2]


def coverage(px, py, inside, samples=3):
    """Какая доля пикселя попала внутрь фигуры. Отсюда берутся полутона."""
    hits = 0
    for sy in range(samples):
        y = py - 0.5 + (sy + 0.5) / samples
        for sx in range(samples):
            x = px - 0.5 + (sx + 0.5) / samples
            if inside(x, y):
                hits += 1
    return hits / (samples * samples)


def wave(phase, cycles=1.0, offset=0.0):
    """Плавная волна от 0 до 1."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * (phase * cycles + offset))


def blink(phase, moments, width=0.045):
    """Насколько открыт глаз: 1 открыт, 0 закрыт. Моргание плавное."""
    closed = 0.0
    for moment in moments:
        distance = abs(((phase - moment + 0.5) % 1.0) - 0.5)
        if distance < width:
            closed = max(closed, 1.0 - (distance / width) ** 2)
    return 1.0 - closed


class Canvas:
    """Холст 16 x 16 со сглаживанием краёв и картой освещённости."""

    def __init__(self):
        self.pixels = [BLACK] * PIXELS
        self.light = [1.0] * PIXELS

    def blend(self, x, y, color, alpha=1.0):
        x, y = int(round(x)), int(round(y))
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT) or alpha <= 0.0:
            return
        index = y * WIDTH + x
        if alpha >= 1.0:
            self.pixels[index] = color
        else:
            self.pixels[index] = mix(self.pixels[index], color, alpha)

    def blend_over_dark(self, x, y, color, alpha=1.0, threshold=80):
        """Кладёт пиксель только поверх тёмного, чтобы блик не убежал с очков."""
        ix, iy = int(round(x)), int(round(y))
        if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
            if luminance(self.pixels[iy * WIDTH + ix]) < threshold:
                self.blend(x, y, color, alpha)

    def lit(self, x, y, color, floor=0.45):
        """Цвет черты лица с поправкой на освещённость шара в этой точке."""
        ix, iy = int(round(x)), int(round(y))
        if not (0 <= ix < WIDTH and 0 <= iy < HEIGHT):
            return color
        light = self.light[iy * WIDTH + ix] ** SHADING_GAMMA
        return scale(color, floor + (1.0 - floor) * light)

    def sphere(self, cx, cy, radius, color, glow=1.0):
        """Освещённый шар: диффузная составляющая, блик и мягкий край."""
        def inside(x, y):
            return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius

        for py in range(HEIGHT):
            dy = py - cy
            if abs(dy) > radius + 1.0:
                continue
            for px in range(WIDTH):
                dx = px - cx
                distance = math.hypot(dx, dy)
                if distance > radius + 0.8:
                    continue
                if distance <= radius - 0.8:
                    cover = 1.0
                else:
                    cover = coverage(px, py, inside)
                    if cover <= 0.0:
                        continue

                nx, ny = dx / radius, dy / radius
                nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
                ndotl = clamp(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2])
                light = AMBIENT + (1.0 - AMBIENT) * ndotl

                tone = scale(color, (light ** SHADING_GAMMA) * glow)
                spec = SPECULAR * ndotl ** SPECULAR_HARDNESS
                if spec > 0.004:
                    tone = mix(tone, WHITE, min(0.6, spec))
                self.blend(px, py, tone, cover)
                self.light[py * WIDTH + px] = light

    def ellipse(self, cx, cy, rx, ry, color, shaded=True, alpha=1.0):
        if rx <= 0.0 or ry <= 0.0:
            return

        def inside(x, y):
            return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0

        for py in range(int(cy - ry - 1), int(cy + ry + 2)):
            for px in range(int(cx - rx - 1), int(cx + rx + 2)):
                cover = coverage(px, py, inside)
                if cover <= 0.0:
                    continue
                tone = self.lit(px, py, color) if shaded else color
                self.blend(px, py, tone, cover * alpha)

    def stroke(self, x, y, color, thickness=1.0, alpha=1.0, shaded=True):
        """Вертикальный мазок с дробной координатой: кривая идёт без лесенки."""
        top = y - thickness / 2.0
        bottom = y + thickness / 2.0
        rows = []
        for py in range(int(math.floor(top - 0.5)), int(math.ceil(bottom + 0.5)) + 1):
            overlap = min(bottom, py + 0.5) - max(top, py - 0.5)
            if overlap > 0.0:
                rows.append((py, overlap))
        if not rows:
            return
        # Ядро мазка кладём в полную силу. Без этого тонкая линия расходится
        # на два полупрозрачных пикселя и рот со глазами теряют контраст.
        peak = max(overlap for _, overlap in rows)
        for py, overlap in rows:
            tone = self.lit(x, py, color) if shaded else color
            self.blend(x, py, tone, clamp(overlap / peak) * alpha)

    def heart(self, cx, cy, size, color):
        """Сердце по неявной формуле, поэтому оно тоже со сглаженным краем."""
        def inside(x, y):
            nx = (x - cx) / size
            ny = -(y - cy) / size
            return (nx * nx + ny * ny - 1.0) ** 3 - nx * nx * ny ** 3 <= 0.0

        for py in range(int(cy - size - 1), int(cy + size + 2)):
            for px in range(int(cx - size - 1), int(cx + size + 2)):
                cover = coverage(px, py, inside)
                if cover <= 0.0:
                    continue
                # Сердце тоже объёмное: сверху слева светлее, снизу темнее.
                shade = 1.15 - 0.4 * ((py - cy + size) / (2 * size))
                self.blend(px, py, scale(color, shade), cover)

    def glow_patch(self, cx, cy, radius, color, strength):
        """Мягкое пятно без чёткого края: румянец, тень."""
        for py in range(int(cy - radius - 1), int(cy + radius + 2)):
            for px in range(int(cx - radius - 1), int(cx + radius + 2)):
                distance = math.hypot(px - cx, py - cy)
                if distance > radius:
                    continue
                falloff = (1.0 - distance / radius) ** 2
                self.blend(px, py, color, falloff * strength)

    def to_bytes(self):
        return b"".join(bytes(color) for color in self.pixels)


# ------------------------------------------------------------- части лица ---


def head(canvas, bob=0.0, glow=1.0):
    canvas.sphere(CENTER, CENTER + bob, HEAD_RADIUS, FACE, glow)


def eyes(canvas, bob, left=1.0, right=1.0, width=1.05, height=1.3):
    """Глаза-капли. left и right - насколько открыт глаз, 0 закрыт."""
    for cx, openness in ((CENTER - 2.9, left), (CENTER + 2.9, right)):
        canvas.ellipse(cx, 5.7 + bob, width, 0.3 + height * clamp(openness), DARK)


def eye_arcs(canvas, bob, happy=True, thickness=1.2):
    """Закрытые глаза дугой: вверх смеются, вниз плачут."""
    for cx in (CENTER - 2.9, CENTER + 2.9):
        for step in range(5):
            offset = (step - 2) / 2.0
            bend = offset * offset * 0.85
            y = 5.5 + (bend if happy else 0.85 - bend)
            canvas.stroke(cx + offset * 2.0, y + bob, DARK, thickness)


def heart_eyes(canvas, bob, size):
    for cx in (CENTER - 2.9, CENTER + 2.9):
        canvas.heart(cx, 5.8 + bob, size, HEART)


def smile(canvas, bob, depth, tilt=0.0, thickness=1.3):
    """Улыбка параболой, дробная высота сглаживается мазком."""
    for x in range(3, 13):
        norm = (x - CENTER) / 4.5
        y = 11.0 - depth * norm * norm + tilt * norm
        canvas.stroke(x, y + bob, DARK, thickness)


def frown(canvas, bob, depth, thickness=1.3):
    for x in range(4, 12):
        norm = (x - CENTER) / 4.0
        canvas.stroke(x, 10.0 + depth * norm * norm + bob, DARK, thickness)


def open_mouth(canvas, bob, openness):
    """Открытый рот: тёмная глубина, зубы сверху, язык снизу."""
    cy = 10.3 + bob
    rx = 3.3
    ry = 0.7 + 1.7 * clamp(openness)

    def inside(x, y):
        return ((x - CENTER) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0

    for py in range(int(cy - ry - 1), int(cy + ry + 2)):
        for px in range(3, 13):
            cover = coverage(px, py, inside)
            if cover <= 0.0:
                continue
            depth = (py - cy) / ry  # -1 у верхней губы, 1 у нижней
            if depth < -0.42:
                color = TEETH
            elif depth > 0.45 and ry > 1.3:
                color = TONGUE
            else:
                # Глубина рта темнеет к центру.
                color = scale(MOUTH, 0.55 + 0.45 * abs(depth))
            canvas.blend(px, py, canvas.lit(px, py, color, floor=0.6), cover)


def round_mouth(canvas, bob, size):
    radius = 0.75 + 1.25 * clamp(size)
    canvas.ellipse(CENTER, 10.6 + bob, radius, radius, MOUTH)
    canvas.ellipse(CENTER, 10.6 + bob + radius * 0.45, radius * 0.55,
                   radius * 0.35, TONGUE, alpha=0.8)


def kiss_lips(canvas, bob, pucker):
    rx = 2.0 - 0.7 * pucker
    ry = 0.85 + 0.7 * pucker
    canvas.ellipse(CENTER, 10.5 + bob, rx, ry, LIPS)
    canvas.ellipse(CENTER, 10.5 + bob, rx * 0.45, ry * 0.45, MOUTH)


def blush(canvas, bob, strength):
    for cx in (CENTER - 4.6, CENTER + 4.6):
        canvas.glow_patch(cx, 9.2 + bob, 2.4, BLUSH, 0.55 * strength)


def sunglasses(canvas, bob, glint):
    for cx in (CENTER - 3.0, CENTER + 3.0):
        canvas.ellipse(cx, 5.9 + bob, 2.4, 1.6, GLASS, shaded=False)
    for x in (6, 7, 8, 9):
        canvas.stroke(x, 5.2 + bob, GLASS, 0.9, shaded=False)
    # Блик проезжает по стёклам слева направо и за оправу не вылезает.
    position = -4.0 + glint * 24.0
    for step in range(4):
        canvas.blend_over_dark(position + step * 0.8, 7.2 - step * 0.8 + bob,
                               GLINT, 0.85 - 0.15 * step)


def tear(canvas, x, y):
    canvas.ellipse(x, y, 0.75, 1.05, TEAR, shaded=False)
    canvas.blend(x, y - 0.4, mix(TEAR, WHITE, 0.55), 0.9)


# --------------------------------------------------------------- смайлики ---


def face_smile(canvas, phase):
    """Улыбается и время от времени моргает."""
    bob = math.sin(2 * math.pi * phase) * 0.6
    head(canvas, bob, 0.9 + 0.1 * math.sin(4 * math.pi * phase))
    open_amount = blink(phase, (0.34, 0.71))
    eyes(canvas, bob, open_amount, open_amount)
    smile(canvas, bob, 1.2 + 1.7 * wave(phase),
          thickness=1.2 + 0.4 * wave(phase))


def face_wink(canvas, phase):
    """Подмигивает правым глазом, ухмылка съезжает вбок."""
    bob = math.sin(2 * math.pi * phase) * 0.6
    head(canvas, bob)
    right = clamp(0.5 + 1.4 * math.cos(4 * math.pi * phase))
    eyes(canvas, bob, left=blink(phase, (0.15, 0.85)), right=right)
    smile(canvas, bob, 1.7, tilt=-0.9 + 0.6 * right)


def face_laugh(canvas, phase):
    """Хохочет: глаза дугами, рот открывается толчками."""
    openness = wave(phase, cycles=5.0)
    bob = 0.5 * openness
    head(canvas, bob)
    eye_arcs(canvas, bob, happy=True, thickness=1.2 + 0.3 * openness)
    open_mouth(canvas, bob, 0.3 + 0.7 * openness)


def face_surprise(canvas, phase):
    """Удивляется: круглые глаза, рот буквой о, щёки горят."""
    pulse = wave(phase, cycles=3.0)
    head(canvas, 0.0)
    eyes(canvas, 0.0, width=1.05, height=1.45)
    blush(canvas, 0.0, 0.6 + 0.4 * pulse)
    round_mouth(canvas, 0.0, 0.3 + 0.7 * pulse)


def face_kiss(canvas, phase):
    """Целует: губы трубочкой, сердечки улетают вправо."""
    bob = math.sin(2 * math.pi * phase) * 0.6
    head(canvas, bob)
    eyes(canvas, bob, left=blink(phase, (0.5,)), right=0.08)
    kiss_lips(canvas, bob, wave(phase, cycles=4.0))
    # Сердечко вылетает четыре раза за круг и уходит вверх и вправо.
    flight = (phase * 4) % 1.0
    if flight > 0.12:
        travel = (flight - 0.12) / 0.88
        canvas.heart(10.0 + travel * 5.0, 10.0 - travel * 9.0,
                     1.5 - 0.5 * travel, HEART)


def face_cool(canvas, phase):
    """В солнечных очках: по стёклам пробегает блик."""
    head(canvas, 0.0)
    sunglasses(canvas, 0.0, (phase * 3) % 1.0)
    smile(canvas, 0.0, 1.5, tilt=-0.7 + 0.4 * math.sin(2 * math.pi * phase))


def face_love(canvas, phase):
    """Влюблён: сердечки вместо глаз бьются, улыбка в такт."""
    beat = wave(phase, cycles=5.0)
    bob = -0.3 * beat
    head(canvas, bob)
    heart_eyes(canvas, bob, 1.35 + 0.45 * beat)
    smile(canvas, bob, 1.8 + 0.8 * beat, thickness=1.2 + 0.4 * beat)


def face_cry(canvas, phase):
    """Плачет: глаза дугами вниз, рот скорбный, слёзы капают."""
    head(canvas, 0.0, glow=0.92)
    eye_arcs(canvas, 0.0, happy=False)
    frown(canvas, 0.0, 1.3 + 0.7 * wave(phase, cycles=2.0))
    for side, delay in ((CENTER - 3.2, 0.0), (CENTER + 3.2, 0.5)):
        drop = (phase * 3 + delay) % 1.0
        tear(canvas, side, 7.2 + drop * 8.5)


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
