"""US scoreboard (issues #89, #90, #91): the top 5 finished runs.

A finished run is written to the ``scores`` table; the board shows the five
best, highest completion first and the fastest time breaking a tie. Every
test gets its own empty database from the ``database`` fixture in conftest.py.
"""

from __future__ import annotations

import commands
import persistence
import rooms  # noqa: F401  (importing rooms registers them)
import ui
from game import Game


def test_top_scores_sorts_by_completion_then_time_and_keeps_five() -> None:
    """Best completion first, the faster run wins a tie, and only five show."""
    persistence.save_score("slow", 80, 300.0)
    persistence.save_score("fast", 80, 100.0)
    persistence.save_score("best", 100, 900.0)
    persistence.save_score("low", 10, 5.0)
    persistence.save_score("mid", 50, 50.0)
    persistence.save_score("lowest", 5, 1.0)

    names = [name for name, _, _ in persistence.top_scores()]

    assert names == ["best", "fast", "slow", "mid", "low"]


def test_scores_survive_creating_the_tables_again() -> None:
    """Starting the game again must not wipe the scoreboard."""
    persistence.save_score("Atax", 42, 61.0)

    persistence.create_tables()

    assert persistence.top_scores() == [("Atax", 42, 61.0)]


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
    persistence.save_score("Atax", 42, 61.0)
    ui.set_scoreboard_handler(lambda: commands.do_scoreboard(Game()))
    console.script("scoreboard", "1")

    try:
        chosen = ui.choose("What do you do?", ["Look around"])
    finally:
        ui.set_scoreboard_handler(None)

    assert chosen == 0
    assert "1. atax - 42% - 01:01" in console.output
