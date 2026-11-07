"""Browser-only helpers for the pygbag (WebAssembly) build. Every function is a no-op on desktop."""
import pygame

from .settings import WEB

if WEB:
    import platform  # in pygbag this module is the bridge to the page's JavaScript


def _js(code):
    """Run a JavaScript expression in the page. Returns None if that isn't possible."""
    if not WEB:
        return None
    try:
        return platform.window.eval(code)
    except Exception:
        return None


def setup_canvas():
    # The page stretches the 960x600 canvas to fit the browser window. By default the
    # browser smooths that stretch, which blurs everything; keep the pixels sharp instead.
    _js("void((window.canvas || document.getElementById('canvas')).style.imageRendering = 'pixelated')")


def set_mouse_capture(on):
    """Lock the mouse to the game (like the desktop build), or release it."""
    if not WEB:
        return
    # SDL's relative mode makes pygame report raw mouse movement instead of a cursor
    # position, so the view can turn forever without the cursor hitting the screen edge.
    if hasattr(pygame.mouse, "set_relative_mode"):
        pygame.mouse.set_relative_mode(on)
    else:
        pygame.event.set_grab(on)
        pygame.mouse.set_visible(not on)
    if on:
        # Ask the browser for pointer lock right away. This is allowed because it runs just
        # after the player's click; if the browser refuses, SDL retries on the next click or key.
        _js("void((function(){var c = window.canvas || document.getElementById('canvas');"
            "var p = c && c.requestPointerLock && c.requestPointerLock();"
            "if (p && p.catch) p.catch(function(){});})())")
    else:
        _js("void(document.pointerLockElement && document.exitPointerLock())")
    pygame.mouse.get_rel()


def pointer_locked():
    """Is the browser currently locking the mouse to the game? (Always True on desktop.)"""
    if not WEB:
        return True
    r = _js("document.pointerLockElement ? 1 : 0")
    if r is None:
        return True  # can't tell, so don't act on it
    return str(r) in ("1", "1.0", "true", "True")
