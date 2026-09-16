# Zombie Trees

A retro first-person shooter built with Python and pygame. The forest has turned. Survive endless waves of
zombie trees that get tougher, faster and meaner every round, and unlock bigger weapons as your kill count climbs.

Everything (wall textures, the zombie trees, weapons, sound effects) is generated in code at startup, so there
are no asset files. The 3D view is a Wolfenstein-style raycaster.

## Run it

```bash
cd ZombieTrees
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Play in a browser

**Play it here: https://sebastianserrano23.github.io/ZombieTrees/**

That page redeploys itself: `.github/workflows/deploy.yml` rebuilds the WebAssembly version and
publishes it to GitHub Pages on every push to `main`, so `git push` is the only step. Progress and
failures show up in the repository's **Actions** tab. (One-time setup, if you fork this:
**Settings → Pages → Source → GitHub Actions**.)

To build it yourself:

```bash
pip install pygbag
./build_web.sh          # produces build/web.zip
```

Upload `build/web.zip` to [itch.io](https://itch.io) as a project with **Kind of project: HTML**, tick
*This file will be played in the browser*, and set the viewport to **960 x 600**.

To try the web version locally first:

```bash
python -m http.server --directory build/web 8000   # then open http://localhost:8000
```

In the browser version you steer by moving the cursor left or right of the screen centre, because
browsers don't hand over the mouse the way a desktop game does. Everything else is the same, though
it runs a little slower and casts fewer rays to compensate.

## Controls

| Key | Action |
| --- | --- |
| `W A S D` / arrows | Move / turn |
| `Shift` | Sprint |
| Mouse | Aim |
| Left click | Attack (hold for automatic weapons) |
| `1`–`6` / mouse wheel | Switch weapon |
| `Q` | Previous weapon |
| `R` | Reload |
| `M` / `Tab` | Toggle minimap |
| `Esc` | Pause (releases the mouse) |
| `F3` | FPS counter |

## Weapons

You start with the machete and pistol. Kills unlock the rest, and each new weapon is equipped automatically.

| Slot | Weapon | Unlocks at | Notes |
| --- | --- | --- | --- |
| 1 | Machete | start | Melee, hits up to 2 trees, big knockback, never runs dry |
| 2 | Pistol | start | Accurate semi-auto |
| 3 | Shotgun | 12 kills | 9 pellets, devastating up close |
| 4 | AK-47 | 30 kills | Full auto, 30-round mag |
| 5 | Chainsaw | 55 kills | Continuous melee, shreds up to 3 trees at once |
| 6 | Flamethrower | 85 kills | Short-range cone that sets trees on fire |

Trees drop ammo crates and first-aid kits. Clearing a wave also heals you and tops up ammo.

## Enemies

| Tree | First wave | Behavior |
| --- | --- | --- |
| Sapling | 1 | Small, quick, fragile |
| Rotwood | 1 | The standard shambler |
| Thornback | 3 | Fast, thorny, hits hard |
| Spitter | 4 | Keeps its distance and spits sap. Dodge it |
| Elder | 5 | Huge, slow, very tanky. Drops ammo and health |

Every wave brings more trees, and every tree gets about **+22% HP**, **+6% speed** (capped at 1.9x) and
**+10% damage** per wave. Trees rise out of the ground at spawn points, usually out of your sight.

## Project layout

```
main.py                 entry point
zombietrees/
  settings.py           resolution, FOV, player stats, tuning constants
  world.py              map layout, DDA raycasting, collision, BFS pathfinding
  art.py                procedural textures, sprites and weapon viewmodels
  renderer.py           raycaster, billboard sprites with z-buffer, particles, viewmodel
  entities.py           player, enemy AI, wave scaling/rosters, projectiles, pickups
  weapons.py            weapon definitions + ammo/reload/unlock logic
  game.py               game loop, states, combat, waves
  hud.py                HUD, menus, minimap
  sound.py              synthesized sound effects
```

Balance lives in `weapons.py` (`WEAPONS`) and `entities.py` (`ENEMY_TYPES`, `wave_scaling`, `wave_roster`).
Your best score is saved to `save.json`.
