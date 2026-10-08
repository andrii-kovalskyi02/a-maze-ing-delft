"""The top 5 players on the 2nd floor (US5, issue #89).

Reads the ``game_states`` table that persistence.py already keeps, so the
scoreboard survives a restart without a table of its own.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import ui
import world
from persistence import get_connection, save_game

if TYPE_CHECKING:
    from game import Game

TOP = 5


def record(game: Game) -> None:
    """Save the final time and progress of a player who just escaped."""
    game.update_elapsed_time()
    save_game(game)


def top_players() -> list[tuple[str, int, float]]:
    """Return (name, percent, seconds) for the best players: highest % first, then fastest."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT player_name, elapsed_time, visited_rooms, defeated_challenges
        FROM game_states
        """
    ).fetchall()
    connection.close()

    rooms = world.all_rooms()
    scores = []
    for name, seconds, visited_json, defeated_json in rows:
        visited = set(json.loads(visited_json))
        defeated = set(json.loads(defeated_json))
        done = sum(
            1
            for room in rooms
            if (room.key in defeated if room.boss is not None else room.key in visited)
        )
        percent = round(done / len(rooms) * 100) if rooms else 0
        scores.append((name, percent, seconds))

    scores.sort(key=lambda score: (-score[1], score[2]))
    return scores[:TOP]


def show() -> None:
    """Print the scoreboard."""
    from commands import _format_duration

    players = top_players()
    ui.say()
    ui.say("Scoreboard - top 5")
    if not players:
        ui.say("Nobody is on the scoreboard yet.")
    for place, (name, percent, seconds) in enumerate(players, start=1):
        ui.say(f"{place}. {name} - {percent}% - {_format_duration(seconds)}")
