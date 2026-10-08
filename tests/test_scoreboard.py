"""US5 (issue #89): the top 5 players, best completion first, then fastest."""

from __future__ import annotations

import persistence
import rooms  # noqa: F401  (importing rooms registers them)
import scoreboard
import world
from game import Game


def saved_run(name: str, rooms_done: int, seconds: float) -> None:
    """Save a game for ``name`` that has finished ``rooms_done`` boss-free rooms."""
    plain = [room.key for room in world.all_rooms() if room.boss is None]
    assert len(plain) >= rooms_done, "the world needs more boss-free rooms for this test"
    game = Game(player_name=name)
    game.visited = set(plain[:rooms_done])
    game.elapsed_time = seconds
    persistence.save_game(game)


def test_the_most_complete_player_comes_first_and_time_breaks_a_tie(console) -> None:
    saved_run("Slow", rooms_done=3, seconds=500)
    saved_run("Fast", rooms_done=3, seconds=100)
    saved_run("Thorough", rooms_done=5, seconds=900)

    names = [name for name, _, _ in scoreboard.top_players()]

    assert names == ["Thorough", "Fast", "Slow"]


def test_only_the_top_five_are_shown(console) -> None:
    for number in range(7):
        saved_run(f"Player {number}", rooms_done=number, seconds=60)

    names = [name for name, _, _ in scoreboard.top_players()]

    assert names == ["Player 6", "Player 5", "Player 4", "Player 3", "Player 2"]


def test_an_empty_scoreboard_says_so(console) -> None:
    scoreboard.show()
    assert "nobody is on the scoreboard yet" in console.output


def test_walking_out_of_the_building_shows_the_scoreboard(console) -> None:
    saved_run("Krug", rooms_done=2, seconds=125)

    Game().finish()

    assert "scoreboard" in console.output
    assert "1. krug" in console.output
