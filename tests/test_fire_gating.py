"""Tests for fire-area gating and fire extinguishers (issue #112).

Acceptance criteria:
- Each wall of fire blocks go to every room in the area behind it, with a clear message.
- Using an extinguisher consumes it permanently and opens exactly one wall.
- The corridor's go destination list grows as areas open.
- The player cannot soft-lock: an extinguisher for the next wall is always reachable in the
  current area.
"""

from __future__ import annotations

import rooms  # noqa: F401
import world
from commands import build_menu
from game import Game
from models import Area


def start() -> Game:
    """Return a fresh game ready for turns."""
    game = Game()
    game.enter()
    return game


def option(game: Game, label: str) -> str:
    """Return the 1-based index matching label in the current menu."""
    for number, item in enumerate(build_menu(game), start=1):
        if label.casefold() in item.label.casefold():
            return str(number)
    raise AssertionError(f"Menu has no option matching {label!r}")


def door_option(game: Game, door_key: str) -> str:
    """Return the 1-based index for door_key from the current room's exits."""
    doors = world.exits_of(game.room)
    for idx, d in enumerate(doors, start=1):
        if d.key == door_key:
            return str(idx)
    raise AssertionError(f"No door with key {door_key!r} found in exits of {game.room.key}")


def test_fire_wall_blocks_red_corridor_without_extinguisher(console) -> None:
    """Entering the red corridor without an extinguisher is blocked with a fire message."""
    game = start()
    game.move_to("corridor_blue")

    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "corridor_red"))
    game.turn()

    assert game.current == "corridor_blue"
    assert "fire" in console.output.lower()
    assert "extinguisher" in console.output.lower()


def test_fire_wall_blocks_lobby_without_extinguisher(console) -> None:
    """Entering the lobby (yellow area) from red corridor without an extinguisher is blocked."""
    game = start()
    # Unlock red corridor directly in game state for this test
    game.unlocked.add("corridor_red")
    game.move_to("corridor_red")

    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "lobby"))
    game.turn()

    assert game.current == "corridor_red"
    assert "fire" in console.output.lower()
    assert "extinguisher" in console.output.lower()


def test_extinguisher_is_consumed_and_unlocks_one_wall(console) -> None:
    """Using an extinguisher consumes it and unlocks exactly the target wall."""
    game = start()
    game.move_to("corridor_blue")
    game.carrying.add("fire_extinguisher")
    assert "fire_extinguisher" in game.carrying

    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "corridor_red"))
    game.turn()

    assert game.current == "corridor_red"
    # Extinguisher is consumed permanently
    assert "fire_extinguisher" not in game.carrying
    assert "corridor_red" in game.unlocked
    assert "spray the fire extinguisher" in console.output.lower()

    # Player can walk back to blue and return to red without needing another extinguisher
    game.move_to("corridor_blue")
    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "corridor_red"))
    game.turn()
    assert game.current == "corridor_red"

    # Exactly one wall was unlocked: lobby is still locked by fire!
    assert "lobby" not in game.unlocked
    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "lobby"))
    game.turn()
    assert game.current == "corridor_red"
    assert "fire" in console.output.lower()


def test_second_extinguisher_opens_yellow_area(console) -> None:
    """A second extinguisher found in the red area opens the yellow area (lobby)."""
    game = start()
    game.unlocked.add("corridor_red")
    game.move_to("corridor_red")

    # Give player second extinguisher
    game.carrying.add("fire_extinguisher")
    assert "fire_extinguisher" in game.carrying

    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "lobby"))
    game.turn()

    assert game.current == "lobby"
    assert "fire_extinguisher" not in game.carrying
    assert "lobby" in game.unlocked
    assert "spray the fire extinguisher" in console.output.lower()

    # Can return to corridor_red and back to lobby without extinguisher
    game.move_to("corridor_red")
    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "lobby"))
    game.turn()
    assert game.current == "lobby"


def test_extinguishers_are_only_in_teachers_room_4_and_storage() -> None:
    """In the whole game, exactly 2 fire extinguishers exist: in teachers room 4 and storage."""
    rooms_with_extinguisher = sorted(
        room.key for room in world.all_rooms() if "fire_extinguisher" in room.items
    )
    assert rooms_with_extinguisher == ["storage", "teachers_room_4"]

    # Blue area check
    staff_room = world.get("teachers_room_4")
    assert staff_room.area == Area.BLUE

    # Red area check
    storage_room = world.get("storage")
    assert storage_room.area == Area.RED


def test_no_soft_lock_blue_area_has_reachable_extinguisher() -> None:
    """Blue area provides an extinguisher without requiring access to Red or Yellow."""
    staff_room = world.get("teachers_room_4")
    assert "fire_extinguisher" in staff_room.items
    assert staff_room.area == Area.BLUE
    # Blue card is in classroom_2031 in blue area
    bp_room = world.get("classroom_2031")
    assert bp_room.area == Area.BLUE
    assert bp_room.boss is not None
    assert bp_room.boss.lose_reward_2 == "blue_card"


def test_no_soft_lock_red_area_has_reachable_extinguisher() -> None:
    """Red area provides an extinguisher without requiring access to Yellow."""
    storage_room = world.get("storage")
    assert "fire_extinguisher" in storage_room.items
    assert storage_room.area == Area.RED
    # Storage key is in front_desk_office in red area
    office_room = world.get("front_desk_office")
    assert office_room.area == Area.RED
    assert office_room.boss is not None
    assert office_room.boss.reward == "storage_key"
    assert office_room.requires is None


def test_area_structure_enforces_intended_room_order() -> None:
    """All rooms in Red area require going through corridor_red; Yellow through lobby."""
    # From starting room, without entering corridor_red, only Blue area rooms are reachable
    blue_rooms = {r.key for r in world.all_rooms() if r.area == Area.BLUE}
    red_rooms = {r.key for r in world.all_rooms() if r.area == Area.RED}
    yellow_rooms = {r.key for r in world.all_rooms() if r.area == Area.YELLOW}

    assert "corridor_blue" in blue_rooms
    assert "corridor_red" in red_rooms
    assert "lobby" in yellow_rooms

    # Check exits from corridor_blue do not leak directly into red non-hallway or yellow rooms
    blue_corridor_exits = set(world.get("corridor_blue").exits)
    assert not (blue_corridor_exits & yellow_rooms)
    assert blue_corridor_exits & red_rooms == {"corridor_red"}

    # Check exits from corridor_red do not leak directly into yellow non-hallway rooms
    red_corridor_exits = set(world.get("corridor_red").exits)
    assert red_corridor_exits & yellow_rooms == {"lobby"}
