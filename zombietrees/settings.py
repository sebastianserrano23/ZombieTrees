import math
import os
import sys

TITLE = "Zombie Trees"

# Running inside a browser (pygbag/WebAssembly)? Python is slower there, so the
# web build casts fewer rays and keeps fewer particles alive.
WEB = sys.platform == "emscripten"

# Window vs. internal 3D render resolution (the 3D view is rendered small and
# scaled up for a chunky retro look and good performance in pure Python).
SCREEN_W, SCREEN_H = 960, 600
RENDER_W, RENDER_H = 480, 300
COL_W = 4 if WEB else 2
NUM_RAYS = RENDER_W // COL_W
FPS = 60

FOV = math.radians(66)
PLANE_LEN = math.tan(FOV / 2)
PROJ = (RENDER_W / 2) / PLANE_LEN

TEX_SIZE = 64
FOG_DIST = 15.0
FOG_LEVELS = 24
FOG_COLOR = (16, 22, 18)

MOUSE_SENS = 0.0022
TURN_SPEED = 2.6
WEB_TURN_RATE = 3.2  # radians/sec when steering with the cursor in the browser

PLAYER_MAX_HP = 100
PLAYER_SPEED = 3.3
PLAYER_SPRINT = 5.2
PLAYER_RADIUS = 0.25

MAX_PARTICLES = 150 if WEB else 260
MAX_CORPSES = 30

SAVE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "save.json")
