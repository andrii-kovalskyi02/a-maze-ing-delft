"""Tests for saving and loading a complete game state."""

from __future__ import annotations

import asyncio

import pytest

import persistence
import rooms  # noqa: F401
import world
from game import Game
from health import Health
from models import Area, Room


def test_save_and_load_preserves_game_state(tmp_path, monkeypatch) -> None:
    """Saving and loading must restore the player's complete state."""
    database = tmp_path / "test.db"
    monkeypatch.setattr(persistence, "DATABASE_NAME", str(database))

    persistence.create_tables()

    game = Game(player_name="Michaela")
    game.current = "corridor_blue"
    game.hearts = Health(2)
    game.visited = {"classroom_2035", "corridor_blue"}
    game.unlocked = {"corridor_red"}
    game.defeated = {"some_challenge"}
    game.taken = {("corridor_blue", "evacuation_plan")}
    game.approached = {"some_encounter"}
    game.carrying.add("evacuation_plan")
    game.elapsed_time = 123.45

    persistence.save_game(game)

    loaded = persistence.load_game("Michaela")

    assert loaded is not None
    assert loaded.player_name == game.player_name
    assert loaded.current == game.current
    assert loaded.hearts == game.hearts
    assert set(item.key for item in loaded.carrying) == set(item.key for item in game.carrying)
    assert loaded.visited == game.visited
    assert loaded.unlocked == game.unlocked
    assert loaded.defeated == game.defeated
    assert loaded.taken == game.taken
    assert loaded.approached == game.approached
    assert loaded.elapsed_time == game.elapsed_time


def test_pause_saves_the_game_and_stops_running(tmp_path, monkeypatch) -> None:
    """Pausing must save the current state and stop the game."""
    database = tmp_path / "test.db"
    monkeypatch.setattr(persistence, "DATABASE_NAME", str(database))

    persistence.create_tables()

    game = Game(player_name="Michaela")
    game.current = "corridor_blue"
    game.hearts = Health(2)
    game.elapsed_time = 10.0

    game.pause()

    assert game.running is False

    loaded = persistence.load_game("Michaela")

    assert loaded is not None
    assert loaded.current == "corridor_blue"
    assert loaded.hearts == Health(2)
    assert loaded.elapsed_time >= 10.0


def _game_in_a_room_holding(item: str, monkeypatch: pytest.MonkeyPatch) -> Game:
    """Return a game standing in a made-up room with ``item`` on the floor."""
    room = Room(
        key="test_cupboard",
        name="Test Cupboard",
        area=Area.BLUE,
        description="A room built for this test.",
        look_around="Shelves.",
        items=(item,),
    )
    monkeypatch.setitem(world._ROOMS, room.key, room)
    return Game(player_name="Tester", current=room.key)


def test_picking_up_a_digit_saves_the_game(console, monkeypatch) -> None:
    """#216: a digit, once found, survives a crash or a closed window."""
    game = _game_in_a_room_holding("digit_4", monkeypatch)
    console.script("1", "1")  # look around, take it
    asyncio.run(game.turn())

    loaded = persistence.load_game("Tester")
    assert loaded is not None
    assert "digit_4" in loaded.carrying
    assert game.running


def test_picking_up_anything_else_does_not_save(console, monkeypatch) -> None:
    """#216: only a digit is worth an autosave; the rest waits for "pause"."""
    game = _game_in_a_room_holding("brass_key", monkeypatch)
    console.script("1", "1")
    asyncio.run(game.turn())

    assert persistence.load_game("Tester") is None


def test_the_scoreboard_puts_the_most_complete_first_and_breaks_a_tie_on_time() -> None:
    """US5: completion descending, then play time ascending - in that order."""
    persistence.record_score("Slow", 40, 500.0)
    persistence.record_score("Fast", 40, 100.0)
    persistence.record_score("Thorough", 90, 900.0)

    names = [name for name, _, _ in persistence.top_scores()]

    assert names == ["Thorough", "Fast", "Slow"]


def test_the_scoreboard_shows_only_the_top_five() -> None:
    for number in range(7):
        persistence.record_score(f"Player {number}", number * 10, 60.0)

    names = [name for name, _, _ in persistence.top_scores()]

    assert names == ["Player 6", "Player 5", "Player 4", "Player 3", "Player 2"]


def test_a_player_keeps_only_their_best_run() -> None:
    persistence.record_score("Krug", 50, 300.0)
    persistence.record_score("Krug", 40, 100.0)  # explored less: not better
    persistence.record_score("Krug", 50, 200.0)  # same, but faster: better

    assert persistence.top_scores() == [("Krug", 50, 200.0)]


def test_the_scoreboard_survives_a_restart() -> None:
    """US5: it is stored in the database, not in memory."""
    persistence.record_score("Krug", 50, 300.0)
    persistence.create_tables()  # what the next start of the program does first

    assert persistence.top_scores() == [("Krug", 50, 300.0)]
