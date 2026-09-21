"""Tests for saving and loading a complete game state."""

from __future__ import annotations

import persistence
import rooms  # noqa: F401
from game import Game


def test_save_and_load_preserves_game_state(tmp_path, monkeypatch) -> None:
    """Saving and loading must restore the player's complete state."""
    database = tmp_path / "test.db"
    monkeypatch.setattr(persistence, "DATABASE_NAME", str(database))

    persistence.create_tables()

    game = Game(player_name="Michaela")
    game.current = "corridor_blue"
    game.hearts = 2
    game.visited = {"classroom_2035", "corridor_blue"}
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
    game.hearts = 2
    game.elapsed_time = 10.0

    game.pause()

    assert game.running is False

    loaded = persistence.load_game("Michaela")

    assert loaded is not None
    assert loaded.current == "corridor_blue"
    assert loaded.hearts == 2
    assert loaded.elapsed_time >= 10.0
