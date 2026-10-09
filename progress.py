"""How far a player has got: the numbers on the status line and the scoreboard.

Both show the same percentage and the same play time, so both read them from
here. Keeping them in one place means the scoreboard can never disagree with
what Status told the player.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import world

if TYPE_CHECKING:
    from game import Game


def percent_explored(game: Game) -> int:
    """Return how much of the whole world graph is *done*, as a percent.

    Counts every registered room, finished or still a skeleton - the guide
    treats that as the game's completion metric, not just what is playable
    today. Walking in is enough for a plain room, but a room with a boss only
    counts once that boss is resolved (``game.defeated``) - stepping up to
    the Evil Backpack and walking away does not count as having finished
    classroom 2.031, only actually facing it does.
    """
    total = len(world.all_rooms())
    if total == 0:
        return 0
    return round(_rooms_completed(game) / total * 100)


def _rooms_completed(game: Game) -> int:
    """Return how many rooms in the world graph count as done."""
    completed = 0
    for room in world.all_rooms():
        done = room.key in game.defeated if room.boss is not None else room.key in game.visited
        if done:
            completed += 1
    return completed


def format_duration(seconds: float) -> str:
    """Return ``seconds`` as ``MM:SS``, for the status line and the scoreboard."""
    total_seconds = max(0, int(seconds))
    minutes, secs = divmod(total_seconds, 60)
    return f"{minutes:02d}:{secs:02d}"
