"""Start the game: ``python main.py``."""

from __future__ import annotations

import asyncio
import os
import tempfile

import accounts
import cloud
import persistence
import profiles
import rooms  # noqa: F401  (importing rooms registers them)
import ui
import world
from game import Game

#: Set this to a room key (e.g. ``lab_2001``) to start straight in that room, to try it out.
START_ROOM_VARIABLE = "AMAZE_START_ROOM"

BANNER = """
****************************************************************************
*                         After Hours - THUAS Delft                        *
*           Something is wrong in here. Find the code. Get out.            *
****************************************************************************
""".strip()

UNREACHABLE = "Could not reach the server to check your password. Check your connection."


async def ask_name() -> str:
    """Ask for the player's name until they give a good one (see ``profiles.check_name``).

    Spaces round a name are dropped, so "  Kru " and "Kru" are the same player to the saved
    games. So are "krug" and "Krug": the spelling already on file is the one that is kept.
    """
    while True:
        name, problem = profiles.check_name(await ui.ask("Enter your name: "))
        if problem is None:
            return persistence.canonical_name(name)
        await ui.say()
        await ui.say(problem)


async def choose_password(name: str) -> bool:
    """Ask for a new password twice, until it is good and both times match, and keep it.

    False if somebody else registered ``name`` online in the meantime.
    """
    while True:
        password = await ui.ask_secret("Choose a password: ")
        problem = profiles.check_password(password)
        if problem is not None:
            await ui.say(problem)
        elif await ui.ask_secret("Type it again: ") != password:
            await ui.say("Those two were not the same. Try again.")
        elif await accounts.set_password(name, password):
            return True
        else:
            await ui.say(f"Somebody has just taken the name {name}. Pick another one.")
            return False


async def log_in(name: str) -> bool:
    """Ask for ``name``'s password. True once it is right; False if the player gives up.

    A player from before passwords existed has none yet: they choose one now.
    """
    if not await accounts.has_password(name):
        await ui.say(f"{name} has no password yet. Choose one, so nobody else can play as you.")
        return await choose_password(name)
    while True:
        try:
            if await accounts.password_matches(name, await ui.ask_secret("Password: ")):
                return True
            await ui.say("Wrong password.")
        except accounts.Locked:
            await ui.say("Too many wrong passwords. Wait a minute before trying again.")
        if await ui.choose("What now?", ["Try again", "Use a different name"]) != 0:
            return False


async def resume(game: Game) -> Game:
    """Welcome a player back to their saved game."""
    await ui.say()
    await ui.say(f"Welcome back, {game.name}!")
    await ui.say("Saved game found. Resuming your game.")
    game.resumed = True  # the backpack greets a player who comes back (see Game.enter)
    return game


async def new_game(name: str) -> Game:
    """Start a fresh game for ``name``."""
    await ui.say()
    await ui.say(f"No saved game found for {name}.")
    await ui.say("Starting a new game.")
    return Game(player_name=name)


async def new_player() -> Game:
    """Ask for a name and start that player's game.

    Names are unique, so the scoreboard never shows two players with one name. A new name gets a
    password. A name that is taken - by a save, a score, or online - needs its password, so
    nobody's save or score is ever taken over.
    """
    while True:
        name = await ask_name()
        try:
            game = await _sign_in(name)
        except accounts.Unreachable:
            await ui.say()
            await ui.say(UNREACHABLE)
            continue
        if game is not None:
            return game


async def _sign_in(name: str) -> Game | None:
    """Register ``name`` or log in as it; return their game, or None to ask for another name."""
    if not await accounts.taken(name):
        await ui.say()
        await ui.say(f"Welcome, {name}! Choose a password, so nobody else can play as you.")
        return await new_game(name) if await choose_password(name) else None
    saved = persistence.load_game(name)
    await ui.say()
    if saved is None:
        await ui.say(f"The name {name} is already taken.")
    else:
        await ui.say(f"There is already a saved game for {name}:")
        await ui.say(profiles.describe(saved))
    is_me = await ui.choose("Is that you?", ["Yes, that's me", "No, use a different name"]) == 0
    if is_me and await log_in(name):
        return await new_game(name) if saved is None else await resume(saved)
    return None


async def pick_player() -> Game:
    """Let the player pick a saved game from the list, or start as a new player."""
    saves = [
        game
        for name in persistence.recent_saves(profiles.MAX_PROFILES)
        if (game := persistence.load_game(name)) is not None
    ]
    if saves:
        labels = [profiles.describe(game) for game in saves] + ["New player"]
        index = await ui.choose("Who is playing?", labels)
        if index is not None and index < len(saves):
            try:
                if await log_in(saves[index].name):
                    return await resume(saves[index])
            except accounts.Unreachable:
                await ui.say()
                await ui.say(UNREACHABLE)
    return await new_player()


async def developer_start() -> Game | None:
    """Start in the room named by ``AMAZE_START_ROOM``, for trying a room out; None if it is unset.

    The practice run uses a scratch database that is emptied each time, and the shared leaderboard
    is switched off, so nothing it does can touch anybody's saves or scores.
    """
    key = os.environ.get(START_ROOM_VARIABLE, "").strip()
    if not key:
        return None
    try:
        world.get(key)
    except KeyError:
        keys = ", ".join(room.key for room in world.all_rooms())
        await ui.say(f"{START_ROOM_VARIABLE}={key!r} is not a room. The rooms are: {keys}")
        await ui.say()
        return None
    persistence.DATABASE_NAME = os.path.join(tempfile.gettempdir(), "amaze_developer.db")
    if os.path.exists(persistence.DATABASE_NAME):
        os.remove(persistence.DATABASE_NAME)
    persistence.create_tables()
    cloud.SUPABASE_URL = ""
    await ui.say(
        f"Developer start in {key}. Nothing from this run is saved or put on the leaderboard."
    )
    await ui.say()
    return Game(player_name="Developer", current=key)


async def main() -> None:
    """Start a new game or resume an existing saved game."""
    persistence.create_tables()

    await ui.say(BANNER)
    await ui.say()

    game = await developer_start()
    if game is None:
        game = await pick_player()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
