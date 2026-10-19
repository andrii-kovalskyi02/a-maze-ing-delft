"""Player names and profiles: what is allowed as a name, and how a saved game is described.

Kept apart from ``main.py`` so the rules can be tested without playing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import progress
import world

if TYPE_CHECKING:
    from game import Game

#: The longest name allowed: the shared leaderboard stores 30 characters at most.
MAX_NAME = 30
#: How many saved games the "who is playing?" list shows (it is a numbered menu).
MAX_PROFILES = 8
#: Besides letters and numbers, a name may use a space and these.
_ALLOWED_MARKS = " -_.'"


def check_name(raw: str) -> tuple[str, str | None]:
    """Tidy a typed name and say what is wrong with it, if anything.

    Spaces round the name are dropped and runs of spaces become one, so "  Kru   Jr " and
    "Kru Jr" are the same player.

    Returns:
        The tidied name, and a message to show the player - or None when the name is fine.
    """
    name = " ".join(raw.split())
    if not name:
        return name, "Please enter a valid name."
    if len(name) > MAX_NAME:
        return name, f"That name is too long: {MAX_NAME} characters at most."
    if not all(letter.isalnum() or letter in _ALLOWED_MARKS for letter in name):
        return name, "Names can only use letters, numbers, spaces and - _ . '"
    return name, None


def describe(game: Game) -> str:
    """One line about a saved game, so the player can tell it is theirs."""
    room = world.get(game.current).name
    return (
        f"{game.name} - {progress.percent_explored(game)}% explored - "
        f"{progress.format_duration(game.elapsed_time)} played - {room}"
    )
