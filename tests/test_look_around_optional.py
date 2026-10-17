"""A room may have no 'look around' text, like a staircase you only pass through."""

from __future__ import annotations

import pytest

import rooms  # noqa: F401  (importing rooms registers them)
import world
from commands import build_menu, do_look_around
from game import Game
from models import Area, Inspectable, Room


def place(monkeypatch: pytest.MonkeyPatch, room: Room) -> Game:
    """Put ``room`` in the world for this test only, and stand the player in it."""
    monkeypatch.setitem(world._ROOMS, room.key, room)
    return Game(current=room.key)


def test_an_empty_room_without_text_does_not_offer_look_around(console, monkeypatch) -> None:
    game = place(monkeypatch, Room(key="stairs", name="Stairs", area=Area.BLUE, description="x"))
    assert "Look around" not in [item.label for item in build_menu(game)]


def test_without_text_look_around_still_offers_what_is_there(console, monkeypatch) -> None:
    room = Room(
        key="stairs",
        name="Stairs",
        area=Area.BLUE,
        description="x",
        inspectables=(Inspectable(name="the poster", text="A notice poster."),),
    )
    game = place(monkeypatch, room)
    assert "Look around" in [item.label for item in build_menu(game)]

    console.script("1", "0")
    do_look_around(game)
    assert "notice poster" in console.output
