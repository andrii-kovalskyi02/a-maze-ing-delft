"""The top 5 players on the 2nd floor (US5, issue #89).

Sorted by how much of the floor they finished, highest first, and then by how
long they took, fastest first. It is
shown when the player walks out of the building, from the Options menu, and
by typing ``scoreboard`` at any prompt. The runs themselves are stored by
persistence.py (#121). When the shared scoreboard is set up (leaderboard/online.py), it shows
everyone's best five instead, falling back to this computer's runs when it cannot be reached.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import persistence
import progress
import ui
from leaderboard import online

if TYPE_CHECKING:
    from game import Game

#: How many players the scoreboard shows.
TOP = 5


def lines() -> list[str]:
    """Return the scoreboard as lines of text, to print or to draw."""
    online.sync_in_background()  # for next time; this call only reads what is already on disk
    players = persistence.online_top() if online.enabled() else None
    everyone = players is not None  # a list that was fetched, even an empty one
    if players is None:
        players = persistence.top_scores(TOP)
    title = f"Leaderboard - top {TOP}"
    if online.enabled():
        title += "" if everyone else " (this computer only)"
    result = [title]
    if not players:
        result.append("Nobody is on the leaderboard yet.")
    for place, (name, percent, seconds) in enumerate(players, start=1):
        result.append(f"{place}. {name} - {percent}% - {progress.format_duration(seconds)}")
    return result


async def show(game: Game | None = None) -> None:
    """Print the scoreboard. ``game`` is unused; it lets the menu call this."""
    await ui.say()
    for line in lines():
        await ui.say(line)
