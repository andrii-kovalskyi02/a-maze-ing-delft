"""The world graph and its locks (enabler #96)."""

from __future__ import annotations

from amazing_delft import rooms, world  # noqa: F401  (importing rooms registers them)
from amazing_delft.backpack import Backpack
from amazing_delft.models import Area, Room


def test_find_is_forgiving_about_how_a_room_is_typed() -> None:
    assert world.find("2.035") is world.get("classroom_2035")
    assert world.find("  CLASSROOM 2.035 ") is world.get("classroom_2035")
    assert world.find("classroom-2035") is world.get("classroom_2035")


def test_find_returns_none_for_a_room_that_does_not_exist() -> None:
    assert world.find("the swimming pool") is None


def test_a_locked_room_needs_its_item() -> None:
    staff_room = world.get("teachers_room_4")
    empty = Backpack()
    assert not world.can_enter(staff_room, empty)

    with_card = Backpack()
    with_card.add("blue_card")
    assert world.can_enter(staff_room, with_card)


def test_an_unlocked_room_needs_nothing() -> None:
    assert world.can_enter(world.get("corridor_ew"), Backpack())


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
