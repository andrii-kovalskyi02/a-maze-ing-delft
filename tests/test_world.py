"""The world graph and its locks (enabler #96)."""

from __future__ import annotations

import rooms  # noqa: F401  (importing rooms registers them)
import world
from inventory import Inventory
from models import Area, Room


def test_a_locked_room_needs_its_item() -> None:
    staff_room = world.get("teachers_room_4")
    empty = Inventory()
    assert not world.can_enter(staff_room, empty)

    with_card = Inventory()
    with_card.add("blue_card")
    assert world.can_enter(staff_room, with_card)


def test_an_unlocked_room_needs_nothing() -> None:
    assert world.can_enter(world.get("corridor_blue"), Inventory())


def test_registering_the_same_key_twice_is_refused() -> None:
    """A duplicate key would silently hide one teammate's room behind another's."""
    duplicate = Room(
        key="classroom_2035",
        name="Not really",
        area=Area.BLUE,
        description="x",
        look_around="x",
    )
    try:
        world.register(duplicate)
    except ValueError as error:
        assert "unique" in str(error)
    else:  # pragma: no cover - only reached if the guard is broken
        raise AssertionError("registering a duplicate room key should raise")
