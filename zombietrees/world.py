import math
from collections import deque

EMPTY, FOREST, ROCK, CABIN, FENCE = 0, 1, 2, 3, 4

MAP_W = MAP_H = 34

NEIGH8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))

TREE_PILLARS = [
    (3, 12), (8, 15), (9, 3), (12, 29), (22, 30), (25, 14), (30, 21), (4, 21),
    (21, 4), (13, 6), (29, 10), (24, 20), (10, 19), (26, 26), (7, 30), (31, 6),
]

SPAWN_POINTS = [
    (2.5, 2.5), (31.5, 2.5), (2.5, 31.5), (31.5, 31.5),
    (17.5, 2.5), (17.5, 31.5), (2.5, 17.5), (31.5, 17.5),
    (10.5, 11.5), (23.5, 11.5),
]

PLAYER_START = (17.5, 26.5, -math.pi / 2)  # facing north, toward the cabin


def _build_grid():
    g = [[EMPTY] * MAP_W for _ in range(MAP_H)]

    for i in range(MAP_W):
        g[0][i] = g[MAP_H - 1][i] = FOREST
    for i in range(MAP_H):
        g[i][0] = g[i][MAP_W - 1] = FOREST

    def rect(x0, y0, x1, y1, t):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = t

    # Abandoned cabin in the middle with a door on the north and south walls.
    for x in range(14, 21):
        g[13][x] = CABIN
        g[18][x] = CABIN
    for y in range(13, 19):
        g[y][14] = CABIN
        g[y][20] = CABIN
    g[13][17] = EMPTY
    g[18][17] = EMPTY

    rect(5, 5, 6, 6, ROCK)
    rect(27, 5, 28, 6, ROCK)
    rect(5, 27, 6, 28, ROCK)
    rect(27, 27, 28, 28, ROCK)

    for x in range(8, 13):
        g[9][x] = FENCE
        g[24][x] = FENCE
    for x in range(21, 26):
        g[9][x] = FENCE
        g[24][x] = FENCE

    for x, y in TREE_PILLARS:
        g[y][x] = FOREST

    # Seal any floor pockets that can't be reached from the player start.
    sx, sy = int(PLAYER_START[0]), int(PLAYER_START[1])
    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in NEIGH8[:4]:
            nx, ny = x + dx, y + dy
            if g[ny][nx] == EMPTY and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    for y in range(MAP_H):
        for x in range(MAP_W):
            if g[y][x] == EMPTY and (x, y) not in seen:
                g[y][x] = FOREST
    return g


def cast_ray(grid, px, py, rdx, rdy):
    """DDA raycast. Returns (perpendicular distance, tile, side, wall_x)."""
    map_x, map_y = int(px), int(py)
    ddx = abs(1.0 / rdx) if rdx != 0 else 1e30
    ddy = abs(1.0 / rdy) if rdy != 0 else 1e30
    if rdx < 0:
        step_x = -1
        side_x = (px - map_x) * ddx
    else:
        step_x = 1
        side_x = (map_x + 1.0 - px) * ddx
    if rdy < 0:
        step_y = -1
        side_y = (py - map_y) * ddy
    else:
        step_y = 1
        side_y = (map_y + 1.0 - py) * ddy

    side = 0
    tile = 0
    while True:
        if side_x < side_y:
            side_x += ddx
            map_x += step_x
            side = 0
        else:
            side_y += ddy
            map_y += step_y
            side = 1
        tile = grid[map_y][map_x]
        if tile:
            break

    if side == 0:
        dist = side_x - ddx
        wall_x = py + dist * rdy
    else:
        dist = side_y - ddy
        wall_x = px + dist * rdx
    wall_x -= math.floor(wall_x)
    return dist, tile, side, wall_x


class World:
    def __init__(self):
        self.w, self.h = MAP_W, MAP_H
        self.grid = _build_grid()
        self.spawn_points = SPAWN_POINTS
        self.player_start = PLAYER_START
        self.flow = None
        self.flow_cell = None

    def is_wall(self, x, y):
        ix, iy = int(x), int(y)
        if ix < 0 or iy < 0 or ix >= self.w or iy >= self.h:
            return True
        return self.grid[iy][ix] != EMPTY

    def collides(self, x, y, r):
        return (self.is_wall(x - r, y - r) or self.is_wall(x + r, y - r)
                or self.is_wall(x - r, y + r) or self.is_wall(x + r, y + r))

    def move(self, x, y, dx, dy, r):
        """Slide-move a circle of radius r, resolving each axis separately."""
        if not self.collides(x + dx, y, r):
            x += dx
        if not self.collides(x, y + dy, r):
            y += dy
        return x, y

    def ray_distance(self, px, py, angle):
        return cast_ray(self.grid, px, py, math.cos(angle), math.sin(angle))[0]

    def line_of_sight(self, x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy)
        if d < 1e-6:
            return True
        wall = cast_ray(self.grid, x0, y0, dx / d, dy / d)[0]
        return wall > d

    def update_flow(self, px, py):
        """BFS distance field from the player's cell, used by enemies to path around walls."""
        cell = (int(px), int(py))
        if cell == self.flow_cell:
            return
        self.flow_cell = cell
        g = self.grid
        dist = [[-1] * self.w for _ in range(self.h)]
        cx, cy = cell
        dist[cy][cx] = 0
        q = deque([cell])
        while q:
            x, y = q.popleft()
            d = dist[y][x] + 1
            for dx, dy in NEIGH8:
                nx, ny = x + dx, y + dy
                if g[ny][nx] or dist[ny][nx] != -1:
                    continue
                if dx and dy and (g[y][nx] or g[ny][x]):
                    continue
                dist[ny][nx] = d
                q.append((nx, ny))
        self.flow = dist

    def next_waypoint(self, x, y):
        if self.flow is None:
            return None
        cx, cy = int(x), int(y)
        g = self.grid
        here = self.flow[cy][cx]
        best = None
        best_d = here if here >= 0 else 1 << 30
        for dx, dy in NEIGH8:
            nx, ny = cx + dx, cy + dy
            if g[ny][nx]:
                continue
            if dx and dy and (g[cy][nx] or g[ny][cx]):
                continue
            d = self.flow[ny][nx]
            if 0 <= d < best_d:
                best_d = d
                best = (nx + 0.5, ny + 0.5)
        return best
