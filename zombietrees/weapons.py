from dataclasses import dataclass

SWITCH_TIME = 0.28


@dataclass(frozen=True)
class WeaponDef:
    key: str
    name: str
    kind: str              # "melee", "hitscan" or "flame"
    damage: float
    cooldown: float
    auto: bool
    unlock_kills: int = 0
    pellets: int = 1
    spread: float = 0.0    # radians, +/- per shot
    range: float = 30.0
    arc: float = 0.0       # half-angle for melee / flame cones
    max_targets: int = 1
    mag: int = 0           # 0 = no ammo needed
    reload_time: float = 0.0
    start_reserve: int = 0
    max_reserve: int = 0
    pickup_ammo: int = 0
    knockback: float = 0.0
    falloff: float = 0.0   # distance over which damage drops off (0 = none)
    burn: float = 0.0      # seconds of burning applied
    shake: float = 0.0
    recoil: float = 0.0
    sound: str = ""
    loop_sound: str = ""


WEAPONS = (
    WeaponDef("machete", "Machete", "melee", damage=38, cooldown=0.5, auto=True,
              range=1.35, arc=0.7, max_targets=2, knockback=2.5, shake=0.06, sound="swing"),
    WeaponDef("pistol", "Pistol", "hitscan", damage=24, cooldown=0.26, auto=False,
              spread=0.01, mag=12, reload_time=1.1, start_reserve=60, max_reserve=144, pickup_ammo=24,
              knockback=0.8, shake=0.05, recoil=0.5, sound="pistol"),
    WeaponDef("shotgun", "Shotgun", "hitscan", damage=14, cooldown=0.82, auto=False, unlock_kills=12,
              pellets=9, spread=0.085, range=22, mag=6, reload_time=1.6, start_reserve=24, max_reserve=60,
              pickup_ammo=10, knockback=0.6, falloff=12, shake=0.22, recoil=1.0, sound="shotgun"),
    WeaponDef("ak47", "AK-47", "hitscan", damage=21, cooldown=0.1, auto=True, unlock_kills=30,
              spread=0.028, mag=30, reload_time=1.9, start_reserve=120, max_reserve=300, pickup_ammo=45,
              knockback=0.35, shake=0.07, recoil=0.45, sound="ak47"),
    WeaponDef("chainsaw", "Chainsaw", "melee", damage=15, cooldown=0.08, auto=True, unlock_kills=55,
              range=1.45, arc=0.55, max_targets=3, knockback=0.3, shake=0.04, loop_sound="chainsaw"),
    WeaponDef("flamethrower", "Flamethrower", "flame", damage=6, cooldown=0.06, auto=True, unlock_kills=85,
              range=5.5, arc=0.22, max_targets=99, mag=100, reload_time=2.2, start_reserve=200, max_reserve=500,
              pickup_ammo=80, burn=3.0, shake=0.02, loop_sound="flame"),
)

SHORT_NAMES = {"machete": "MACHETE", "pistol": "PISTOL", "shotgun": "SHOTGUN",
               "ak47": "AK-47", "chainsaw": "CHAINSAW", "flamethrower": "FLAMER"}


class WeaponState:
    def __init__(self, defn):
        self.defn = defn
        self.unlocked = defn.unlock_kills == 0
        self.mag = defn.mag
        self.reserve = defn.start_reserve if self.unlocked else 0


class Arsenal:
    def __init__(self):
        self.weapons = [WeaponState(d) for d in WEAPONS]
        self.index = 1  # start with the pistol out
        self.last_index = 0
        self.cooldown = 0.0
        self.reload_timer = 0.0
        self.switch_timer = SWITCH_TIME
        self.fire_anim = 9.0
        self.recoil = 0.0
        self.flash = 0.0

    @property
    def current(self):
        return self.weapons[self.index]

    @property
    def reloading(self):
        return self.reload_timer > 0

    @property
    def reload_progress(self):
        rt = self.current.defn.reload_time
        return 1.0 - self.reload_timer / rt if rt else 1.0

    def update(self, dt):
        self.cooldown = max(0.0, self.cooldown - dt)
        self.switch_timer = max(0.0, self.switch_timer - dt)
        self.recoil = max(0.0, self.recoil - dt * 4)
        self.flash -= dt
        self.fire_anim += dt
        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reload_timer = 0.0
                w = self.current
                take = min(w.defn.mag - w.mag, w.reserve)
                w.mag += take
                w.reserve -= take

    def ready(self):
        return self.cooldown <= 0 and self.switch_timer <= 0 and self.reload_timer <= 0

    def switch(self, index):
        if index == self.index or not 0 <= index < len(self.weapons) or not self.weapons[index].unlocked:
            return False
        self.last_index = self.index
        self.index = index
        self.switch_timer = SWITCH_TIME
        self.reload_timer = 0.0
        self.fire_anim = 9.0
        return True

    def cycle(self, step):
        i = self.index
        for _ in range(len(self.weapons)):
            i = (i + step) % len(self.weapons)
            if self.weapons[i].unlocked:
                return self.switch(i)
        return False

    def start_reload(self):
        w = self.current
        if (w.defn.mag and w.mag < w.defn.mag and w.reserve > 0
                and self.reload_timer <= 0 and self.switch_timer <= 0):
            self.reload_timer = w.defn.reload_time
            return True
        return False

    def on_fire(self):
        d = self.current.defn
        self.cooldown = d.cooldown
        self.fire_anim = 0.0
        self.recoil = min(1.5, self.recoil + d.recoil)
        if d.kind == "hitscan":
            self.flash = 0.05

    def unlock_for_kills(self, kills):
        newly = []
        for i, w in enumerate(self.weapons):
            if not w.unlocked and kills >= w.defn.unlock_kills:
                w.unlocked = True
                w.mag = w.defn.mag
                w.reserve = w.defn.start_reserve
                newly.append(i)
        return newly

    def next_locked(self):
        locked = [w.defn for w in self.weapons if not w.unlocked]
        return min(locked, key=lambda d: d.unlock_kills) if locked else None

    def last_unlock_threshold(self):
        return max((w.defn.unlock_kills for w in self.weapons if w.unlocked), default=0)

    def add_ammo(self, fraction=1.0):
        for w in self.weapons:
            if w.unlocked and w.defn.mag:
                w.reserve = min(w.defn.max_reserve, w.reserve + int(w.defn.pickup_ammo * fraction))
