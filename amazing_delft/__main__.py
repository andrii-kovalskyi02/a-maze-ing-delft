"""Start the game with ``python -m amazing_delft``."""

from __future__ import annotations

from amazing_delft import rooms, ui  # noqa: F401  (importing rooms registers them)
from amazing_delft.game import Game

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
