import math

import pygame

from .settings import PLAYER_MAX_HP, PLAYER_RADIUS, PLAYER_SPEED, PLAYER_SPRINT, TURN_SPEED

RISE_TIME = 0.9
BURN_DPS = 14.0

ENEMY_TYPES = {
    "sapling": dict(name="Sapling", hp=26, speed=2.4, damage=5, radius=0.26, height=0.72,
                    reach=0.55, cooldown=0.9, windup=0.28, score=50, kb_resist=0.0),
    "rotwood": dict(name="Rotwood", hp=46, speed=1.45, damage=9, radius=0.33, height=1.05,
                    reach=0.6, cooldown=1.1, windup=0.4, score=100, kb_resist=0.2),
    "thornback": dict(name="Thornback", hp=80, speed=2.3, damage=13, radius=0.33, height=1.0,
                      reach=0.65, cooldown=0.9, windup=0.32, score=175, kb_resist=0.35),
    "spitter": dict(name="Spitter", hp=58, speed=1.25, damage=8, radius=0.35, height=1.1,
                    reach=0.6, cooldown=2.3, windup=0.5, score=200, kb_resist=0.2, ranged=True),
    "elder": dict(name="Elder", hp=450, speed=0.95, damage=26, radius=0.52, height=1.6,
                  reach=0.8, cooldown=1.4, windup=0.6, score=900, kb_resist=0.85),
}


def wave_scaling(wave):
    """(hp, speed, damage) multipliers: trees get tougher, faster and meaner every wave."""
    w = wave - 1
    return 1.0 + 0.22 * w, min(1.0 + 0.06 * w, 1.9), 1.0 + 0.1 * w


def wave_roster(wave, rng):
    count = 5 + 3 * (wave - 1)
    weights = {"sapling": max(1, 6 - wave), "rotwood": 5}
    if wave >= 3:
        weights["thornback"] = min(5, wave - 1)
    if wave >= 4:
        weights["spitter"] = min(4, wave - 2)
    kinds = list(weights)
    roster = rng.choices(kinds, weights=[weights[k] for k in kinds], k=count)
    if wave >= 5:
        # Elders show up in the back half of the wave.
        for _ in range(1 + (wave - 5) // 3):
            roster.insert(rng.randint(len(roster) // 2, len(roster)), "elder")
    return roster


class Player:
    def __init__(self, x, y, angle):
        self.x, self.y, self.angle = x, y, angle
        self.max_hp = PLAYER_MAX_HP
        self.hp = PLAYER_MAX_HP
        self.bob = 0.0
        self.move_amount = 0.0
        self.hurt_timer = 0.0
        self.shake = 0.0

    def update(self, dt, keys, world, turn):
        self.angle += turn  # radians already; the game decides mouse vs. cursor steering
        if keys[pygame.K_LEFT]:
            self.angle -= TURN_SPEED * dt
        if keys[pygame.K_RIGHT]:
            self.angle += TURN_SPEED * dt
        self.angle %= 2 * math.pi

        ca, sa = math.cos(self.angle), math.sin(self.angle)
        fx = fy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            fx += ca
            fy += sa
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            fx -= ca
            fy -= sa
        if keys[pygame.K_d]:
            fx -= sa
            fy += ca
        if keys[pygame.K_a]:
            fx += sa
            fy -= ca
        length = math.hypot(fx, fy)
        moving = length > 0
        if moving:
            sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            speed = PLAYER_SPRINT if sprint else PLAYER_SPEED
            self.x, self.y = world.move(self.x, self.y, fx / length * speed * dt, fy / length * speed * dt, PLAYER_RADIUS)
            self.bob += dt * (11 if sprint else 8)
        target = 1.0 if moving else 0.0
        self.move_amount += (target - self.move_amount) * min(1.0, dt * 8)
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.shake = max(0.0, self.shake - dt)


class Enemy:
    def __init__(self, kind, x, y, wave, rng):
        t = ENEMY_TYPES[kind]
        hp_m, spd_m, dmg_m = wave_scaling(wave)
        self.kind = kind
        self.x, self.y = x, y
        self.max_hp = t["hp"] * hp_m
        self.hp = self.max_hp
        self.speed = t["speed"] * spd_m * rng.uniform(0.9, 1.1)
        self.damage = t["damage"] * dmg_m
        self.radius = t["radius"]
        self.coll_r = min(self.radius, 0.38)
        self.height = t["height"]
        self.attack_range = self.radius + PLAYER_RADIUS + t["reach"]
        self.cooldown = t["cooldown"]
        self.windup_time = t["windup"]
        self.ranged = t.get("ranged", False)
        self.kb_resist = t["kb_resist"]
        self.score = t["score"]
        self.rng = rng

        self.state = "rising"
        self.rise = 0.0
        self.attack_timer = rng.uniform(0.3, 0.8)
        self.windup = 0.0
        self.hurt = 0.0
        self.burn = 0.0
        self.burn_tick = 0.0
        self.kb_x = self.kb_y = 0.0
        self.anim = rng.random() * 2
        self.los = False
        self.los_timer = rng.random() * 0.3
        self.detour = 0.0
        self.chase_timer = 0.0
        self.growl_timer = rng.uniform(1.5, 6.0)
        self.strafe = rng.choice((-1, 1))
        self.dead = False

    def image(self, art):
        variants = art.trees[self.kind]
        if self.hurt > 0:
            frames = variants["hurt"]
        elif self.burn > 0:
            frames = variants["burn"]
        else:
            frames = variants["normal"]
        if self.windup > 0:
            return frames[2]
        return frames[int(self.anim * 2) % 2]

    def update(self, dt, g):
        if self.hurt > 0:
            self.hurt -= dt
        if self.burn > 0:
            self.burn -= dt
            self.burn_tick -= dt
            if self.burn_tick <= 0:
                self.burn_tick = 0.25
                if g.damage_enemy(self, BURN_DPS * 0.25, marker=False):
                    return
        if self.state == "rising":
            self.rise += dt / RISE_TIME
            if self.rise >= 1.0:
                self.rise = 1.0
                self.state = "chase"
            return

        p, w = g.player, g.world
        dx, dy = p.x - self.x, p.y - self.y
        dist = math.hypot(dx, dy) or 1e-6

        self.los_timer -= dt
        if self.los_timer <= 0:
            self.los_timer = 0.2
            self.los = w.line_of_sight(self.x, self.y, p.x, p.y)

        if self.kb_x or self.kb_y:
            self.x, self.y = w.move(self.x, self.y, self.kb_x * dt, self.kb_y * dt, self.coll_r)
            decay = max(0.0, 1.0 - 7.0 * dt)
            self.kb_x *= decay
            self.kb_y *= decay
            if abs(self.kb_x) + abs(self.kb_y) < 0.05:
                self.kb_x = self.kb_y = 0.0

        self.growl_timer -= dt
        if self.growl_timer <= 0:
            self.growl_timer = self.rng.uniform(4.0, 9.0)
            g.sound.play_at("growl", p, self.x, self.y, 0.7)

        if self.windup > 0:
            self.windup -= dt
            if self.windup <= 0:
                if self.ranged:
                    g.spawn_spit(self)
                elif dist <= self.attack_range + 0.3 and self.los:
                    g.hurt_player(self.damage, self.x, self.y)
            return

        self.attack_timer -= dt
        self.chase_timer = max(0.0, self.chase_timer - dt)
        mx = my = 0.0
        if self.ranged and self.los and dist < 11 and self.chase_timer <= 0:
            if self.attack_timer <= 0:
                self.windup = self.windup_time
                self.attack_timer = self.cooldown
                return
            if dist > 6.5:
                mx, my = dx / dist, dy / dist
            elif dist < 3.5:
                mx, my = -dx / dist, -dy / dist
            else:
                mx = (-dy * self.strafe * 0.6 + dx * 0.2) / dist
                my = (dx * self.strafe * 0.6 + dy * 0.2) / dist
        elif not self.ranged and dist <= self.attack_range and self.los:
            if self.attack_timer <= 0:
                self.windup = self.windup_time
                self.attack_timer = self.cooldown
            return
        else:
            if self.ranged and not self.los:
                # Commit to closing in for a moment so spitters don't dither on the edge of sight.
                self.chase_timer = 1.2
            tx, ty = p.x, p.y
            if not self.los or self.detour > 0:
                wp = w.next_waypoint(self.x, self.y)
                if wp:
                    tx, ty = wp
            self.detour = max(0.0, self.detour - dt)
            vx, vy = tx - self.x, ty - self.y
            length = math.hypot(vx, vy)
            if length > 1e-4:
                mx, my = vx / length, vy / length

        if mx or my:
            step = self.speed * dt
            ox, oy = self.x, self.y
            self.x, self.y = w.move(self.x, self.y, mx * step, my * step, self.coll_r)
            if math.hypot(self.x - ox, self.y - oy) < step * 0.3:
                # Snagged on a corner: follow the path field for a moment.
                self.detour = 0.8
                self.strafe *= -1
            self.anim += dt * self.speed * 1.3


class Spit:
    SPEED = 7.0

    def __init__(self, x, y, tx, ty, damage):
        dx, dy = tx - x, ty - y
        d = math.hypot(dx, dy) or 1.0
        self.x, self.y = x + dx / d * 0.4, y + dy / d * 0.4
        self.vx, self.vy = dx / d * self.SPEED, dy / d * self.SPEED
        self.damage = damage
        self.life = 3.0
        self.dead = False

    def update(self, dt, g):
        self.life -= dt
        if self.life <= 0:
            self.dead = True
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if g.world.is_wall(self.x, self.y):
            self.dead = True
            g.burst(self.x - self.vx * dt, self.y - self.vy * dt, 0.5, (90, 220, 60), 8)
            return
        p = g.player
        if math.hypot(p.x - self.x, p.y - self.y) < PLAYER_RADIUS + 0.22:
            self.dead = True
            g.hurt_player(self.damage, self.x - self.vx, self.y - self.vy)
            g.sound.play("splat")


class Pickup:
    def __init__(self, kind, x, y, phase):
        self.kind = kind
        self.x, self.y = x, y
        self.life = 30.0
        self.phase = phase


class Corpse:
    def __init__(self, kind, x, y, scale):
        self.kind = kind
        self.x, self.y = x, y
        self.scale = scale
        self.life = 10.0


class Particle:
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "life", "max_life", "color", "size", "gravity", "glow")

    def __init__(self, x, y, z, vx, vy, vz, life, color, size, gravity=9.0, glow=None):
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy, self.vz = vx, vy, vz
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity
        self.glow = glow
