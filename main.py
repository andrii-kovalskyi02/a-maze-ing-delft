"""Start the game: ``python main.py``."""

from __future__ import annotations

import persistence
import profiles
import rooms  # noqa: F401  (importing rooms registers them)
import ui
from game import Game

BANNER = """
****************************************************************************
*                       A-maze-ing Delft - THUAS Delft                     *
*           Something is wrong in here. Find the code. Get out.            *
****************************************************************************
""".strip()


def ask_name() -> str:
    """Ask for the player's name until they give a good one (see ``profiles.check_name``).

    Spaces round a name are dropped, so "  Kru " and "Kru" are the same player to the saved
    games. So are "krug" and "Krug": the spelling already on file is the one that is kept.
    """
    while True:
        name, problem = profiles.check_name(ui.ask("Enter your name: "))
        if problem is None:
            return persistence.canonical_name(name)
        ui.say()
        ui.say(problem)


def resume(game: Game) -> Game:
    """Welcome a player back to their saved game."""
    ui.say()
    ui.say(f"Welcome back, {game.name}!")
    ui.say("Saved game found. Resuming your game.")
    game.resumed = True  # the backpack greets a player who comes back (see Game.enter)
    return game


def new_player() -> Game:
    """Ask for a name and start that player's game.

    A name that already has a saved game is never taken over: the player may continue it if it
    is theirs, and otherwise picks another name, so nobody's save is ever replaced.
    """
    while True:
        name = ask_name()
        saved = persistence.load_game(name)
        if saved is None:
            ui.say()
            ui.say(f"No saved game found for {name}.")
            ui.say("Starting a new game.")
            return Game(player_name=name)
        ui.say()
        ui.say(f"There is already a saved game for {name}:")
        ui.say(profiles.describe(saved))
        if ui.choose("Is that you?", ["Yes, continue this game", "No, use a different name"]) == 0:
            return resume(saved)


def pick_player() -> Game:
    """Let the player pick a saved game from the list, or start as a new player."""
    saves = [
        game
        for name in persistence.recent_saves(profiles.MAX_PROFILES)
        if (game := persistence.load_game(name)) is not None
    ]
    if saves:
        labels = [profiles.describe(game) for game in saves] + ["New player"]
        index = ui.choose("Who is playing?", labels)
        if index is not None and index < len(saves):
            return resume(saves[index])
    return new_player()


def main() -> None:
    """Start a new game or resume an existing saved game."""
    persistence.create_tables()

    ui.say(BANNER)
    ui.say()

    pick_player().run()


if __name__ == "__main__":
    main()
