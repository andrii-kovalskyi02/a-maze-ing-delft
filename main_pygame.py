"""Play the game in a Pygame window: ``python main_pygame.py``.

The real console game (main.py) runs unchanged inside the window - see the ``pygame_ui``
package for how. Type + Enter like a normal console. The story text moves on by itself a second
after each line; Space skips all of it. Escape opens the pause menu, M the floor map once you
have it. Closing the window saves and quits, the same as typing "pause".
"""

from __future__ import annotations

import ctypes
import os
import sys

from pygame_ui.window import TerminalWindow

__all__ = ["TerminalWindow"]

# an exe built with `pyinstaller --windowed` has no console, and Windows then hands it fake
# stdout/stderr that crash on the first write. So it is built WITH a console, and that console
# is hidden the instant we start: it never flashes on screen, but the streams stay real
if sys.platform == "win32" and getattr(sys, "frozen", False):
    console_window = ctypes.windll.kernel32.GetConsoleWindow()
    if console_window:
        ctypes.windll.user32.ShowWindow(console_window, 0)  # 0 = SW_HIDE

# if stdout/stderr are still missing or broken for any other reason (a different packager, a
# future PyInstaller), give them somewhere harmless to write instead of crashing the game
try:
    sys.stdout.write("")
except Exception:
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115 - stays open all program
try:
    sys.stderr.write("")
except Exception:
    sys.stderr = open(os.devnull, "w")  # noqa: SIM115 - stays open all program


if __name__ == "__main__":
    TerminalWindow().run()
