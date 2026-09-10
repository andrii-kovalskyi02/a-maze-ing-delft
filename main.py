"""Start the game: ``python main.py``."""

from __future__ import annotations

import rooms  # noqa: F401  (importing rooms registers them)
import ui
from game import Game

BANNER = """
****************************************************************************
*                       A-maze-ing Delft - THUAS Delft                     *
*         The fire alarm is screaming. Find the code. Get out alive.       *
****************************************************************************
""".strip()


def main() -> None:
    """Print the banner and play one game."""
    ui.say(BANNER)
    Game().run()


if __name__ == "__main__":
    main()
