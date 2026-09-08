"""The room test kit.

Every room registered in ``amazing_delft/rooms/__init__.py`` is checked here
automatically.  You do not add anything to this file when you add a room - if
your room breaks one of these rules, the failure names your room.
"""

from __future__ import annotations

import pytest

from amazing_delft import rooms, world  # noqa: F401  (importing rooms registers them)
from amazing_delft.backpack import ITEM_CATALOGUE
from amazing_delft.game import STARTING_ROOM
from amazing_delft.models import Area, Room

ALL_ROOMS = world.all_rooms()


def ids(room: Room) -> str:
    """Name the room in the test report, so a failure points at its file."""
    return room.key


@pytest.mark.parametrize("room", ALL_ROOMS, ids=ids)
def test_room_introduces_itself(room: Room) -> None:
    """Every room has something to say when the player walks in and looks."""
    assert room.description.strip(), f"{room.key} has no description"
    assert room.look_around.strip(), f"{room.key} has no 'look around' text"
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
            f"{room.key} contains {item_key!r}; add it to ITEM_CATALOGUE in backpack.py"
        )
    if room.requires is not None:
        assert room.requires in ITEM_CATALOGUE, (
            f"{room.key} needs {room.requires!r}; add it to ITEM_CATALOGUE in backpack.py"
        )


@pytest.mark.parametrize("room", ALL_ROOMS, ids=ids)
def test_room_can_be_reached_by_name(room: Room) -> None:
    """The player can type the room's name, key or an alias and get there."""
    for typed in (room.key, room.name, *room.aliases):
        assert world.find(typed) is room, f"typing {typed!r} does not find {room.key}"


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
