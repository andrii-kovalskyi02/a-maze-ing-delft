"""Build the game for web browsers with pygbag: ``python web/build.py``.

Copies the game into ``build/web-src/game`` next to ``web/main.py`` (pygbag needs its start-up file
to be called main.py, and the game's own main.py is the terminal version), then runs pygbag.
The finished site is in ``build/web-src/build/web``: upload that folder's files anywhere that
serves static pages. Add ``--serve`` to try it at http://localhost:8000 instead, and
``--offline`` for a build that never talks to Supabase (accounts and scores stay in the browser).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "build" / "web-src"
# what the browser needs: the game's code and its assets, not the tests or the tools
FOLDERS = ("assets", "leaderboard", "pygame_ui", "rooms")


def copy_game() -> None:
    """Put a fresh copy of the game, and the web start-up file, in :data:`SOURCE`."""
    shutil.rmtree(SOURCE, ignore_errors=True)
    game = SOURCE / "game"
    game.mkdir(parents=True)
    for module in REPO.glob("*.py"):
        shutil.copy2(module, game / module.name)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for folder in FOLDERS:
        shutil.copytree(REPO / folder, game / folder, ignore=ignore)
    shutil.copy2(REPO / "web" / "main.py", SOURCE / "main.py")
    if "--offline" in sys.argv:
        cloud = game / "cloud.py"
        cloud.write_text(
            cloud.read_text().replace('SUPABASE_URL = "https://', 'SUPABASE_URL = ""  # ')
        )


def main() -> None:
    """Copy the game and run pygbag on it."""
    copy_game()
    serve = "--serve" in sys.argv
    command = [sys.executable, "-m", "pygbag", "--title", "After Hours"]
    command += [] if serve else ["--build"]
    subprocess.run([*command, str(SOURCE)], check=True)


if __name__ == "__main__":
    main()
