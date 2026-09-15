"""Procedurally synthesized sound effects (no audio files needed).

If no audio device is available the game runs silently.
"""
import math
import random
from array import array

import pygame


class SoundBank:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self.loop_name = None
        self.rng = random.Random(99)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2, 512)
            self.freq, fmt, self.channels = pygame.mixer.get_init()
            formats = {-16: ("h", 32767, 0), 16: ("H", 32767, 32768), -8: ("b", 127, 0),
                       8: ("B", 127, 128), -32: ("i", 2147483647, 0), 32: ("f", 1.0, 0)}
            if fmt not in formats:
                return
            self.fmt = formats[fmt]
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(1)
            self.loop_ch = pygame.mixer.Channel(0)
            self._build()
            self.enabled = True
        except (pygame.error, OSError):
            self.enabled = False

    # ------------------------------------------------------------ playback

    def play(self, name, vol=1.0, pan=0.0):
        if not self.enabled:
            return
        ch = self.sounds[name].play()
        if ch:
            left = vol * min(1.0, 1.0 - pan * 0.8)
            right = vol * min(1.0, 1.0 + pan * 0.8)
            ch.set_volume(max(0.0, left), max(0.0, right))

    def play_at(self, name, listener, x, y, vol=1.0):
        dx, dy = x - listener.x, y - listener.y
        v = vol * max(0.0, 1.0 - math.hypot(dx, dy) / 20.0)
        if v > 0.02:
            self.play(name, v, math.sin(math.atan2(dy, dx) - listener.angle))

    def loop(self, name):
        if not self.enabled:
            return
        if self.loop_name != name or not self.loop_ch.get_busy():
            self.loop_ch.play(self.sounds[name], loops=-1)
            self.loop_name = name

    def stop_loop(self):
        if self.enabled and self.loop_name:
            self.loop_ch.stop()
            self.loop_name = None

    # ------------------------------------------------------------ synthesis

    def _to_sound(self, samples, vol):
        peak = max(1e-6, max(abs(v) for v in samples))
        k = vol / peak
        tc, scale, offset = self.fmt
        if tc == "f":
            mono = [v * k for v in samples]
        else:
            mono = [int(v * k * scale) + offset for v in samples]
        if self.channels > 1:
            data = [s for s in mono for _ in range(self.channels)]
        else:
            data = mono
        return pygame.mixer.Sound(buffer=array(tc, data).tobytes())

    def _noise_shot(self, dur, decay, lp, thump_f=0.0, thump_amp=0.0):
        sr = self.freq
        n = int(dur * sr)
        out = [0.0] * n
        y = 0.0
        uni = self.rng.uniform
        for i in range(n):
            t = i / sr
            y += lp * (uni(-1, 1) - y)
            v = y * math.exp(-t * decay) * 2.5
            if thump_amp:
                v += thump_amp * math.sin(2 * math.pi * thump_f * t * (1 - t * 0.8)) * math.exp(-t * decay * 0.7)
            out[i] = v
        return out

    def _tone(self, dur, f0, f1, wave="sine", decay=None, attack=0.005, vib=0.0, vib_f=0.0):
        sr = self.freq
        n = int(dur * sr)
        out = [0.0] * n
        phase = 0.0
        for i in range(n):
            t = i / sr
            f = f0 + (f1 - f0) * (t / dur)
            if vib:
                f += vib * math.sin(2 * math.pi * vib_f * t)
            phase += 2 * math.pi * f / sr
            if wave == "sine":
                v = math.sin(phase)
            elif wave == "square":
                v = 1.0 if math.sin(phase) > 0 else -1.0
            else:
                saw = (phase / (2 * math.pi)) % 1.0 * 2 - 1
                v = saw if wave == "saw" else 2 * abs(saw) - 1
            env = min(1.0, t / attack) if attack else 1.0
            env *= math.exp(-t * decay) if decay else (1 - t / dur)
            out[i] = v * env
        return out

    @staticmethod
    def _mix(a, b, gain_b=1.0):
        n = max(len(a), len(b))
        return [(a[i] if i < len(a) else 0.0) + (b[i] * gain_b if i < len(b) else 0.0) for i in range(n)]

    def _delay(self, samples, secs):
        return [0.0] * int(secs * self.freq) + samples

    def _whoosh(self, dur):
        sr = self.freq
        n = int(dur * sr)
        y = y2 = 0.0
        out = []
        for i in range(n):
            t = i / n
            y += 0.18 * (self.rng.uniform(-1, 1) - y)
            y2 += 0.3 * (y - y2)
            out.append((y - y2) * math.sin(math.pi * t) ** 2)
        return out

    def _chainsaw(self, dur):
        sr = self.freq
        out = []
        for i in range(int(dur * sr)):
            t = i / sr
            saw = (t * 100) % 1.0 * 2 - 1
            saw2 = (t * 150) % 1.0 * 2 - 1
            am = 0.7 + 0.3 * math.sin(2 * math.pi * 25 * t)
            out.append((saw * 0.6 + saw2 * 0.3 + self.rng.uniform(-0.25, 0.25)) * am)
        return out

    def _flame(self, dur):
        sr = self.freq
        out = []
        y = 0.0
        for i in range(int(dur * sr)):
            t = i / sr
            y += 0.12 * (self.rng.uniform(-1, 1) - y)
            out.append(y * (0.8 + 0.2 * math.sin(2 * math.pi * 5 * t)))
        return out

    def _growl(self, dur):
        sr = self.freq
        out = []
        y = 0.0
        phase = 0.0
        for i in range(int(dur * sr)):
            t = i / sr
            f = 58 + 14 * math.sin(2 * math.pi * 3 * t) + self.rng.uniform(-6, 6)
            phase += f / sr
            saw = phase % 1.0 * 2 - 1
            y += 0.25 * (saw + self.rng.uniform(-0.6, 0.6) - y)
            env = min(1.0, t / 0.08) * max(0.0, 1 - t / dur) ** 0.7
            out.append(y * env)
        return out

    def _death(self, dur):
        sr = self.freq
        out = []
        phase = 0.0
        y = 0.0
        for i in range(int(dur * sr)):
            t = i / sr
            f = 190 * (1 - t / dur) + 45
            phase += f / sr
            saw = phase % 1.0 * 2 - 1
            crackle = self.rng.uniform(-1, 1) if self.rng.random() < 0.04 else 0.0
            y += 0.3 * (saw * 0.7 + crackle - y)
            out.append(y * math.exp(-t * 3.5))
        return out

    def _build(self):
        S = self.sounds
        mk = self._to_sound
        S["pistol"] = mk(self._noise_shot(0.3, 15, 0.55, 150, 0.8), 0.5)
        S["shotgun"] = mk(self._noise_shot(0.6, 7, 0.32, 70, 1.1), 0.75)
        S["ak47"] = mk(self._noise_shot(0.18, 24, 0.6, 120, 0.7), 0.42)
        S["swing"] = mk(self._whoosh(0.26), 0.35)
        S["chop"] = mk(self._noise_shot(0.16, 28, 0.25, 110, 1.0), 0.5)
        S["hit"] = mk(self._mix(self._noise_shot(0.1, 40, 0.15), self._tone(0.1, 260, 120, decay=30)), 0.3)
        S["chainsaw"] = mk(self._chainsaw(0.4), 0.3)
        S["flame"] = mk(self._flame(0.6), 0.38)
        S["growl"] = mk(self._growl(0.8), 0.45)
        S["death"] = mk(self._death(0.8), 0.5)
        S["spit"] = mk(self._tone(0.25, 420, 140, decay=10, vib=60, vib_f=40), 0.3)
        S["splat"] = mk(self._noise_shot(0.2, 18, 0.12, 90, 0.6), 0.35)
        S["hurt"] = mk(self._mix(self._tone(0.3, 110, 60, decay=10), self._noise_shot(0.2, 20, 0.2), 0.5), 0.6)
        S["pickup"] = mk(self._tone(0.16, 520, 1100, "square", decay=12), 0.18)
        S["health"] = mk(self._mix(self._tone(0.12, 660, 660, "tri", decay=10),
                                   self._delay(self._tone(0.2, 990, 990, "tri", decay=10), 0.1)), 0.28)
        arp = []
        for i, f in enumerate((523, 659, 784, 1046)):
            arp = self._mix(arp, self._delay(self._tone(0.22, f, f, "tri", decay=9), i * 0.09))
        S["unlock"] = mk(arp, 0.4)
        horn = self._mix(self._tone(1.1, 110, 104, "saw", attack=0.12), self._tone(1.1, 165, 156, "saw", attack=0.12), 0.7)
        S["wave"] = mk(horn, 0.4)
        click = self._noise_shot(0.03, 120, 0.9)
        S["reload"] = mk(self._mix(click, self._delay(self._noise_shot(0.05, 80, 0.7, 300, 0.5), 0.22)), 0.35)
        S["empty"] = mk(self._noise_shot(0.04, 100, 0.95), 0.3)
