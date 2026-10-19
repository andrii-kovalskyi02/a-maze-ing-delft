"""Start the game: ``python main.py``."""

from __future__ import annotations

import os
import tempfile

import persistence
import rooms  # noqa: F401  (importing rooms registers them)
import ui
import world
from game import Game
from persistence import create_tables, load_game

#: Set this to a room key (e.g. ``lab_2001``) to start straight in that room, to try it out.
START_ROOM_VARIABLE = "AMAZE_START_ROOM"

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


def developer_start() -> Game | None:
    """Start in the room named by ``AMAZE_START_ROOM``, for trying a room out; None if it is unset.

    The practice run uses a scratch database that is emptied each time, so nothing it does can
    touch anybody's saves or scores.
    """
    key = os.environ.get(START_ROOM_VARIABLE, "").strip()
    if not key:
        return None
    try:
        world.get(key)
    except KeyError:
        keys = ", ".join(room.key for room in world.all_rooms())
        ui.say(f"{START_ROOM_VARIABLE}={key!r} is not a room. The rooms are: {keys}")
        ui.say()
        return None
    persistence.DATABASE_NAME = os.path.join(tempfile.gettempdir(), "amaze_developer.db")
    if os.path.exists(persistence.DATABASE_NAME):
        os.remove(persistence.DATABASE_NAME)
    create_tables()
    ui.say(f"Developer start in {key}. Nothing from this run is saved or put on the scoreboard.")
    ui.say()
    return Game(player_name="Developer", current=key)


def main() -> None:
    """Start a new game or resume an existing saved game."""
    create_tables()

    ui.say(BANNER)
    ui.say()

    practice = developer_start()
    if practice is not None:
        practice.run()
        return

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

    game.run()


if __name__ == "__main__":
    main()
