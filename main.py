"""Start the game: ``python main.py``."""

from __future__ import annotations

import rooms  # noqa: F401  (importing rooms registers them)
import ui
from game import Game
from persistence import create_tables, load_game

BANNER = """
****************************************************************************
*                       A-maze-ing Delft - THUAS Delft                     *
*           Something is wrong in here. Find the code. Get out.            *
****************************************************************************
""".strip()


def ask_name() -> str:
    """Ask for the player's name until they give one: it cannot be empty.

    Spaces on their own count as empty, and spaces round a name are dropped, so
    "  Kru " and "Kru" are the same player to the saved games.
    """
    while True:
        name = ui.ask("Enter your name: ").strip()
        if name:
            return name
        ui.say()
        ui.say("Please enter a valid name.")


def main() -> None:
    """Start a new game or resume an existing saved game."""
    create_tables()

    ui.say(BANNER)
    ui.say()

    player_name = ask_name()

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
        game.resumed = True

    game.run()


if __name__ == "__main__":
    main()
