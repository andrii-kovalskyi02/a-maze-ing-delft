"""US scoreboard (issues #89, #90, #91): the top 5 finished runs.

A finished run's score is written to the player's row in ``game_states``;
the board shows the five best, highest completion first and the fastest time
breaking a tie. Each player has one row, so every score here has its own name.
Every test gets its own empty database from the ``database`` fixture in
conftest.py.
"""

from __future__ import annotations

import sqlite3

import commands
import persistence
import rooms  # noqa: F401  (importing rooms registers them)
import ui
from game import Game


def save_score(name: str, completion: int, play_time: float) -> None:
    """Give ``name`` a saved game, then put a score on it."""
    persistence.save_game(Game(player_name=name))
    persistence.save_score(name, completion, play_time)


def test_top_scores_sorts_by_completion_then_time_and_keeps_five() -> None:
    """Best completion first, the faster run wins a tie, and only five show."""
    save_score("slow", 80, 300.0)
    save_score("fast", 80, 100.0)
    save_score("best", 100, 900.0)
    save_score("low", 10, 5.0)
    save_score("mid", 50, 50.0)
    save_score("lowest", 5, 1.0)

    names = [name for name, _, _ in persistence.top_scores()]

    assert names == ["best", "fast", "slow", "mid", "low"]


def test_scores_survive_creating_the_tables_again() -> None:
    """Starting the game again must not wipe the scoreboard."""
    save_score("Atax", 42, 61.0)

    persistence.create_tables()

    assert persistence.top_scores() == [("Atax", 42, 61.0)]


def test_a_game_that_was_never_finished_has_no_score() -> None:
    """A paused game sits in game_states too, but is not on the board."""
    persistence.save_game(Game(player_name="Paused"))

    assert persistence.top_scores() == []


def test_saving_the_game_again_keeps_the_score() -> None:
    """save_game must not wipe a score that is already on the row."""
    save_score("Atax", 42, 61.0)

    persistence.save_game(Game(player_name="Atax"))

    assert persistence.top_scores() == [("Atax", 42, 61.0)]


def test_an_old_database_gets_the_scoreboard_columns() -> None:
    """A game.db made before the scoreboard is upgraded, not broken."""
    connection = persistence.get_connection()
    connection.execute("DROP TABLE game_states")
    connection.execute("CREATE TABLE game_states (player_name TEXT PRIMARY KEY)")
    connection.commit()
    connection.close()

    persistence.create_tables()

    connection = sqlite3.connect(persistence.DATABASE_NAME)
    columns = [row[1] for row in connection.execute("PRAGMA table_info(game_states)")]
    connection.close()
    assert "completion" in columns
    assert "finish_time" in columns


def test_options_menu_offers_the_scoreboard() -> None:
    """The Options menu's Scoreboard entry shows the board."""
    menu = {item.label: item.action for item in commands.options_menu(Game())}

    assert menu["Scoreboard"] is commands.do_scoreboard


def test_finishing_saves_the_run_and_shows_the_board(console) -> None:
    """Walking out of the building puts the run on the scoreboard."""
    game = Game(player_name="Atax")

    game.finish()

    assert [name for name, _, _ in persistence.top_scores()] == ["Atax"]
    assert "1. atax" in console.output


def test_typing_scoreboard_at_a_menu_shows_the_board(console) -> None:
    """Typing ``scoreboard`` at any menu shows the board, then asks again."""
    save_score("Atax", 42, 61.0)
    ui.set_scoreboard_handler(lambda: commands.do_scoreboard(Game()))
    console.script("scoreboard", "1")

    try:
        chosen = ui.choose("What do you do?", ["Look around"])
    finally:
        ui.set_scoreboard_handler(None)

    assert chosen == 0
    assert "1. atax - 42% - 01:01" in console.output
