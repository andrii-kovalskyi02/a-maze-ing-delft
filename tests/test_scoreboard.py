"""US5 (issue #89): the top 5 players, best completion first, then fastest.

The sorting itself is the database's job and is tested in test_persistence.py.
These tests are about when the board is shown, and what finishing puts on it.
"""

from __future__ import annotations

import asyncio
import time

import persistence
import rooms  # noqa: F401  (importing rooms registers them)
from game import Game
from leaderboard import scoreboard


def test_an_empty_scoreboard_says_so(console) -> None:
    asyncio.run(scoreboard.show())
    assert "nobody is on the leaderboard yet" in console.output


def test_walking_out_of_the_building_puts_the_run_on_the_scoreboard(console, monkeypatch) -> None:
    game = Game(player_name="Krug")
    game.elapsed_time = 60.0  # a minute from an earlier session
    game.started_at = 0.0
    monkeypatch.setattr(time, "monotonic", lambda: 65.0)  # and 1:05 in this one

    asyncio.run(game.finish())

    assert persistence.top_scores() == [("Krug", 0, 125.0)]
    assert "1. krug - 0% - 02:05" in console.output


def test_a_finished_game_can_no_longer_be_resumed(console) -> None:
    game = Game(player_name="Krug")
    persistence.save_game(game)

    asyncio.run(game.finish())

    assert persistence.load_game("Krug") is None
