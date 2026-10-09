"""Tests for saving and loading a complete game state."""

from __future__ import annotations

import persistence
import rooms  # noqa: F401
from game import Game
from health import Health


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
