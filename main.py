"""Start the game: ``python main.py``."""

from __future__ import annotations

import rooms  # noqa: F401  (importing rooms registers them)
import ui
from game import Game
from persistence import create_tables, load_game

BANNER = """
****************************************************************************
*                       A-maze-ing Delft - THUAS Delft                     *
*         The fire alarm is screaming. Find the code. Get out alive.       *
****************************************************************************
""".strip()


def main() -> None:
    """Start a new game or resume an existing saved game."""
    create_tables()

    ui.say(BANNER)
    ui.say()

    player_name = ui.ask("Enter your name: ")

    game = load_game(player_name)

    if game is None:
        ui.say()
        ui.say(f"No saved game found for {player_name}.")
        ui.say("Starting a new game.")
        game = Game(player_name=player_name)
    else:
        ui.say()
        ui.say(f"Welcome back, {player_name}!")
        ui.say("Saved game found. Resuming your game.")

    game.run()


if __name__ == "__main__":
    main()
