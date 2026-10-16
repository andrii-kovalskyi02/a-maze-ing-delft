"""The top 5 players on the 2nd floor (US5, issue #89).

Sorted by how much of the floor they finished, highest first, and then by how
long they took, fastest first - the order the Project Guide asks for. It is
shown when the player walks out of the building, from the Options menu, and
by typing ``scoreboard`` at any prompt. The runs themselves are stored by
persistence.py (#121).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import persistence
import progress
import ui

if TYPE_CHECKING:
    from game import Game

#: How many players the scoreboard shows.
TOP = 5


def lines() -> list[str]:
    """Return the scoreboard as lines of text, to print or to draw."""
    players = persistence.top_scores(TOP)
    result = [f"Scoreboard - top {TOP}"]
    if not players:
        result.append("Nobody is on the scoreboard yet.")
    for place, (name, percent, seconds) in enumerate(players, start=1):
        result.append(f"{place}. {name} - {percent}% - {progress.format_duration(seconds)}")
    return result


def show(game: Game | None = None) -> None:
    """Print the scoreboard. ``game`` is unused; it lets the menu call this."""
    ui.say()
    for line in lines():
        ui.say(line)
