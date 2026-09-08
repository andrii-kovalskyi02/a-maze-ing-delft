"""Playing the game end to end, with the test console instead of a keyboard."""

from __future__ import annotations

from amazing_delft import rooms  # noqa: F401  (importing rooms registers them)
from amazing_delft.game import Game


def test_the_player_starts_in_2035_with_the_note(console) -> None:
    game = Game()
    game.enter()
    assert game.current == "classroom_2035"
    assert "note" in game.backpack
    assert "classroom 2.035" in console.output


def test_help_lists_the_commands(console) -> None:
    game = Game()
    game.step("?")
    assert "look around" in console.output
    assert "go <room>" in console.output


def test_inspecting_something_that_is_there(console) -> None:
    game = Game()
    game.enter()
    game.step("inspect clock")
    assert "half past four" in console.output


def test_inspecting_something_that_is_not(console) -> None:
    game = Game()
    game.enter()
    game.step("inspect unicorn")
    assert "no 'unicorn'" in console.output


def test_taking_an_item_puts_it_in_the_backpack(console) -> None:
    game = Game()
    game.enter()
    game.step("take blue_card")
    assert "blue_card" in game.backpack
    game.step("take blue_card")
    assert "no 'blue_card'" in console.output


def test_walking_to_a_room_that_is_not_next_door(console) -> None:
    game = Game()
    game.enter()
    game.step("go teachers room 4")
    assert "cannot get to" in console.output
    assert game.current == "classroom_2035"


def test_a_locked_door_turns_the_player_away(console) -> None:
    game = Game()
    game.enter()
    game.step("go corridor")
    game.step("go teachers room 4")
    assert "key card" in console.output
    assert game.current == "corridor_ew"


def test_the_key_card_is_checked_automatically(console) -> None:
    """The player never types 'use key' - carrying it is enough."""
    game = Game()
    game.enter()
    game.step("take blue_card")
    game.step("go corridor")
    game.step("go teachers room 4")
    assert game.current == "teachers_room_4"


def test_nonsense_is_answered_with_a_hint_and_changes_nothing(console) -> None:
    game = Game()
    game.enter()
    game.step("do a backflip")
    assert "type '?'" in console.output
    assert game.current == "classroom_2035"


def test_quit_stops_the_loop(console) -> None:
    game = Game()
    game.step("quit")
    assert game.running is False
