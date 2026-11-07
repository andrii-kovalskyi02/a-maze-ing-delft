"""Start the game in a web browser. This is the page's start-up file in a pygbag build.

``python web/build.py`` puts the game in a ``game`` folder next to this file; pygbag runs this.
"""

import asyncio
import os
import sys

import pygame  # noqa: F401 - pygbag loads the packages it sees imported in this file

GAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game")
sys.path.insert(0, GAME)  # the game's own modules ("import ui", "import main") come from there

import persistence  # noqa: E402 - needs the path above
from pygame_ui.window import TerminalWindow  # noqa: E402

# pygbag changes the working folder while the game runs, so the database gets a full path
persistence.DATABASE_NAME = os.path.join(GAME, persistence.DATABASE_NAME)


async def main() -> None:
    """Open the game's window (a canvas on the page) and play."""
    await TerminalWindow().main_loop()


asyncio.run(main())
