import math
import random

import pygame

from .art import glow
from .settings import (COL_W, FOG_COLOR, FOG_DIST, FOG_LEVELS, FOV, NUM_RAYS, PLANE_LEN, PROJ, RENDER_H,
                       RENDER_W, TEX_SIZE)
from .weapons import SWITCH_TIME
from .world import cast_ray

HALF_W = RENDER_W / 2
HALF_H = RENDER_H // 2
FIRE_COLORS = ((255, 236, 150), (255, 170, 50), (235, 96, 24), (130, 44, 12))


class Renderer:
    def __init__(self, art):
        self.art = art
        self.surf = pygame.Surface((RENDER_W, RENDER_H)).convert()
        self.zbuf = [1e9] * NUM_RAYS
        self.pano_w = art.sky.get_width()

    def render(self, game, show_viewmodel=True):
        self._setup_camera(game.player)
        self._draw_background(game.player.angle)
        self._draw_walls(game.world)
        self._draw_sprites(game)
        self._draw_particles(game.particles)
        if show_viewmodel:
            self._draw_viewmodel(game)
        return self.surf

    # ------------------------------------------------------------ camera

    def _setup_camera(self, p):
        self.px, self.py = p.x, p.y
        self.dx, self.dy = math.cos(p.angle), math.sin(p.angle)
        self.plx, self.ply = -self.dy * PLANE_LEN, self.dx * PLANE_LEN
        self.inv_det = 1.0 / (self.plx * self.dy - self.dx * self.ply)

    def _project(self, wx, wy):
        rx, ry = wx - self.px, wy - self.py
        ty = self.inv_det * (-self.ply * rx + self.plx * ry)
        tx = self.inv_det * (self.dy * rx - self.dx * ry)
        return tx, ty

    # ------------------------------------------------------------ world

    def _draw_background(self, angle):
        left = angle - FOV / 2
        off = int(left / (2 * math.pi) * self.pano_w) % self.pano_w
        self.surf.blit(self.art.sky, (-off, 0))
        if self.pano_w - off < RENDER_W:
            self.surf.blit(self.art.sky, (self.pano_w - off, 0))
        self.surf.blit(self.art.floor, (0, HALF_H))

    def _draw_walls(self, world):
        grid = world.grid
        walls = self.art.walls
        zbuf = self.zbuf
        scale = pygame.transform.scale
        blit = self.surf.blit
        px, py, dx, dy, plx, ply = self.px, self.py, self.dx, self.dy, self.plx, self.ply
        tex_max = TEX_SIZE - 1
        fog_max = FOG_LEVELS - 1
        for i in range(NUM_RAYS):
            cam = 2.0 * (i + 0.5) / NUM_RAYS - 1.0
            rdx = dx + plx * cam
            rdy = dy + ply * cam
            dist, tile, side, wall_x = cast_ray(grid, px, py, rdx, rdy)
            if dist < 1e-3:
                dist = 1e-3
            zbuf[i] = dist
            tex_x = int(wall_x * TEX_SIZE)
            if (side == 0 and rdx > 0) or (side == 1 and rdy < 0):
                tex_x = tex_max - tex_x
            tex_x = 0 if tex_x < 0 else tex_max if tex_x > tex_max else tex_x
            lv = int(dist / FOG_DIST * FOG_LEVELS)
            tex = walls[tile][side][lv if lv < fog_max else fog_max]
            line_h = int(PROJ / dist)
            x = i * COL_W
            if line_h <= RENDER_H:
                if line_h < 1:
                    continue
                blit(scale(tex.subsurface((tex_x, 0, 1, TEX_SIZE)), (COL_W, line_h)), (x, HALF_H - line_h // 2))
            else:
                th = max(1, int(TEX_SIZE * RENDER_H / line_h))
                ty = (TEX_SIZE - th) // 2
                blit(scale(tex.subsurface((tex_x, ty, 1, th)), (COL_W, RENDER_H)), (x, 0))

    # ------------------------------------------------------------ sprites

    def draw_billboard(self, img, wx, wy, world_h, z_bottom=0.0, clip_floor=False, min_depth=0.12):
        tx, ty = self._project(wx, wy)
        if ty < min_depth:
            return
        sx = HALF_W * (1 + tx / ty)
        h = min(PROJ * world_h / ty, RENDER_H * 4)
        iw, ih = img.get_size()
        w = h * iw / ih
        if h < 1 or w < 1:
            return
        x0 = int(sx - w / 2)
        x1 = int(sx + w / 2)
        if x1 < 0 or x0 >= RENDER_W:
            return
        floor_y = HALF_H + PROJ * 0.5 / ty
        top = int(floor_y - PROJ * z_bottom / ty - h)

        zbuf = self.zbuf
        c0 = max(0, x0 // COL_W)
        c1 = min(NUM_RAYS - 1, x1 // COL_W)
        runs = []
        start = None
        for c in range(c0, c1 + 1):
            if ty < zbuf[c]:
                if start is None:
                    start = c
            elif start is not None:
                runs.append((start, c - 1))
                start = None
        if start is not None:
            runs.append((start, c1))
        if not runs:
            return

        sw, sh = max(1, x1 - x0), max(1, int(h))
        vis_h = sh
        if clip_floor:
            vis_h = min(sh, int(floor_y) - top)
            if vis_h <= 0:
                return
        scaled = pygame.transform.scale(img, (sw, sh))
        t = min(1.0, ty / FOG_DIST)
        if t > 0.05:
            m = int(255 * (1 - t))
            scaled.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
            scaled.fill(tuple(int(c * t) for c in FOG_COLOR), special_flags=pygame.BLEND_RGB_ADD)
        for a, b in runs:
            rx0 = max(a * COL_W, x0)
            rx1 = min((b + 1) * COL_W, x1)
            if rx1 > rx0:
                self.surf.blit(scaled, (rx0, top), (rx0 - x0, 0, rx1 - rx0, vis_h))

    def draw_glow(self, color, wx, wy, z, world_r):
        tx, ty = self._project(wx, wy)
        if ty < 0.1:
            return
        sx = HALF_W * (1 + tx / ty)
        c = int(sx) // COL_W
        if c < 0 or c >= NUM_RAYS or ty >= self.zbuf[c]:
            return
        sy = HALF_H + PROJ * (0.5 - z) / ty
        g = glow(color, PROJ * world_r / ty)
        r = g.get_width() // 2
        self.surf.blit(g, (int(sx) - r, int(sy) - r), special_flags=pygame.BLEND_RGB_ADD)

    def _draw_sprites(self, game):
        art = self.art
        px, py = self.px, self.py
        items = []
        for c in game.corpses:
            items.append(((c.x - px) ** 2 + (c.y - py) ** 2, 0, c))
        for pk in game.pickups:
            items.append(((pk.x - px) ** 2 + (pk.y - py) ** 2, 1, pk))
        for e in game.enemies:
            items.append(((e.x - px) ** 2 + (e.y - py) ** 2, 2, e))
        for s in game.projectiles:
            items.append(((s.x - px) ** 2 + (s.y - py) ** 2, 3, s))
        items.sort(key=lambda it: -it[0])
        t = game.time
        for _, typ, o in items:
            if typ == 0:
                sink = 0.0 if o.life > 1 else -(1 - o.life) * 0.35 * o.scale
                # Floor clutter right at the player's feet would fill the screen, so skip it up close.
                self.draw_billboard(art.corpses[o.kind], o.x, o.y, 0.3 * o.scale, sink, clip_floor=True, min_depth=0.8)
            elif typ == 1:
                if o.life < 5 and int(t * 8) % 2 == 0:
                    continue
                self.draw_billboard(art.pickups[o.kind], o.x, o.y, 0.28, 0.05 + 0.04 * math.sin(t * 3 + o.phase),
                                    min_depth=0.6)
            elif typ == 2:
                if o.state == "rising":
                    self.draw_billboard(o.image(art), o.x, o.y, o.height, -(1 - o.rise) * o.height, clip_floor=True)
                else:
                    bob = abs(math.sin(o.anim * math.pi)) * 0.03
                    self.draw_billboard(o.image(art), o.x, o.y, o.height, bob)
            else:
                self.draw_glow((80, 220, 50), o.x, o.y, 0.5, 0.18)
                self.draw_glow((200, 255, 160), o.x, o.y, 0.5, 0.06)

    def _draw_particles(self, particles):
        surf = self.surf
        zbuf = self.zbuf
        px, py, dx, dy, plx, ply, inv = self.px, self.py, self.dx, self.dy, self.plx, self.ply, self.inv_det
        for pt in particles:
            rx, ry = pt.x - px, pt.y - py
            ty = inv * (-ply * rx + plx * ry)
            if ty < 0.1:
                continue
            sx = HALF_W * (1 + inv * (dy * rx - dx * ry) / ty)
            c = int(sx) // COL_W
            if c < 0 or c >= NUM_RAYS or ty >= zbuf[c]:
                continue
            sy = HALF_H + PROJ * (0.5 - pt.z) / ty
            if pt.glow:
                age = 1 - pt.life / pt.max_life
                color = FIRE_COLORS[min(3, int(age * 4))]
                g = glow(color, PROJ * pt.size * (1 + age * 1.5) / ty)
                r = g.get_width() // 2
                surf.blit(g, (int(sx) - r, int(sy) - r), special_flags=pygame.BLEND_RGB_ADD)
            else:
                s = max(1, min(6, int(PROJ * pt.size / ty)))
                f = min(1.0, ty / FOG_DIST)
                col = tuple(int(pt.color[i] + (FOG_COLOR[i] - pt.color[i]) * f) for i in range(3))
                surf.fill(col, (int(sx) - s // 2, int(sy) - s // 2, s, s))

    # ------------------------------------------------------------ viewmodel

    def _draw_viewmodel(self, game):
        ars = game.arsenal
        p = game.player
        d = ars.current.defn
        key = d.key
        firing_saw = key == "chainsaw" and game.trigger_down and not ars.reloading
        if firing_saw and int(game.time * 30) % 2:
            img, (mx, my) = self.art.chainsaw_alt
        else:
            img, (mx, my) = self.art.viewmodels[key]
        iw, ih = img.get_size()

        if key == "machete":
            x = RENDER_W - iw + 6
        elif key == "pistol":
            x = HALF_W - mx + 40
        else:
            x = HALF_W - mx
        x += math.sin(p.bob) * 7 * p.move_amount
        y = RENDER_H - ih + 8 + abs(math.cos(p.bob)) * 6 * p.move_amount
        y += ars.recoil * 14
        if ars.switch_timer > 0:
            y += ars.switch_timer / SWITCH_TIME * ih
        if ars.reloading:
            y += math.sin(ars.reload_progress * math.pi) * ih * 0.6
        if firing_saw:
            x += random.randint(-2, 2)
            y += random.randint(-2, 2)

        if key == "machete" and ars.fire_anim < 0.32:
            s = math.sin(ars.fire_anim / 0.32 * math.pi)
            rot = pygame.transform.rotate(img, 40 * s)
            rw, rh = rot.get_size()
            self.surf.blit(rot, (x - 160 * s - (rw - iw) / 2, y - 30 * s - (rh - ih) / 2))
            return

        self.surf.blit(img, (x, y))
        if ars.flash > 0 and d.kind == "hitscan":
            flashes = self.art.big_flashes if key == "shotgun" else self.art.flashes
            fl = random.choice(flashes)
            self.surf.blit(fl, (x + mx - fl.get_width() / 2, y + my - fl.get_height() / 2))
            self.surf.fill((22, 18, 8), special_flags=pygame.BLEND_RGB_ADD)
        if key == "flamethrower" and not ars.reloading and ars.switch_timer <= 0:
            g = glow((110, 150, 255), 5 + random.random() * 2)
            r = g.get_width() // 2
            self.surf.blit(g, (x + mx - r, y + my - r), special_flags=pygame.BLEND_RGB_ADD)
