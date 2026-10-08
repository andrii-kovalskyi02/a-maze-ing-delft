"""The top 5 players on the 2nd floor (US5, issue #89).

Sorted by how much of the floor they finished, highest first, and then by how
long they took, fastest first - the order the Project Guide asks for. It is
shown when the player walks out of the building, and from the Options menu.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import progress
import ui
from persistence import get_connection, load_game

if TYPE_CHECKING:
    from game import Game

#: How many players the scoreboard shows.
TOP = 5


def show(game: Game | None = None) -> None:
    """Print the scoreboard. ``game`` is unused; it lets the menu call this."""
    players = top_players()
    ui.say()
    ui.say(f"Scoreboard - top {TOP}")
    if not players:
        ui.say("Nobody is on the scoreboard yet.")
    for place, (name, percent, seconds) in enumerate(players, start=1):
        ui.say(f"{place}. {name} - {percent}% - {progress.format_duration(seconds)}")


def top_players() -> list[tuple[str, int, float]]:
    """Return (name, percent, seconds) for the best players: highest % first, then fastest."""
    scores = [(run.name, progress.percent_explored(run), run.elapsed_time) for run in _runs()]
    scores.sort(key=lambda score: (-score[1], score[2]))
    return scores[:TOP]


def _runs() -> list[Game]:
    """Return every run the scoreboard ranks.

    A stand-in until the persistence enabler (#121) stores finished runs: for
    now this is every saved game, finished or not. When #121 lands, this is
    the only function that has to change.
    """
    connection = get_connection()
    names = [row[0] for row in connection.execute("SELECT player_name FROM game_states")]
    connection.close()

    runs = []
    for name in names:
        game = load_game(name)
        if game is not None:
            runs.append(game)
    return runs
