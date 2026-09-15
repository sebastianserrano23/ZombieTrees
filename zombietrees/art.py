"""Procedurally generated graphics: wall textures, sky, zombie trees, pickups and weapon viewmodels.

Everything is drawn with pygame primitives at startup so the game ships without asset files.
"""
import math
import random

import pygame

from .settings import FOG_COLOR, FOG_LEVELS, FOV, RENDER_H, RENDER_W, TEX_SIZE
from .world import CABIN, FENCE, FOREST, ROCK


def _clamp(v):
    return 0 if v < 0 else 255 if v > 255 else int(v)


def _shade(color, f):
    return tuple(_clamp(c * f) for c in color[:3])


def _lerp(a, b, t):
    return tuple(_clamp(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------- wall textures

def _forest_tex(rng):
    s = pygame.Surface((TEX_SIZE, TEX_SIZE))
    for y in range(TEX_SIZE):
        pygame.draw.line(s, _lerp((10, 14, 10), (22, 30, 22), y / TEX_SIZE), (0, y), (TEX_SIZE, y))
    # A pair of glowing eyes lurking between the trunks.
    ex, ey = rng.randint(8, 50), rng.randint(14, 30)
    x = 0
    trunks = []
    while x < TEX_SIZE:
        w = rng.randint(7, 14)
        trunks.append((x, w))
        x += w + rng.randint(2, 5)
    for x0, w in trunks:
        base = rng.choice([(62, 48, 34), (50, 42, 36), (70, 58, 42), (44, 38, 32)])
        for i in range(w):
            curve = 0.55 + 0.45 * math.sin((i + 0.5) / w * math.pi)
            for y in range(TEX_SIZE):
                n = rng.uniform(0.8, 1.15)
                groove = 0.65 if (i + (y // 9)) % 4 == 0 else 1.0
                px = x0 + i
                if px < TEX_SIZE:
                    s.set_at((px, y), _shade(base, curve * n * groove))
        for _ in range(rng.randint(1, 3)):
            my = rng.randint(30, 60)
            pygame.draw.ellipse(s, (46, 70, 34), (x0, my, max(3, w - 2), rng.randint(3, 7)))
        ky = rng.randint(6, 56)
        pygame.draw.ellipse(s, _shade(base, 0.45), (x0 + w // 3, ky, max(2, w // 3), 4))
    for dx in (0, 7):
        pygame.draw.circle(s, (120, 10, 0), (ex + dx, ey), 2)
        s.set_at((ex + dx, ey), (255, 60, 30))
    return s


def _rock_tex(rng):
    s = pygame.Surface((TEX_SIZE, TEX_SIZE))
    for y in range(TEX_SIZE):
        for x in range(TEX_SIZE):
            n = rng.uniform(0.82, 1.12)
            b = 78 + 10 * math.sin(x * 0.3) * math.cos(y * 0.23)
            s.set_at((x, y), _shade((b, b + 2, b + 4), n))
    for _ in range(7):
        x, y = rng.randint(0, 63), rng.randint(0, 63)
        for _ in range(rng.randint(5, 12)):
            nx, ny = x + rng.randint(-5, 5), y + rng.randint(1, 6)
            pygame.draw.line(s, (38, 38, 42), (x, y), (nx, ny), 1)
            x, y = nx, ny
    for _ in range(40):
        x, y = rng.randint(0, 63), rng.randint(44, 63)
        pygame.draw.circle(s, (48, 78, 38), (x, y), rng.randint(1, 3))
    return s


def _cabin_tex(rng):
    s = pygame.Surface((TEX_SIZE, TEX_SIZE))
    for row in range(8):
        y0 = row * 8
        base = rng.choice([(96, 66, 40), (84, 58, 36), (104, 74, 46), (76, 52, 34)])
        for y in range(y0, y0 + 8):
            for x in range(TEX_SIZE):
                grain = 0.9 + 0.1 * math.sin(x * 0.5 + row * 3 + (y - y0) * 0.8)
                s.set_at((x, y), _shade(base, grain * rng.uniform(0.9, 1.08)))
        pygame.draw.line(s, (34, 22, 14), (0, y0 + 7), (TEX_SIZE, y0 + 7))
        seam = rng.randint(10, 54)
        pygame.draw.line(s, (40, 26, 16), (seam, y0), (seam, y0 + 7))
        s.set_at((seam - 3, y0 + 3), (30, 30, 30))
        s.set_at((seam + 3, y0 + 3), (30, 30, 30))
    # Sap slime dripping down the planks.
    for _ in range(3):
        x = rng.randint(4, 60)
        length = rng.randint(10, 40)
        pygame.draw.line(s, (70, 130, 40), (x, 0), (x, length), 2)
        pygame.draw.circle(s, (90, 160, 50), (x, length), 2)
    return s


def _fence_tex(rng):
    s = pygame.Surface((TEX_SIZE, TEX_SIZE))
    for y in range(TEX_SIZE):
        pygame.draw.line(s, _lerp((12, 16, 12), (24, 30, 22), y / TEX_SIZE), (0, y), (TEX_SIZE, y))
    for rail_y in (18, 44):
        pygame.draw.rect(s, (80, 62, 44), (0, rail_y, TEX_SIZE, 6))
        pygame.draw.line(s, (50, 38, 26), (0, rail_y + 5), (TEX_SIZE, rail_y + 5))
    for i in range(4):
        x0 = 2 + i * 16
        top = rng.randint(2, 8)
        base = rng.choice([(110, 86, 58), (96, 76, 52), (120, 94, 64)])
        pygame.draw.rect(s, base, (x0, top, 11, TEX_SIZE - top))
        pygame.draw.polygon(s, base, [(x0, top), (x0 + 5, top - 4), (x0 + 11, top)])
        pygame.draw.line(s, _shade(base, 0.6), (x0 + 10, top), (x0 + 10, TEX_SIZE))
        pygame.draw.line(s, _shade(base, 1.2), (x0, top), (x0, TEX_SIZE))
    return s


def _build_shaded(tex):
    """Pre-bake fog/side-darkened variants: shaded[side][fog_level]."""
    out = []
    for side in (0, 1):
        levels = []
        side_f = 1.0 if side == 0 else 0.7
        for lv in range(FOG_LEVELS):
            t = lv / (FOG_LEVELS - 1)
            s = tex.copy()
            m = _clamp(255 * (1 - t) * side_f)
            s.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
            s.fill(tuple(int(c * t) for c in FOG_COLOR), special_flags=pygame.BLEND_RGB_ADD)
            levels.append(s)
        out.append(levels)
    return out


# ---------------------------------------------------------------- sky & floor

def _sky_panorama(rng):
    pano_w = int(RENDER_W * (2 * math.pi) / FOV)
    h = RENDER_H // 2
    s = pygame.Surface((pano_w, h))
    top, horizon = (6, 5, 16), FOG_COLOR
    for y in range(h):
        pygame.draw.line(s, _lerp(top, horizon, (y / h) ** 1.6), (0, y), (pano_w, y))
    for _ in range(220):
        x, y = rng.randint(0, pano_w - 1), rng.randint(0, int(h * 0.6))
        b = rng.randint(90, 200)
        s.set_at((x, y), (b, b, int(b * 0.9)))

    def wrap_draw(fn, x):
        for off in (-pano_w, 0, pano_w):
            fn(x + off)

    moon_x, moon_y = int(pano_w * 0.62), 42
    def moon(x):
        for r, a in ((34, 0.08), (26, 0.16), (20, 0.3)):
            pygame.draw.circle(s, _lerp(FOG_COLOR, (150, 190, 120), a), (x, moon_y), r)
        pygame.draw.circle(s, (206, 222, 176), (x, moon_y), 15)
        pygame.draw.circle(s, (170, 190, 146), (x - 5, moon_y - 3), 4)
        pygame.draw.circle(s, (180, 198, 154), (x + 6, moon_y + 5), 3)
    wrap_draw(moon, moon_x)

    # Jagged silhouette of the dead forest on the horizon.
    far = _lerp(FOG_COLOR, (0, 0, 0), 0.35)
    x = 0
    while x < pano_w:
        tree_h = rng.randint(10, 46)
        w = rng.randint(2, 5)
        def tree(px, tree_h=tree_h, w=w):
            pygame.draw.rect(s, far, (px, h - tree_h, w, tree_h))
            for _ in range(3):
                by = h - tree_h + rng.randint(0, tree_h // 2)
                bl = rng.randint(4, 10) * rng.choice((-1, 1))
                pygame.draw.line(s, far, (px + w // 2, by), (px + w // 2 + bl, by - abs(bl) // 2), 1)
        wrap_draw(tree, x)
        x += rng.randint(4, 14)
    pygame.draw.rect(s, far, (0, h - 6, pano_w, 6))
    return s


def _floor():
    h = RENDER_H - RENDER_H // 2
    s = pygame.Surface((RENDER_W, h))
    for y in range(h):
        s.fill(_lerp(FOG_COLOR, (52, 44, 30), (y / h) ** 0.8), (0, y, RENDER_W, 1))
    return s


# ---------------------------------------------------------------- zombie trees

TREE_STYLES = {
    "sapling": dict(bark=(128, 98, 64), leaf=(146, 196, 62), eye=(255, 232, 60), canopy=0.8),
    "rotwood": dict(bark=(96, 72, 50), leaf=(84, 124, 50), eye=(255, 54, 30), canopy=1.0),
    "thornback": dict(bark=(64, 52, 58), leaf=None, eye=(206, 90, 255), canopy=0.0, thorns=True),
    "spitter": dict(bark=(104, 100, 72), leaf=(112, 156, 92), eye=(90, 255, 120), canopy=0.9, vines=True),
    "elder": dict(bark=(74, 58, 44), leaf=(58, 92, 40), eye=(255, 150, 20), canopy=1.25, moss=True),
}


def _zombie_tree(kind, frame):
    st = TREE_STYLES[kind]
    rng = random.Random(kind)
    W, H = 96, 128
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    bark = st["bark"]
    dark = _shade(bark, 0.6)
    cx = 48
    sway = (-3, 3, 0)[frame]
    ground = H - 2
    trunk_bot = H - 20
    top_y = 44

    # Root legs
    stride = (7, -7, 0)[frame]
    for sgn in (-1, 1):
        foot = cx + sgn * 16 + (stride if sgn < 0 else -stride)
        pygame.draw.polygon(s, dark, [(cx + sgn * 3, trunk_bot - 8), (cx + sgn * 14, trunk_bot - 6),
                                      (foot + sgn * 6, ground), (foot - sgn * 5, ground)])
        pygame.draw.line(s, dark, (foot, ground - 1), (foot + sgn * 11, ground - 2), 3)
        pygame.draw.line(s, dark, (foot, ground - 1), (foot - sgn * 7, ground), 2)

    # Arms (behind canopy, in front of legs)
    if frame == 2:
        arms = [((cx - 10, 62), (cx - 34, 44), (cx - 26, 20)), ((cx + 10, 62), (cx + 34, 44), (cx + 26, 20))]
    else:
        lift = (4, -4)[frame]
        arms = [((cx - 10, 62), (cx - 30, 66 + lift), (cx - 40, 86 + lift)),
                ((cx + 10, 62), (cx + 30, 66 - lift), (cx + 40, 86 - lift))]
    for sh, el, hand in arms:
        pygame.draw.line(s, bark, sh, el, 7)
        pygame.draw.line(s, bark, el, hand, 5)
        pygame.draw.circle(s, bark, el, 3)
        dx, dy = hand[0] - el[0], hand[1] - el[1]
        ang = math.atan2(dy, dx)
        for spread in (-0.6, 0.0, 0.6):
            a = ang + spread
            tip = (hand[0] + math.cos(a) * 9, hand[1] + math.sin(a) * 9)
            pygame.draw.line(s, dark, hand, tip, 2)
        if st.get("thorns"):
            mid = ((sh[0] + el[0]) // 2, (sh[1] + el[1]) // 2)
            pygame.draw.polygon(s, (30, 24, 28), [(mid[0] - 2, mid[1]), (mid[0] + 2, mid[1]), (mid[0], mid[1] - 7)])

    # Trunk
    pygame.draw.polygon(s, bark, [(cx - 15, trunk_bot), (cx + 15, trunk_bot),
                                  (cx + 10 + sway, top_y), (cx - 10 + sway, top_y)])
    for i in range(6):
        x = cx - 11 + i * 4 + rng.randint(-1, 1)
        pygame.draw.line(s, dark, (x, trunk_bot - 2), (x + sway, top_y + 4 + rng.randint(0, 8)), 1)
    pygame.draw.ellipse(s, _shade(bark, 0.45), (cx + 3, 94, 8, 5))
    if st.get("moss"):
        for _ in range(10):
            pygame.draw.circle(s, (52, 96, 40), (cx + rng.randint(-13, 13), rng.randint(80, trunk_bot)), rng.randint(2, 4))
    if st.get("thorns"):
        for _ in range(14):
            tx, ty = cx + rng.randint(-12, 12) + sway // 2, rng.randint(top_y, trunk_bot - 4)
            d = -1 if tx < cx else 1
            pygame.draw.polygon(s, (28, 22, 26), [(tx, ty - 2), (tx, ty + 2), (tx + d * 8, ty - 3)])

    # Canopy
    if st["leaf"]:
        leaf = st["leaf"]
        c = st["canopy"]
        blobs = [(0, 26, 22), (-18, 32, 16), (18, 32, 16), (-10, 14, 15), (12, 14, 15), (0, 6, 12)]
        for bx, by, br in blobs:
            pygame.draw.circle(s, _shade(leaf, 0.55), (cx + int(bx * c) + sway, int(by * c + (1 - c) * 30)), int(br * c) + 2)
        for bx, by, br in blobs:
            pygame.draw.circle(s, leaf, (cx + int(bx * c) + sway - 1, int(by * c + (1 - c) * 30) - 1), int(br * c))
        for _ in range(12):
            hx = cx + rng.randint(-26, 26) + sway
            hy = rng.randint(6, 40)
            pygame.draw.circle(s, _shade(leaf, 0.4), (hx, hy), rng.randint(1, 3))
    else:
        # Bare, jagged branches
        for bx, by in ((-24, 12), (22, 8), (-8, 2), (12, 24), (-30, 30)):
            pygame.draw.line(s, bark, (cx + sway, top_y + 2), (cx + bx + sway, by + 8), 3)
    if st.get("vines"):
        for i in range(9):
            vx = cx - 28 + i * 7 + sway
            vl = 50 + rng.randint(0, 40)
            pts = [(vx + math.sin(k * 0.7 + i) * 2, 20 + k * vl / 8) for k in range(9)]
            pygame.draw.lines(s, _shade(st["leaf"], 0.8), False, pts, 2)

    # Face
    eye = st["eye"]
    ey = 64
    for ex in (cx - 7 + sway // 2, cx + 7 + sway // 2):
        glow = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*eye, 70), (10, 10), 9)
        pygame.draw.circle(glow, (*eye, 140), (10, 10), 5)
        s.blit(glow, (ex - 10, ey - 10))
        pygame.draw.circle(s, eye, (ex, ey), 3)
        s.set_at((ex, ey), (255, 255, 230))
    pygame.draw.line(s, (20, 12, 8), (cx - 12 + sway // 2, ey - 7), (cx - 3 + sway // 2, ey - 3), 3)
    pygame.draw.line(s, (20, 12, 8), (cx + 12 + sway // 2, ey - 7), (cx + 3 + sway // 2, ey - 3), 3)
    mouth_open = 12 if frame == 2 else 7
    mx = cx + sway // 2
    mouth = [(mx - 9, 76), (mx - 4, 74), (mx, 77), (mx + 4, 74), (mx + 9, 76),
             (mx + 6, 76 + mouth_open), (mx, 78 + mouth_open), (mx - 6, 76 + mouth_open)]
    pygame.draw.polygon(s, (22, 6, 4), mouth)
    for tx in (-6, -2, 2, 6):
        pygame.draw.polygon(s, (220, 210, 160), [(mx + tx - 1, 76), (mx + tx + 1, 76), (mx + tx, 80)])
    pygame.draw.line(s, (100, 200, 60), (mx - 3, 78 + mouth_open), (mx - 3, 84 + mouth_open), 2)
    return s


def _corpse(kind):
    st = TREE_STYLES[kind]
    bark = st["bark"]
    dark = _shade(bark, 0.55)
    s = pygame.Surface((96, 36), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (20, 50, 14, 160), (4, 24, 88, 12))
    pygame.draw.rect(s, bark, (24, 16, 62, 14), border_radius=6)
    pygame.draw.ellipse(s, _shade(bark, 1.25), (80, 15, 12, 16))
    pygame.draw.ellipse(s, dark, (83, 19, 6, 8))
    for x in range(30, 80, 7):
        pygame.draw.line(s, dark, (x, 18), (x + 4, 28), 1)
    pygame.draw.polygon(s, bark, [(6, 32), (26, 32), (24, 10), (19, 16), (15, 6), (11, 15), (8, 9)])
    pygame.draw.line(s, (100, 200, 60), (40, 30), (40, 35), 2)
    pygame.draw.line(s, (100, 200, 60), (60, 30), (61, 34), 2)
    if st["leaf"]:
        for x in (36, 50, 66):
            pygame.draw.circle(s, _shade(st["leaf"], 0.6), (x, 14), 5)
    return s


# ---------------------------------------------------------------- pickups

def _ammo_crate():
    s = pygame.Surface((48, 40), pygame.SRCALPHA)
    pygame.draw.rect(s, (74, 84, 44), (4, 14, 40, 24), border_radius=2)
    pygame.draw.rect(s, (54, 62, 32), (4, 14, 40, 5))
    pygame.draw.rect(s, (40, 46, 24), (4, 14, 40, 24), 2, border_radius=2)
    for i in range(5):
        x = 9 + i * 7
        pygame.draw.rect(s, (200, 160, 50), (x, 4, 4, 12))
        pygame.draw.polygon(s, (230, 200, 90), [(x, 4), (x + 4, 4), (x + 2, 0)])
    pygame.draw.rect(s, (230, 210, 120), (16, 24, 16, 6))
    return s


def _health_kit():
    s = pygame.Surface((48, 40), pygame.SRCALPHA)
    pygame.draw.rect(s, (230, 232, 225), (4, 10, 40, 28), border_radius=4)
    pygame.draw.rect(s, (150, 150, 140), (4, 10, 40, 28), 2, border_radius=4)
    pygame.draw.rect(s, (120, 120, 110), (18, 4, 12, 8), 2)
    pygame.draw.rect(s, (40, 180, 70), (21, 14, 6, 20))
    pygame.draw.rect(s, (40, 180, 70), (14, 21, 20, 6))
    return s


# ---------------------------------------------------------------- viewmodels

SKIN = (206, 156, 116)
SKIN_D = (160, 116, 84)
SLEEVE = (54, 64, 40)


def _hand(s, x, y, w, h):
    pygame.draw.rect(s, SKIN, (x, y, w, h), border_radius=5)
    for i in range(1, 4):
        pygame.draw.line(s, SKIN_D, (x + 2, y + i * h // 4), (x + w - 3, y + i * h // 4), 1)


def _pistol_vm():
    s = pygame.Surface((120, 130), pygame.SRCALPHA)
    pygame.draw.polygon(s, SLEEVE, [(34, 130), (104, 130), (92, 104), (46, 104)])
    pygame.draw.polygon(s, SKIN, [(44, 108), (94, 108), (86, 80), (52, 80)])
    pygame.draw.rect(s, (38, 38, 42), (56, 64, 28, 30))  # grip
    pygame.draw.rect(s, (58, 58, 64), (50, 36, 40, 34), border_radius=3)  # slide rear
    pygame.draw.rect(s, (84, 84, 92), (50, 36, 40, 6), border_radius=3)
    pygame.draw.rect(s, (30, 30, 34), (52, 30, 8, 8))  # rear sights
    pygame.draw.rect(s, (30, 30, 34), (80, 30, 8, 8))
    pygame.draw.rect(s, (230, 230, 200), (54, 33, 3, 3))
    pygame.draw.rect(s, (230, 230, 200), (83, 33, 3, 3))
    pygame.draw.rect(s, (40, 40, 44), (68, 26, 4, 10))  # front sight
    pygame.draw.rect(s, (90, 255, 90), (69, 27, 2, 2))
    pygame.draw.line(s, (26, 26, 30), (54, 52), (86, 52), 2)
    _hand(s, 50, 76, 40, 22)
    return s, (70, 24)


def _shotgun_vm():
    s = pygame.Surface((200, 150), pygame.SRCALPHA)
    pygame.draw.polygon(s, SLEEVE, [(120, 150), (200, 150), (190, 118), (140, 110)])
    pygame.draw.polygon(s, (44, 44, 48), [(92, 18), (108, 18), (124, 110), (76, 110)])  # barrel
    pygame.draw.polygon(s, (70, 70, 76), [(94, 18), (100, 18), (98, 110), (84, 110)])
    pygame.draw.ellipse(s, (20, 20, 22), (93, 14, 14, 8))
    pygame.draw.polygon(s, (120, 76, 40), [(80, 66), (120, 66), (132, 106), (68, 106)])  # pump
    for y in range(72, 104, 6):
        pygame.draw.line(s, (86, 52, 28), (80 - (y - 66) // 4, y), (120 + (y - 66) // 4, y), 2)
    pygame.draw.polygon(s, (100, 62, 34), [(70, 110), (130, 110), (150, 150), (50, 150)])  # stock
    pygame.draw.polygon(s, SKIN, [(58, 150), (66, 94), (84, 88), (86, 150)])
    _hand(s, 64, 84, 26, 30)
    pygame.draw.polygon(s, SKIN, [(140, 150), (150, 126), (176, 126), (180, 150)])
    return s, (100, 16)


def _ak_vm():
    s = pygame.Surface((200, 160), pygame.SRCALPHA)
    pygame.draw.polygon(s, SLEEVE, [(124, 160), (200, 160), (190, 124), (140, 116)])
    pygame.draw.polygon(s, (36, 36, 40), [(97, 12), (103, 12), (110, 70), (90, 70)])  # barrel
    pygame.draw.polygon(s, (30, 30, 34), [(95, 2), (98, 2), (99, 16), (94, 16)])  # front sight post
    pygame.draw.polygon(s, (30, 30, 34), [(102, 2), (105, 2), (106, 16), (101, 16)])
    pygame.draw.polygon(s, (60, 60, 66), [(92, 28), (108, 28), (112, 56), (88, 56)])  # gas block
    pygame.draw.polygon(s, (150, 84, 36), [(84, 54), (116, 54), (128, 104), (72, 104)])  # handguard
    pygame.draw.line(s, (110, 58, 24), (86, 66), (114, 66), 2)
    pygame.draw.line(s, (110, 58, 24), (80, 84), (120, 84), 2)
    pygame.draw.polygon(s, (48, 48, 54), [(70, 104), (130, 104), (136, 132), (64, 132)])  # receiver
    pygame.draw.rect(s, (74, 74, 80), (70, 104, 60, 5))
    pygame.draw.polygon(s, (54, 40, 32), [(96, 132), (122, 132), (110, 160), (84, 160)])  # magazine
    pygame.draw.polygon(s, SKIN, [(60, 160), (70, 96), (86, 92), (90, 160)])
    _hand(s, 68, 88, 24, 28)
    pygame.draw.polygon(s, SKIN, [(142, 160), (152, 134), (178, 134), (182, 160)])
    return s, (100, 0)


def _machete_vm():
    s = pygame.Surface((170, 170), pygame.SRCALPHA)
    pygame.draw.polygon(s, SLEEVE, [(110, 170), (170, 170), (170, 140), (136, 136)])
    blade = [(112, 118), (124, 128), (58, 26), (34, 6), (46, 30)]
    pygame.draw.polygon(s, (168, 174, 180), blade)
    pygame.draw.line(s, (230, 236, 240), (122, 126), (36, 8), 2)
    pygame.draw.line(s, (110, 116, 122), (112, 118), (46, 30), 2)
    pygame.draw.polygon(s, (90, 170, 60), [(70, 50), (84, 62), (78, 70), (66, 58)])
    pygame.draw.circle(s, (90, 170, 60), (60, 44), 3)
    pygame.draw.line(s, (60, 60, 64), (104, 124), (132, 118), 6)  # guard
    pygame.draw.polygon(s, (30, 24, 20), [(116, 124), (128, 122), (150, 164), (136, 168)])  # handle
    _hand(s, 120, 130, 30, 30)
    return s, (60, 40)


def _chainsaw_vm(teeth_phase):
    s = pygame.Surface((210, 160), pygame.SRCALPHA)
    pygame.draw.polygon(s, SLEEVE, [(130, 160), (210, 160), (200, 128), (150, 120)])
    pygame.draw.polygon(s, (150, 154, 160), [(94, 14), (106, 14), (118, 96), (82, 96)])  # bar
    pygame.draw.ellipse(s, (150, 154, 160), (92, 6, 16, 16))
    pygame.draw.line(s, (100, 104, 110), (100, 20), (100, 94), 3)
    for i in range(12):
        t = (i + teeth_phase * 0.5) / 12
        y = 14 + t * 80
        wl = 6 + t * 12
        pygame.draw.rect(s, (40, 40, 44), (100 - wl - 2, int(y), 3, 3))
        pygame.draw.rect(s, (40, 40, 44), (100 + wl - 1, int(y), 3, 3))
    pygame.draw.polygon(s, (226, 110, 20), [(56, 96), (144, 96), (156, 160), (44, 160)])  # body
    pygame.draw.polygon(s, (180, 80, 10), [(56, 96), (144, 96), (146, 108), (54, 108)])
    pygame.draw.rect(s, (30, 30, 30), (70, 118, 60, 22), border_radius=4)
    for x in range(76, 126, 8):
        pygame.draw.line(s, (60, 60, 60), (x, 121), (x, 137), 2)
    pygame.draw.arc(s, (30, 30, 30), (60, 70, 80, 60), 0.3, math.pi - 0.3, 6)  # handle loop
    _hand(s, 66, 82, 26, 26)
    pygame.draw.polygon(s, SKIN, [(150, 160), (158, 134), (184, 134), (190, 160)])
    return s, (100, 8)


def _flamer_vm():
    s = pygame.Surface((210, 160), pygame.SRCALPHA)
    pygame.draw.polygon(s, SLEEVE, [(130, 160), (210, 160), (200, 128), (150, 120)])
    pygame.draw.ellipse(s, (160, 40, 30), (6, 96, 70, 90))  # fuel tank
    pygame.draw.ellipse(s, (210, 70, 50), (16, 104, 26, 40))
    pygame.draw.rect(s, (230, 190, 40), (6, 130, 70, 8))
    pygame.draw.polygon(s, (84, 86, 90), [(94, 22), (106, 22), (116, 104), (84, 104)])  # nozzle
    pygame.draw.polygon(s, (120, 122, 128), [(96, 22), (100, 22), (96, 104), (88, 104)])
    pygame.draw.rect(s, (50, 50, 54), (90, 16, 20, 10), border_radius=2)
    for y in (46, 66, 86):
        pygame.draw.line(s, (54, 56, 60), (88 - (y - 22) // 10, y), (112 + (y - 22) // 10, y), 3)
    pygame.draw.polygon(s, (60, 60, 64), [(70, 104), (130, 104), (140, 160), (60, 160)])
    pygame.draw.line(s, (40, 40, 40), (40, 110), (80, 130), 5)  # hose
    _hand(s, 76, 92, 26, 30)
    pygame.draw.polygon(s, SKIN, [(150, 160), (158, 134), (184, 134), (190, 160)])
    return s, (100, 14)


def _muzzle_flash(size, seed):
    rng = random.Random(seed)
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    for color, scale in (((255, 140, 30, 200), 1.0), ((255, 220, 90, 230), 0.62), ((255, 255, 220, 255), 0.3)):
        pts = []
        n = 14
        for i in range(n):
            a = i / n * 2 * math.pi
            r = c * scale * (1.0 if i % 2 == 0 else rng.uniform(0.35, 0.55))
            pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
        pygame.draw.polygon(s, color, pts)
    return s


# ---------------------------------------------------------------- glow sprites

_glow_cache = {}


def glow(color, radius):
    """Soft radial glow on black, meant to be blitted with BLEND_RGB_ADD."""
    r = max(1, min(72, int(radius)))
    key = (color, r)
    surf = _glow_cache.get(key)
    if surf is None:
        surf = pygame.Surface((r * 2, r * 2))
        surf.fill((0, 0, 0))
        steps = max(2, r)
        for i in range(steps, 0, -1):
            t = i / steps
            k = (1 - t) ** 1.6
            pygame.draw.circle(surf, tuple(_clamp(ch * k) for ch in color), (r, r), max(1, int(r * t)))
        _glow_cache[key] = surf
    return surf


# ---------------------------------------------------------------- bundle

class Art:
    def __init__(self):
        rng = random.Random(1337)
        raw = {
            FOREST: _forest_tex(rng),
            ROCK: _rock_tex(rng),
            CABIN: _cabin_tex(rng),
            FENCE: _fence_tex(rng),
        }
        self.walls = {k: _build_shaded(v.convert()) for k, v in raw.items()}
        self.sky = _sky_panorama(rng).convert()
        self.floor = _floor().convert()

        self.trees = {}
        for kind in TREE_STYLES:
            frames = [_zombie_tree(kind, f).convert_alpha() for f in range(3)]
            hurt = []
            burn = []
            for f in frames:
                h = f.copy()
                h.fill((140, 140, 140), special_flags=pygame.BLEND_RGB_ADD)
                hurt.append(h)
                b = f.copy()
                b.fill((90, 36, 0), special_flags=pygame.BLEND_RGB_ADD)
                burn.append(b)
            self.trees[kind] = {"normal": frames, "hurt": hurt, "burn": burn}
        self.corpses = {kind: _corpse(kind).convert_alpha() for kind in TREE_STYLES}
        self.pickups = {"ammo": _ammo_crate().convert_alpha(), "health": _health_kit().convert_alpha()}

        self.viewmodels = {
            "machete": _machete_vm(),
            "pistol": _pistol_vm(),
            "shotgun": _shotgun_vm(),
            "ak47": _ak_vm(),
            "chainsaw": _chainsaw_vm(0),
            "flamethrower": _flamer_vm(),
        }
        self.chainsaw_alt = _chainsaw_vm(1)
        self.viewmodels = {k: (s.convert_alpha(), m) for k, (s, m) in self.viewmodels.items()}
        self.chainsaw_alt = (self.chainsaw_alt[0].convert_alpha(), self.chainsaw_alt[1])
        self.flashes = [_muzzle_flash(56, i).convert_alpha() for i in range(3)]
        self.big_flashes = [_muzzle_flash(90, 10 + i).convert_alpha() for i in range(3)]
