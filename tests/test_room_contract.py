"""The room test kit.

Every room registered in ``rooms/__init__.py`` is checked here
automatically.  You do not add anything to this file when you add a room - if
your room breaks one of these rules, the failure names your room.
"""

from __future__ import annotations

import pytest

import rooms  # noqa: F401  (importing rooms registers them)
import world
from game import STARTING_ROOM
from inventory import ITEM_CATALOGUE
from models import Area, Room, plain

ALL_ROOMS = world.all_rooms()


def ids(room: Room) -> str:
    """Name the room in the test report, so a failure points at its file."""
    return room.key


@pytest.mark.parametrize("room", ALL_ROOMS, ids=ids)
def test_room_introduces_itself(room: Room) -> None:
    """Every room has something to say when the player walks in.

    ``look_around`` may be left out (None) for a place with nothing to
    describe, but if it is given it must not be empty.
    """
    assert plain(room.description).strip(), f"{room.key} has no description"
    if room.look_around is not None:
        assert plain(room.look_around).strip(), (
            f"{room.key} has an empty 'look around' text; leave it out instead"
        )
    assert isinstance(room.area, Area)


@pytest.mark.parametrize("room", ALL_ROOMS, ids=ids)
def test_exits_lead_somewhere_real(room: Room) -> None:
    """Every exit names a room that actually exists."""
    for exit_key in room.exits:
        assert exit_key in {other.key for other in ALL_ROOMS}, (
            f"{room.key} has an exit to {exit_key!r}, which is not a registered room"
        )


@pytest.mark.parametrize("room", ALL_ROOMS, ids=ids)
def test_exits_go_both_ways(room: Room) -> None:
    """If you can walk there, you can walk back. Otherwise the player is trapped."""
    for exit_key in room.exits:
        neighbour = world.get(exit_key)
        assert room.key in neighbour.exits, (
            f"{room.key} leads to {neighbour.key}, but {neighbour.key} has no way back"
        )


@pytest.mark.parametrize("room", ALL_ROOMS, ids=ids)
def test_items_are_in_the_catalogue(room: Room) -> None:
    """Items and locks name real items from ITEM_CATALOGUE."""
    for item_key in room.items:
        assert item_key in ITEM_CATALOGUE, (
            f"{room.key} contains {item_key!r}; add it to ITEM_CATALOGUE in inventory.py"
        )
    if room.requires is not None:
        assert room.requires in ITEM_CATALOGUE, (
            f"{room.key} needs {room.requires!r}; add it to ITEM_CATALOGUE in inventory.py"
        )


def test_every_room_is_reachable_from_the_start() -> None:
    """No room is stranded: walking from the start can reach all of them."""
    seen: set[str] = set()
    frontier = [STARTING_ROOM]
    while frontier:
        key = frontier.pop()
        if key in seen:
            continue
        seen.add(key)
        frontier.extend(world.get(key).exits)

    stranded = {room.key for room in ALL_ROOMS} - seen
    assert not stranded, f"these rooms cannot be walked to: {sorted(stranded)}"
