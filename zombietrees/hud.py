import math

import pygame

from .settings import SCREEN_H, SCREEN_W, WEB
from .weapons import SHORT_NAMES


def _font(size):
    try:
        return pygame.font.SysFont("impact,haettenschweiler,arialblack,arial", size)
    except (pygame.error, OSError):
        return pygame.font.Font(None, size)


def _body_font(size):
    try:
        return pygame.font.SysFont("helveticaneue,helvetica,arial", size)
    except (pygame.error, OSError):
        return pygame.font.Font(None, size)


MINIMAP_COLORS = {1: (40, 72, 40), 2: (110, 110, 112), 3: (124, 84, 52), 4: (140, 112, 72)}


class HUD:
    def __init__(self):
        self.f_huge = _font(100)
        self.f_big = _font(56)
        self.f_med = _font(34)
        self.f_small = _font(24)
        self.f_tiny = _font(17)
        self.body = _body_font(20)
        self.vignette = self._make_vignette((170, 0, 0))
        self.dark = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._panels = {}
        self._text_cache = {}
        self._minimap = None
        self._minimap_grid = None

    # ------------------------------------------------------------ helpers

    @staticmethod
    def _make_vignette(color):
        w, h = SCREEN_W // 4, SCREEN_H // 4
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w / 2, h / 2
        for y in range(h):
            for x in range(w):
                d = math.hypot((x - cx) / cx, (y - cy) / cy) / 1.414
                a = max(0.0, (d - 0.3) / 0.7)
                s.set_at((x, y), (*color, int(255 * min(1.0, a ** 1.4))))
        return pygame.transform.smoothscale(s, (SCREEN_W, SCREEN_H))

    def _render(self, txt, font, color):
        key = (txt, id(font), color)
        img = self._text_cache.get(key)
        if img is None:
            if len(self._text_cache) > 400:
                self._text_cache.clear()
            img = font.render(txt, True, color)
            self._text_cache[key] = img
        return img

    def text(self, surf, txt, font, color, pos, anchor="topleft", alpha=255, shadow=True):
        img = self._render(txt, font, color)
        rect = img.get_rect(**{anchor: pos})
        if shadow:
            sh = self._render(txt, font, (0, 0, 0))
            sh.set_alpha(int(alpha * 0.75))
            surf.blit(sh, rect.move(2, 3))
        img.set_alpha(alpha)
        surf.blit(img, rect)
        return rect

    def panel(self, surf, rect, alpha=140):
        key = (rect.w, rect.h, alpha)
        p = self._panels.get(key)
        if p is None:
            p = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            p.fill((0, 0, 0, alpha))
            self._panels[key] = p
        surf.blit(p, rect.topleft)

    def dim(self, surf, alpha, color=(0, 0, 0)):
        self.dark.fill((*color, alpha))
        surf.blit(self.dark, (0, 0))

    # ------------------------------------------------------------ in-game HUD

    def draw_play(self, screen, g):
        p = g.player
        ars = g.arsenal
        w = ars.current
        d = w.defn
        cx, cy = SCREEN_W // 2, SCREEN_H // 2

        if p.hurt_timer > 0:
            self.vignette.set_alpha(int(230 * min(1.0, p.hurt_timer / 0.45)))
            screen.blit(self.vignette, (0, 0))
        elif p.hp < 35:
            pulse = 0.5 + 0.5 * math.sin(g.time * 6)
            self.vignette.set_alpha(int(30 + (1 - p.hp / 35) * 130 * pulse))
            screen.blit(self.vignette, (0, 0))

        # Crosshair
        if d.kind == "melee":
            pygame.draw.circle(screen, (0, 0, 0), (cx, cy), 6, 3)
            pygame.draw.circle(screen, (240, 240, 240), (cx, cy), 5, 1)
        else:
            gap = 5 + int(d.spread * 150 + ars.recoil * 10)
            for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a = (cx + ux * gap, cy + uy * gap)
                b = (cx + ux * (gap + 9), cy + uy * (gap + 9))
                pygame.draw.line(screen, (0, 0, 0), a, b, 4)
                pygame.draw.line(screen, (240, 240, 240), a, b, 2)
        if g.hitmarker > 0:
            col = (255, 60, 40) if g.hitmarker_kill else (255, 255, 255)
            size = 11 if g.hitmarker_kill else 7
            for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                pygame.draw.line(screen, col, (cx + sx * 6, cy + sy * 6), (cx + sx * (6 + size), cy + sy * (6 + size)), 2)

        # Damage direction indicators
        for sx, sy, t in g.damage_dirs:
            rel = math.atan2(sy - p.y, sx - p.x) - p.angle
            ux, uy = math.sin(rel), -math.cos(rel)
            r = 120
            tip = (cx + ux * (r + 26), cy + uy * (r + 26))
            base = (cx + ux * r, cy + uy * r)
            half = 10 + 10 * t
            left = (base[0] - uy * half, base[1] + ux * half)
            right = (base[0] + uy * half, base[1] - ux * half)
            col = (int(120 + 135 * t), 20, 20)
            pygame.draw.polygon(screen, col, (tip, left, right))

        # Health
        rect = pygame.Rect(18, SCREEN_H - 104, 250, 86)
        self.panel(screen, rect)
        self.text(screen, "HEALTH", self.f_tiny, (200, 200, 190), (32, SCREEN_H - 98))
        frac = max(0.0, p.hp) / p.max_hp
        col = (80, 214, 96) if frac > 0.6 else (232, 200, 60) if frac > 0.3 else (232, 64, 50)
        bar = pygame.Rect(32, SCREEN_H - 54, 160, 22)
        pygame.draw.rect(screen, (40, 40, 40), bar)
        pygame.draw.rect(screen, col, (bar.x, bar.y, int(bar.w * frac), bar.h))
        pygame.draw.rect(screen, (0, 0, 0), bar, 2)
        self.text(screen, str(max(0, math.ceil(p.hp))), self.f_med, col, (256, SCREEN_H - 43), "midright")

        # Weapon & ammo
        rect = pygame.Rect(SCREEN_W - 268, SCREEN_H - 104, 250, 86)
        self.panel(screen, rect)
        self.text(screen, d.name.upper(), self.f_tiny, (200, 200, 190), (rect.x + 14, rect.y + 6))
        if d.mag:
            mag_col = (240, 70, 50) if w.mag == 0 else (245, 240, 220)
            r = self.text(screen, str(w.mag), self.f_big, mag_col, (rect.x + 14, rect.bottom + 6), "bottomleft")
            res_col = (240, 70, 50) if w.reserve == 0 else (180, 180, 170)
            self.text(screen, f"/ {w.reserve}", self.f_small, res_col, (r.right + 8, rect.bottom - 8), "bottomleft")
        else:
            self.text(screen, "MELEE", self.f_med, (245, 240, 220), (rect.x + 14, rect.bottom - 4), "bottomleft")
        if ars.reloading:
            rb = pygame.Rect(rect.x + 130, rect.y + 50, 104, 10)
            pygame.draw.rect(screen, (40, 40, 40), rb)
            pygame.draw.rect(screen, (240, 200, 70), (rb.x, rb.y, int(rb.w * ars.reload_progress), rb.h))
            self.text(screen, "RELOADING", self.f_tiny, (240, 200, 70), (rb.centerx, rb.y - 2), "midbottom")
        elif d.mag and w.mag == 0 and w.reserve == 0:
            self.text(screen, "NO AMMO", self.f_tiny, (240, 70, 50), (rect.right - 14, rect.y + 40), "topright")

        # Wave / score
        rect = pygame.Rect(18, 18, 240, 96)
        self.panel(screen, rect)
        self.text(screen, f"WAVE {max(1, g.wave)}", self.f_med, (232, 90, 60), (32, 22))
        if g.wave_state == "intermission":
            info = f"Next wave in {max(0, math.ceil(g.wave_timer))}"
        else:
            info = f"Trees left: {len(g.spawn_queue) + len(g.enemies)}"
        self.text(screen, info, self.f_small, (220, 220, 200), (32, 62))
        self.text(screen, f"Kills {g.kills}    Score {g.score}", self.f_tiny, (170, 200, 150), (32, 90))

        self._draw_slots(screen, g)
        self._draw_messages(screen, g)
        if g.show_minimap:
            self._draw_minimap(screen, g)

    def _draw_slots(self, screen, g):
        ars = g.arsenal
        n = len(ars.weapons)
        bw, bh, gap = 64, 38, 5
        total = n * bw + (n - 1) * gap
        x0 = (SCREEN_W - total) // 2
        y = SCREEN_H - 52
        for i, ws in enumerate(ars.weapons):
            r = pygame.Rect(x0 + i * (bw + gap), y, bw, bh)
            active = i == ars.index
            self.panel(screen, r, 170 if active else 120)
            if active:
                border = (240, 200, 70)
            elif ws.unlocked:
                border = (130, 130, 120)
            else:
                border = (60, 60, 60)
            pygame.draw.rect(screen, border, r, 2)
            self.text(screen, str(i + 1), self.f_tiny, border, (r.x + 5, r.y + 1), shadow=False)
            if ws.unlocked:
                self.text(screen, SHORT_NAMES[ws.defn.key], self.f_tiny, (230, 230, 220), (r.centerx, r.bottom - 1), "midbottom", shadow=False)
            else:
                self.text(screen, f"{ws.defn.unlock_kills} K", self.f_tiny, (110, 110, 100), (r.centerx, r.bottom - 1), "midbottom", shadow=False)

        nxt = ars.next_locked()
        if nxt:
            prev = ars.last_unlock_threshold()
            frac = max(0.0, min(1.0, (g.kills - prev) / max(1, nxt.unlock_kills - prev)))
            bar = pygame.Rect(x0, y - 9, total, 5)
            pygame.draw.rect(screen, (30, 30, 30), bar)
            pygame.draw.rect(screen, (240, 200, 70), (bar.x, bar.y, int(bar.w * frac), bar.h))
            self.text(screen, f"NEXT WEAPON: {nxt.name.upper()}   {g.kills} / {nxt.unlock_kills} KILLS",
                      self.f_tiny, (240, 220, 150), (SCREEN_W // 2, y - 11), "midbottom")

    def _draw_messages(self, screen, g):
        fonts = {"huge": self.f_huge, "big": self.f_big, "med": self.f_med, "small": self.f_small}
        y = 130
        for m in g.messages:
            alpha = 1.0
            if m.t < 0.15:
                alpha = m.t / 0.15
            remaining = m.dur - m.t
            if remaining < 0.5:
                alpha = min(alpha, remaining / 0.5)
            r = self.text(screen, m.text, fonts[m.size], m.color, (SCREEN_W // 2, y), "midtop", int(255 * max(0.0, alpha)))
            y += r.h + 2

    def _draw_minimap(self, screen, g):
        world = g.world
        cell = 5
        if self._minimap_grid is not world.grid:
            s = pygame.Surface((world.w * cell, world.h * cell), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            for y, row in enumerate(world.grid):
                for x, t in enumerate(row):
                    if t:
                        s.fill((*MINIMAP_COLORS[t], 230), (x * cell, y * cell, cell, cell))
            self._minimap = s
            self._minimap_grid = world.grid
        ox, oy = SCREEN_W - world.w * cell - 18, 18
        screen.blit(self._minimap, (ox, oy))
        for pk in g.pickups:
            col = (240, 220, 80) if pk.kind == "ammo" else (90, 230, 110)
            pygame.draw.rect(screen, col, (ox + pk.x * cell - 2, oy + pk.y * cell - 2, 4, 4))
        for e in g.enemies:
            col = (120, 60, 60) if e.state == "rising" else (255, 150, 30) if e.kind == "elder" else (235, 50, 40)
            pygame.draw.circle(screen, col, (ox + e.x * cell, oy + e.y * cell), 4 if e.kind == "elder" else 2)
        for s in g.projectiles:
            pygame.draw.circle(screen, (120, 255, 80), (ox + s.x * cell, oy + s.y * cell), 1)
        p = g.player
        px, py = ox + p.x * cell, oy + p.y * cell
        ca, sa = math.cos(p.angle), math.sin(p.angle)
        tri = [(px + ca * 7, py + sa * 7), (px - ca * 4 - sa * 4, py - sa * 4 + ca * 4), (px - ca * 4 + sa * 4, py - sa * 4 - ca * 4)]
        pygame.draw.polygon(screen, (255, 255, 255), tri)
        pygame.draw.rect(screen, (90, 90, 80), (ox, oy, world.w * cell, world.h * cell), 1)

    # ------------------------------------------------------------ screens

    def draw_menu(self, screen, g):
        self.dim(screen, 120)
        t = g.time
        y = 90 + math.sin(t * 1.5) * 4
        self.text(screen, "ZOMBIE TREES", self.f_huge, (132, 222, 72), (SCREEN_W // 2, y), "midtop")
        self.text(screen, "The forest woke up hungry. Chop, shoot and burn your way to survival.",
                  self.body, (220, 220, 200), (SCREEN_W // 2, 215), "midtop")
        if int(t * 2) % 2 == 0:
            self.text(screen, "CLICK OR PRESS ENTER TO START", self.f_med, (245, 220, 120), (SCREEN_W // 2, 280), "midtop")

        box = pygame.Rect(SCREEN_W // 2 - 360, 350, 720, 150)
        self.panel(screen, box, 150)
        lines = [
            ("WASD", "move"), ("SHIFT", "sprint"), ("MOUSE", "aim"), ("LEFT CLICK", "attack"),
            ("1-6 / WHEEL", "switch weapon"), ("Q", "last weapon"), ("R", "reload"), ("M", "minimap"),
            ("ESC", "pause"),
        ]
        if WEB:
            lines[2] = ("MOUSE", "steer left / right")
        for i, (k, v) in enumerate(lines):
            col, row = i % 3, i // 3
            x = box.x + (24, 250, 540)[col]
            yy = box.y + 18 + row * 42
            r = self.text(screen, k, self.f_small, (245, 220, 120), (x, yy))
            self.text(screen, v, self.body, (220, 220, 210), (r.right + 10, yy + 4))
        best = g.best
        self.text(screen, f"BEST: {best['score']} PTS   ·   WAVE {best['wave']}   ·   {best['kills']} KILLS",
                  self.f_small, (170, 200, 150), (SCREEN_W // 2, 525), "midtop")
        self.text(screen, "Kill trees to unlock: Shotgun · AK-47 · Chainsaw · Flamethrower",
                  self.body, (190, 190, 180), (SCREEN_W // 2, 562), "midtop")

    def draw_pause(self, screen, g):
        self.dim(screen, 150)
        self.text(screen, "PAUSED", self.f_huge, (240, 240, 230), (SCREEN_W // 2, 190), "midtop")
        self.text(screen, "Click or ESC to resume   ·   Q to quit to menu", self.body, (220, 220, 210),
                  (SCREEN_W // 2, 320), "midtop")

    def draw_gameover(self, screen, g):
        a = min(1.0, g.gameover_timer / 1.2)
        self.dim(screen, int(170 * a), (60, 0, 0))
        self.text(screen, "YOU BECAME FERTILIZER", self.f_big, (235, 70, 50), (SCREEN_W // 2, 150), "midtop", int(255 * a))
        self.text(screen, f"WAVE {g.wave}     KILLS {g.kills}     SCORE {g.score}", self.f_med, (240, 235, 220),
                  (SCREEN_W // 2, 250), "midtop", int(255 * a))
        if g.new_best:
            self.text(screen, "NEW HIGH SCORE!", self.f_med, (245, 210, 80), (SCREEN_W // 2, 305), "midtop", int(255 * a))
        else:
            self.text(screen, f"Best: {g.best['score']}", self.f_small, (200, 190, 170), (SCREEN_W // 2, 310), "midtop", int(255 * a))
        if g.gameover_timer > 1.2 and int(g.gameover_timer * 2) % 2 == 0:
            self.text(screen, "ENTER / CLICK TO PLAY AGAIN   ·   ESC FOR MENU", self.f_small, (245, 220, 120),
                      (SCREEN_W // 2, 400), "midtop")

    def draw_fps(self, screen, fps):
        self.text(screen, f"{fps:.0f} FPS", self.f_tiny, (200, 255, 200), (SCREEN_W // 2, 6), "midtop")
