"""A room stops describing what the player has already picked up, and welcomes them back."""

from __future__ import annotations

import pytest

import rooms  # noqa: F401  (importing rooms registers them)
import world
from commands import _interactions, do_look_around
from game import Game
from models import Room, Unless, plain, resolve


def look(game: Game, console) -> str:
    """Return what "Look around" says in the game's current room."""
    before = len(console.lines)
    console.script("0")  # nothing to do afterwards
    do_look_around(game)
    return "\n".join(console.lines[before:])


def test_the_evacuation_plan_is_left_out_once_it_is_taken(console) -> None:
    game = Game(current="corridor_blue")
    assert "evacuation plan hangs" in look(game, console)
    assert "Look at the evacuation plan" in [a.label for a in _interactions(game)]

    game.take("evacuation_plan")
    assert "evacuation plan hangs" not in look(game, console)
    assert "Look at the evacuation plan" not in [a.label for a in _interactions(game)]


def test_the_extinguisher_in_teachers_room_4_is_left_out_once_it_is_taken(console) -> None:
    game = Game(current="teachers_room_4")
    assert "fire extinguisher" in look(game, console)
    game.take("fire_extinguisher")
    assert "fire extinguisher" not in look(game, console)


def test_a_reward_counts_as_taken_too(console) -> None:
    game = Game(current="lab_2003")
    assert "turning the brass key" in look(game, console)
    game.carrying.add("brass_key")  # what winning against Steve hands over
    assert "turning the brass key" not in look(game, console)
    assert "Look at the brass key" not in [a.label for a in _interactions(game)]


def test_the_notebook_stays_when_the_key_is_gone(console) -> None:
    game = Game(current="project_room_1")
    assert "shiny key" in look(game, console)
    game.take("lab_2001_key")
    after = look(game, console)
    assert "shiny key" not in after
    assert "notebook" in after


def test_a_room_with_a_return_line_says_it_on_the_second_visit(console) -> None:
    game = Game(current="classroom_2021")
    game.visited.add("classroom_2021")
    game.enter()
    assert "The same spotless room" in "\n".join(console.lines)
    assert "You push the door" not in "\n".join(console.lines)


def test_the_first_visit_still_tells_the_whole_description(console) -> None:
    game = Game(current="classroom_2021")
    game.enter()
    assert "You push the door" in "\n".join(console.lines)


@pytest.mark.parametrize("room", world.all_rooms(), ids=lambda room: room.key)
def test_every_part_of_a_look_around_text_can_be_told(room: Room) -> None:
    """Whatever the player has taken, what is left to say is plain text and pauses."""
    if room.look_around is None:
        return
    for taken in (False, True):
        told = resolve(room.look_around, lambda _key, taken=taken: taken)
        assert all(isinstance(part, str | float) for part in told)
    assert plain(room.look_around).strip()


def test_unless_tells_its_after_text_once_taken() -> None:
    text = ("a", Unless("key", ("b",), after=("c",)))
    assert resolve(text, lambda _key: False) == ("a", "b")
    assert resolve(text, lambda _key: True) == ("a", "c")


def test_resolve_leaves_plain_text_alone() -> None:
    assert resolve("one line", lambda _key: True) == ("one line",)
