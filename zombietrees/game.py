import asyncio
import json
import math
import random

import pygame

from .art import TREE_STYLES, Art
from .entities import Corpse, Enemy, Particle, Pickup, Player, Spit, wave_roster, wave_scaling
from .hud import HUD
from .renderer import Renderer
from .settings import (FPS, MAX_CORPSES, MAX_PARTICLES, MOUSE_SENS, PLAYER_RADIUS, SAVE_FILE, SCREEN_H,
                       SCREEN_W, TITLE, WEB, WEB_TURN_RATE)
from .sound import NullSound, SoundBank
from .weapons import WEAPONS, Arsenal
from .world import World, cast_ray

SAP = (96, 210, 60)
NEW_ENEMY_INTROS = {
    3: "THORNBACKS: fast and thorny",
    4: "SPITTERS: they spit sap from range. Keep moving!",
    5: "THE ELDERS HAVE AWOKEN",
}


def angle_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


class Message:
    def __init__(self, text, color, size, dur):
        self.text, self.color, self.size, self.dur = text, color, size, dur
        self.t = 0.0


class Game:
    def __init__(self):
        try:
            pygame.mixer.pre_init(22050, -16, 2, 512)
        except Exception:
            pass  # some builds (e.g. the browser) have no mixer; the game just runs silently
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.scaled = pygame.Surface((SCREEN_W, SCREEN_H)).convert()
        self.clock = pygame.time.Clock()
        self._loading_screen()

        self.art = Art()
        # Browsers refuse to start audio until the player interacts, so on web we
        # build the sound bank on the first click instead.
        self.sound = NullSound() if WEB else SoundBank()
        self.renderer = Renderer(self.art)
        self.hud = HUD()
        self.rng = random.Random()
        self.best = self._load_best()
        self.show_minimap = True
        self.show_fps = False
        self.running = True
        self.to_menu()

    # ------------------------------------------------------------ lifecycle

    def _loading_screen(self):
        self.screen.fill((8, 10, 8))
        font = pygame.font.Font(None, 40)
        img = font.render("Growing the forest...", True, (130, 210, 80))
        self.screen.blit(img, img.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2)))
        pygame.display.flip()

    def reset(self):
        self.world = World()
        sx, sy, sa = self.world.player_start
        self.player = Player(sx, sy, sa)
        self.arsenal = Arsenal()
        self.enemies = []
        self.projectiles = []
        self.pickups = []
        self.particles = []
        self.corpses = []
        self.messages = []
        self.damage_dirs = []
        self.wave = 0
        self.kills = 0
        self.score = 0
        self.wave_state = "intermission"
        self.wave_timer = 3.0
        self.spawn_queue = []
        self.spawn_timer = 0.0
        self.time = 0.0
        self.hitmarker = 0.0
        self.hitmarker_kill = False
        self.trigger_down = False
        self.trigger_pressed = False
        self.gameover_timer = 0.0
        self.new_best = False
        self.chop_cooldown = 0.0
        self.empty_cooldown = 0.0

    def to_menu(self):
        self.reset()
        self.state = "menu"
        self._set_grab(False)
        self.sound.stop_loop()
        # Camera slowly pans around the clearing with a few trees posing for the title screen.
        self.player.x, self.player.y = 17.5, 29.0
        for kind, x, y in (("rotwood", 16.2, 24.0), ("elder", 19.3, 22.5), ("sapling", 14.0, 26.0),
                           ("spitter", 22.0, 27.5), ("thornback", 12.0, 28.5)):
            e = Enemy(kind, x, y, 1, self.rng)
            e.state = "chase"
            e.rise = 1.0
            self.enemies.append(e)

    def start_game(self):
        if WEB and isinstance(self.sound, NullSound):
            self.sound = SoundBank()
        self.reset()
        self.state = "playing"
        self._set_grab(True)
        self.add_message("SURVIVE THE FOREST", (170, 230, 110), "big", 2.5)

    def pause(self):
        if self.state != "playing":
            return
        self.state = "paused"
        self.trigger_down = False
        self.sound.stop_loop()
        self._set_grab(False)

    def resume(self):
        self.state = "playing"
        self._set_grab(True)

    def game_over(self):
        self.state = "gameover"
        self.gameover_timer = 0.0
        self.trigger_down = False
        self.sound.stop_loop()
        self.sound.play("death")
        self._set_grab(False)
        if self.score > self.best["score"]:
            self.new_best = True
            self.best["score"] = self.score
        self.best["wave"] = max(self.best["wave"], self.wave)
        self.best["kills"] = max(self.best["kills"], self.kills)
        self._save_best()

    @staticmethod
    def _set_grab(on):
        if WEB:
            # No pointer lock in the browser build: the cursor stays visible and steers the view.
            pygame.mouse.set_visible(True)
            return
        pygame.event.set_grab(on)
        pygame.mouse.set_visible(not on)
        pygame.mouse.get_rel()

    @staticmethod
    def _look_turn(dt):
        """How far to turn this frame, in radians."""
        if not WEB:
            return pygame.mouse.get_rel()[0] * MOUSE_SENS
        off = pygame.mouse.get_pos()[0] - SCREEN_W / 2
        dead = 40
        if abs(off) <= dead:
            return 0.0
        span = SCREEN_W / 2 - dead
        steer = max(-1.0, min(1.0, (off - math.copysign(dead, off)) / span))
        return steer * WEB_TURN_RATE * dt

    def _load_best(self):
        try:
            with open(SAVE_FILE) as f:
                data = json.load(f)
            return {k: int(data.get(k, 0)) for k in ("score", "wave", "kills")}
        except (OSError, ValueError, AttributeError):
            return {"score": 0, "wave": 0, "kills": 0}

    def _save_best(self):
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(self.best, f)
        except OSError:
            pass

    # ------------------------------------------------------------ main loop

    async def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            if self.state == "playing":
                self.update_playing(dt)
            elif self.state == "menu":
                self.time += dt
                self.player.angle += dt * 0.12
                for e in self.enemies:
                    e.anim += dt * 1.2
            elif self.state == "gameover":
                self.gameover_timer += dt
                self.update_particles(dt)
            self.draw()
            await asyncio.sleep(0)  # hands control back to the browser each frame
        self.sound.stop_loop()
        pygame.quit()

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
                continue
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F3:
                self.show_fps = not self.show_fps
                continue
            click = ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
            if self.state == "menu":
                if click or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)):
                    self.start_game()
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    self.running = False
            elif self.state == "playing":
                self._handle_play_event(ev)
            elif self.state == "paused":
                if click or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    self.resume()
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                    self.to_menu()
            elif self.state == "gameover":
                if self.gameover_timer > 1.2:
                    if click or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)):
                        self.start_game()
                    elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                        self.to_menu()

    def _handle_play_event(self, ev):
        ars = self.arsenal
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.pause()
            elif pygame.K_1 <= ev.key <= pygame.K_6:
                idx = ev.key - pygame.K_1
                ws = ars.weapons[idx]
                if not ws.unlocked:
                    self.add_message(f"{ws.defn.name.upper()} UNLOCKS AT {ws.defn.unlock_kills} KILLS", (200, 190, 170), "small", 1.5)
                elif ars.switch(idx):
                    self.sound.stop_loop()
            elif ev.key == pygame.K_q:
                if ars.switch(ars.last_index):
                    self.sound.stop_loop()
            elif ev.key == pygame.K_r:
                if ars.start_reload():
                    self.sound.play("reload")
            elif ev.key in (pygame.K_m, pygame.K_TAB):
                self.show_minimap = not self.show_minimap
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.trigger_down = True
            self.trigger_pressed = True
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.trigger_down = False
        elif ev.type == pygame.MOUSEWHEEL and ev.y:
            if ars.cycle(-1 if ev.y > 0 else 1):
                self.sound.stop_loop()
        elif ev.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self.pause()

    # ------------------------------------------------------------ update

    def update_playing(self, dt):
        self.time += dt
        keys = pygame.key.get_pressed()
        p = self.player
        p.update(dt, keys, self.world, self._look_turn(dt))
        self.world.update_flow(p.x, p.y)
        self.arsenal.update(dt)
        self.update_weapon(dt)
        self.update_waves(dt)

        for e in self.enemies:
            if not e.dead:
                e.update(dt, self)
                if e.burn > 0 and self.rng.random() < dt * 18:
                    self.add_particle(e.x + self.rng.uniform(-0.2, 0.2), e.y + self.rng.uniform(-0.2, 0.2),
                                      self.rng.uniform(0.1, 0.8) * e.height, 0, 0, 1.2, 0.5, None, 0.06,
                                      gravity=-1.0, glow="fire")
        self.enemies = [e for e in self.enemies if not e.dead]
        self._separate()

        for s in self.projectiles:
            s.update(dt, self)
        self.projectiles = [s for s in self.projectiles if not s.dead]

        self.update_pickups(dt)
        self.update_particles(dt)
        for c in self.corpses:
            c.life -= dt
        self.corpses = [c for c in self.corpses if c.life > 0]

        self.hitmarker = max(0.0, self.hitmarker - dt)
        for m in self.messages:
            m.t += dt
        self.messages = [m for m in self.messages if m.t < m.dur]
        for d in self.damage_dirs:
            d[2] -= dt
        self.damage_dirs = [d for d in self.damage_dirs if d[2] > 0]

        if p.hp <= 0:
            self.game_over()

    def update_weapon(self, dt):
        ars = self.arsenal
        w = ars.current
        d = w.defn
        pressed = self.trigger_pressed
        self.trigger_pressed = False
        wants = self.trigger_down if d.auto else pressed
        self.chop_cooldown -= dt
        self.empty_cooldown -= dt

        if wants and ars.ready():
            if d.mag and w.mag <= 0:
                if w.reserve > 0:
                    if ars.start_reload():
                        self.sound.play("reload")
                elif self.empty_cooldown <= 0:
                    self.empty_cooldown = 0.5
                    self.sound.play("empty")
                    self.add_message("OUT OF AMMO - SWITCH WEAPONS", (240, 90, 60), "small", 1.2)
            else:
                if d.mag:
                    w.mag -= 1
                ars.on_fire()
                self.player.shake = max(self.player.shake, d.shake)
                if d.kind == "hitscan":
                    self.fire_hitscan(d)
                elif d.kind == "melee":
                    self.fire_melee(d)
                else:
                    self.fire_flame(d)
                if d.sound:
                    self.sound.play(d.sound)

        if (d.loop_sound and self.trigger_down and not ars.reloading and ars.switch_timer <= 0
                and (not d.mag or w.mag > 0)):
            self.sound.loop(d.loop_sound)
        else:
            self.sound.stop_loop()

        if d.mag and w.mag == 0 and w.reserve > 0 and ars.ready():
            if ars.start_reload():
                self.sound.play("reload")

    def fire_hitscan(self, d):
        p = self.player
        rng = self.rng
        hits = {}
        spread = d.spread * (1 + self.arsenal.recoil * 0.6)
        for _ in range(d.pellets):
            a = p.angle + rng.uniform(-spread, spread)
            rdx, rdy = math.cos(a), math.sin(a)
            wall = cast_ray(self.world.grid, p.x, p.y, rdx, rdy)[0]
            best = None
            best_t = min(wall, d.range)
            for e in self.enemies:
                if e.dead:
                    continue
                ex, ey = e.x - p.x, e.y - p.y
                t = ex * rdx + ey * rdy
                if t <= 0 or t >= best_t:
                    continue
                if ex * ex + ey * ey - t * t < e.radius * e.radius:
                    best, best_t = e, t
            if best:
                dmg = d.damage
                if d.falloff:
                    dmg *= max(0.35, 1 - best_t / d.falloff)
                prev = hits.get(best)
                hits[best] = ((prev[0] if prev else 0) + dmg, rdx, rdy)
                hx, hy = p.x + rdx * (best_t - best.radius * 0.5), p.y + rdy * (best_t - best.radius * 0.5)
                self.burst(hx, hy, rng.uniform(0.35, 0.8) * best.height, SAP, 4, speed=2.0)
            elif wall < d.range:
                wx, wy = p.x + rdx * (wall - 0.05), p.y + rdy * (wall - 0.05)
                self.burst(wx, wy, rng.uniform(0.3, 0.7), (130, 120, 100), 3, speed=1.5, life=0.4)
        for e, (dmg, rdx, rdy) in hits.items():
            self.damage_enemy(e, dmg, rdx, rdy, d.knockback)
        if hits:
            self.sound.play("hit", 0.7)

    def _targets_in_cone(self, d):
        p = self.player
        targets = []
        for e in self.enemies:
            if e.dead:
                continue
            dx, dy = e.x - p.x, e.y - p.y
            dist = math.hypot(dx, dy)
            if dist - e.radius > d.range:
                continue
            if dist > 0.05:
                if abs(angle_diff(math.atan2(dy, dx), p.angle)) > d.arc + math.atan2(e.radius, dist):
                    continue
                nx, ny = dx / dist, dy / dist
            else:
                nx, ny = math.cos(p.angle), math.sin(p.angle)
            if not self.world.line_of_sight(p.x, p.y, e.x, e.y):
                continue
            targets.append((dist, e, nx, ny))
        targets.sort(key=lambda t: t[0])
        return targets[:d.max_targets]

    def fire_melee(self, d):
        targets = self._targets_in_cone(d)
        for dist, e, nx, ny in targets:
            self.burst(e.x - nx * e.radius, e.y - ny * e.radius, 0.5 * e.height, SAP, 6 if d.key == "machete" else 3)
            self.damage_enemy(e, d.damage, nx, ny, d.knockback)
        if targets and self.chop_cooldown <= 0:
            self.chop_cooldown = 0.12
            self.sound.play("chop")
            self.player.shake = max(self.player.shake, 0.1)

    def fire_flame(self, d):
        p = self.player
        rng = self.rng
        ca, sa = math.cos(p.angle), math.sin(p.angle)
        for _ in range(3):
            a = p.angle + rng.uniform(-d.arc * 0.7, d.arc * 0.7)
            spd = rng.uniform(6.0, 8.0)
            self.add_particle(p.x + ca * 0.35, p.y + sa * 0.35, 0.32, math.cos(a) * spd, math.sin(a) * spd,
                              rng.uniform(0.2, 1.0), rng.uniform(0.35, 0.55), None, 0.07, gravity=-1.0, glow="fire")
        for dist, e, nx, ny in self._targets_in_cone(d):
            e.burn = max(e.burn, d.burn)
            self.damage_enemy(e, d.damage)

    def damage_enemy(self, e, amount, nx=0.0, ny=0.0, knockback=0.0, marker=True):
        if e.dead:
            return False
        e.hp -= amount
        e.hurt = 0.1
        if knockback:
            k = knockback * (1 - e.kb_resist)
            e.kb_x += nx * k
            e.kb_y += ny * k
        if marker:
            self.hitmarker = 0.18
            self.hitmarker_kill = False
        if e.hp <= 0:
            self.kill_enemy(e)
            return True
        return False

    def kill_enemy(self, e):
        e.dead = True
        self.kills += 1
        self.score += int(e.score * (1 + 0.15 * (self.wave - 1)))
        self.hitmarker = 0.3
        self.hitmarker_kill = True
        self.corpses.append(Corpse(e.kind, e.x, e.y, e.height))
        if len(self.corpses) > MAX_CORPSES:
            self.corpses.pop(0)
        self.burst(e.x, e.y, 0.5 * e.height, SAP, 14, speed=3.0)
        self.burst(e.x, e.y, 0.6 * e.height, TREE_STYLES[e.kind]["bark"], 10, speed=2.5, size=0.06)
        self.sound.play_at("death", self.player, e.x, e.y)

        r = self.rng.random()
        if e.kind == "elder":
            self.pickups.append(Pickup("ammo", e.x + 0.3, e.y, self.rng.random() * 6))
            self.pickups.append(Pickup("health", e.x - 0.3, e.y, self.rng.random() * 6))
        elif r < 0.25:
            self.pickups.append(Pickup("ammo", e.x, e.y, self.rng.random() * 6))
        elif r < 0.25 + (0.18 if self.player.hp < 50 else 0.08):
            self.pickups.append(Pickup("health", e.x, e.y, self.rng.random() * 6))

        for idx in self.arsenal.unlock_for_kills(self.kills):
            d = WEAPONS[idx]
            self.add_message(f"NEW WEAPON: {d.name.upper()}", (250, 210, 80), "big", 3.0)
            self.add_message(f"Equipped! (slot {idx + 1})", (240, 230, 200), "small", 3.0)
            self.sound.play("unlock")
            if self.arsenal.switch(idx):
                self.sound.stop_loop()

    def hurt_player(self, amount, sx, sy):
        p = self.player
        p.hp -= amount
        p.hurt_timer = 0.45
        p.shake = max(p.shake, 0.15 + amount / 60)
        self.damage_dirs.append([sx, sy, 1.0])
        if len(self.damage_dirs) > 6:
            self.damage_dirs.pop(0)
        self.sound.play("hurt", 0.8)

    def spawn_spit(self, e):
        p = self.player
        self.projectiles.append(Spit(e.x, e.y, p.x, p.y, e.damage))
        self.sound.play_at("spit", p, e.x, e.y)

    # ------------------------------------------------------------ waves

    def update_waves(self, dt):
        if self.wave_state == "intermission":
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.start_wave()
            return
        self.spawn_timer -= dt
        max_alive = min(26, 6 + self.wave * 2)
        if self.spawn_queue and self.spawn_timer <= 0 and len(self.enemies) < max_alive:
            self.spawn_enemy(self.spawn_queue.pop(0))
            self.spawn_timer = max(0.3, 1.5 - self.wave * 0.1)
        if not self.spawn_queue and not self.enemies:
            self.clear_wave()

    def start_wave(self):
        self.wave += 1
        self.wave_state = "active"
        self.spawn_queue = wave_roster(self.wave, self.rng)
        self.spawn_timer = 0.3
        self.add_message(f"WAVE {self.wave}", (232, 76, 52), "huge", 2.5)
        if self.wave > 1:
            hp, spd, _ = wave_scaling(self.wave)
            self.add_message(f"The trees grow stronger:  HP x{hp:.2f}   SPEED x{spd:.2f}", (220, 200, 170), "small", 3.0)
        if self.wave in NEW_ENEMY_INTROS:
            self.add_message(NEW_ENEMY_INTROS[self.wave], (200, 140, 255), "small", 3.5)
        self.sound.play("wave")

    def clear_wave(self):
        self.wave_state = "intermission"
        self.wave_timer = 6.0
        bonus = 250 * self.wave
        self.score += bonus
        p = self.player
        p.hp = min(p.max_hp, p.hp + 25)
        self.arsenal.add_ammo(0.5)
        self.add_message(f"WAVE {self.wave} CLEARED", (120, 230, 100), "big", 3.0)
        self.add_message(f"+{bonus} PTS   +25 HP   +AMMO", (230, 230, 210), "small", 3.0)
        self.sound.play("health")

    def spawn_enemy(self, kind):
        p = self.player
        w = self.world
        cands = [(math.hypot(sx - p.x, sy - p.y), sx, sy) for sx, sy in w.spawn_points]
        far = [c for c in cands if c[0] >= 9]
        if far:
            hidden = [c for c in far if not w.line_of_sight(p.x, p.y, c[1], c[2])]
            _, sx, sy = self.rng.choice(hidden or far)
        else:
            _, sx, sy = max(cands)
        for _ in range(6):
            jx, jy = sx + self.rng.uniform(-0.6, 0.6), sy + self.rng.uniform(-0.6, 0.6)
            if not w.collides(jx, jy, 0.4):
                sx, sy = jx, jy
                break
        self.enemies.append(Enemy(kind, sx, sy, self.wave, self.rng))
        self.burst(sx, sy, 0.05, (70, 56, 40), 12, speed=1.5, up=3.0)

    def _separate(self):
        es = self.enemies
        w = self.world
        p = self.player
        n = len(es)
        for i in range(n):
            a = es[i]
            for j in range(i + 1, n):
                b = es[j]
                dx, dy = b.x - a.x, b.y - a.y
                md = a.radius + b.radius
                d2 = dx * dx + dy * dy
                if d2 < md * md:
                    d = math.sqrt(d2)
                    if d < 1e-4:
                        dx, dy, d = 1.0, 0.0, 1.0
                    push = (md - min(d, md)) * 0.5
                    nx, ny = dx / d, dy / d
                    a.x, a.y = w.move(a.x, a.y, -nx * push, -ny * push, a.coll_r)
                    b.x, b.y = w.move(b.x, b.y, nx * push, ny * push, b.coll_r)
            dx, dy = a.x - p.x, a.y - p.y
            md = a.radius + PLAYER_RADIUS
            d2 = dx * dx + dy * dy
            if d2 < md * md:
                d = math.sqrt(d2) or 1e-4
                push = md - d
                a.x, a.y = w.move(a.x, a.y, dx / d * push, dy / d * push, a.coll_r)

    # ------------------------------------------------------------ misc updates

    def update_pickups(self, dt):
        p = self.player
        keep = []
        for pk in self.pickups:
            pk.life -= dt
            if pk.life <= 0:
                continue
            if math.hypot(pk.x - p.x, pk.y - p.y) < 1.0:
                if pk.kind == "health":
                    if p.hp < p.max_hp:
                        p.hp = min(p.max_hp, p.hp + 25)
                        self.sound.play("health")
                        self.add_message("+25 HEALTH", (100, 230, 120), "small", 1.2)
                        continue
                else:
                    self.arsenal.add_ammo(1.0)
                    self.sound.play("pickup")
                    self.add_message("+AMMO", (240, 220, 100), "small", 1.2)
                    continue
            keep.append(pk)
        self.pickups = keep

    def update_particles(self, dt):
        w = self.world
        keep = []
        for pt in self.particles:
            pt.life -= dt
            if pt.life <= 0:
                continue
            pt.vz -= pt.gravity * dt
            nx, ny = pt.x + pt.vx * dt, pt.y + pt.vy * dt
            if w.is_wall(nx, ny):
                if pt.glow:
                    continue
                pt.vx *= -0.3
                pt.vy *= -0.3
            else:
                pt.x, pt.y = nx, ny
            pt.z += pt.vz * dt
            if pt.z < 0:
                pt.z = 0.0
                pt.vz *= -0.3
                pt.vx *= 0.6
                pt.vy *= 0.6
            keep.append(pt)
        self.particles = keep

    def add_particle(self, x, y, z, vx, vy, vz, life, color, size, gravity=9.0, glow=None):
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(Particle(x, y, z, vx, vy, vz, life, color, size, gravity, glow))

    def burst(self, x, y, z, color, count, speed=2.5, life=0.7, size=0.04, up=1.5):
        rng = self.rng
        for _ in range(count):
            a = rng.uniform(0, 2 * math.pi)
            s = rng.uniform(0.3, 1.0) * speed
            self.add_particle(x, y, z, math.cos(a) * s, math.sin(a) * s, rng.uniform(0.2, 1.0) * up * speed / 2,
                              rng.uniform(0.5, 1.0) * life, color, size * rng.uniform(0.6, 1.4))

    def add_message(self, text, color, size, dur):
        self.messages = [m for m in self.messages if m.text != text]
        self.messages.append(Message(text, color, size, dur))
        if len(self.messages) > 4:
            self.messages.pop(0)

    # ------------------------------------------------------------ draw

    def draw(self):
        show_vm = self.state in ("playing", "paused")
        surf = self.renderer.render(self, show_vm)
        pygame.transform.scale(surf, (SCREEN_W, SCREEN_H), self.scaled)
        ox = oy = 0
        if self.state == "playing" and self.player.shake > 0:
            mag = self.player.shake * 14
            ox, oy = int(self.rng.uniform(-mag, mag)), int(self.rng.uniform(-mag, mag))
            self.screen.fill((0, 0, 0))
        self.screen.blit(self.scaled, (ox, oy))

        if self.state == "playing":
            self.hud.draw_play(self.screen, self)
        elif self.state == "paused":
            self.hud.draw_play(self.screen, self)
            self.hud.draw_pause(self.screen, self)
        elif self.state == "menu":
            self.hud.draw_menu(self.screen, self)
        elif self.state == "gameover":
            self.hud.draw_gameover(self.screen, self)
        if self.show_fps:
            self.hud.draw_fps(self.screen, self.clock.get_fps())
        pygame.display.flip()
