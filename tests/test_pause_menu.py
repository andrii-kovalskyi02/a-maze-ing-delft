"""The hooks behind the Pygame window's Escape menu.

The window itself needs a screen, so it is not tested here. What it relies on
is: the game says how the player is doing, time spent in the menu is taken off
every clock, and the game menu drops "Options" because the window has its own.
"""

from __future__ import annotations

import pytest

import commands
import ui
from game import Game


@pytest.fixture
def window_menu():
    """Pretend the Pygame window, with its Escape menu, is the one playing."""
    ui.set_pause_menu(True)
    yield
    ui.set_pause_menu(False)


def test_the_game_menu_offers_options_without_a_pause_menu(console) -> None:
    labels = [item.label for item in commands.build_menu(Game())]
    assert "Options" in labels


def test_the_game_menu_drops_options_when_the_window_has_a_pause_menu(console, window_menu) -> None:
    labels = [item.label for item in commands.build_menu(Game())]
    assert "Options" not in labels


def test_paused_time_is_taken_off_the_clock(console) -> None:
    console.time = 100.0
    ui.hold_time(30.0)
    assert ui.now() == 70.0


def test_paused_time_is_taken_off_the_time_played(console) -> None:
    game = Game()
    ui.set_time_hold_handler(game.hold_time)
    try:
        before = game.started_at
        ui.hold_time(12.0)
        assert game.started_at == before + 12.0
    finally:
        ui.set_time_hold_handler(None)


def test_status_says_how_the_player_is_doing(console) -> None:
    game = Game()
    game.name = "Krug"
    status = game.status()
    assert status["name"] == "Krug"
    assert status["hearts"] == str(game.hearts)
    assert status["percent"] == 0
    assert status["seconds"] >= 0


def test_there_is_no_status_between_games(console) -> None:
    ui.set_status_provider(None)
    assert ui.status() is None
