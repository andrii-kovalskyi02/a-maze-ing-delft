"""Tests for key-card gating of the red corridor and the lobby (issue #112).

Acceptance criteria:
- A locked door blocks every room in the area behind it, with a clear message.
- A key card opens exactly one door, and stays in the backpack afterwards.
- The corridor's go destination list grows as areas open.
- The player cannot soft-lock: the key card for the next door is always reachable in the
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


def test_red_corridor_is_locked_without_the_red_card(console) -> None:
    """Entering the red corridor without the red key card is blocked with a clear message."""
    game = start()
    game.move_to("corridor_blue")

    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "corridor_red"))
    game.turn()

    assert game.current == "corridor_blue"
    assert "red key card" in console.output.lower()


def test_lobby_is_locked_without_the_yellow_card(console) -> None:
    """Entering the lobby from the red corridor without the yellow key card is blocked."""
    game = start()
    game.unlocked.add("corridor_red")
    game.move_to("corridor_red")

    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "lobby"))
    game.turn()

    assert game.current == "corridor_red"
    assert "yellow key card" in console.output.lower()


def test_the_red_card_opens_exactly_one_door_and_is_kept(console) -> None:
    """The red key card opens the red corridor, stays in the backpack, and opens no other door."""
    game = start()
    game.move_to("corridor_blue")
    game.carrying.add("red_card")

    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "corridor_red"))
    game.turn()

    assert game.current == "corridor_red"
    assert "red_card" in game.carrying
    assert "corridor_red" in game.unlocked
    assert "red key card up to the reader" in console.output.lower()

    # The door stays open: back to blue and into red again
    game.move_to("corridor_blue")
    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "corridor_red"))
    game.turn()
    assert game.current == "corridor_red"

    # The red card does not open the lobby
    assert "lobby" not in game.unlocked
    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "lobby"))
    game.turn()
    assert game.current == "corridor_red"
    assert "yellow key card" in console.output.lower()


def test_the_yellow_card_opens_the_lobby(console) -> None:
    """The yellow key card, found in the red area, opens the lobby."""
    game = start()
    game.unlocked.add("corridor_red")
    game.move_to("corridor_red")
    game.carrying.add("yellow_card")

    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "lobby"))
    game.turn()

    assert game.current == "lobby"
    assert "lobby" in game.unlocked
    assert "yellow key card up to the reader" in console.output.lower()

    game.move_to("corridor_red")
    console.lines.clear()
    console.script(option(game, "Go through a door"), door_option(game, "lobby"))
    game.turn()
    assert game.current == "lobby"


def test_each_card_is_in_exactly_one_room() -> None:
    """The red card is in teachers room 4 (blue area), the yellow card in storage (red area)."""
    assert [r.key for r in world.all_rooms() if "red_card" in r.items] == ["teachers_room_4"]
    assert [r.key for r in world.all_rooms() if "yellow_card" in r.items] == ["storage"]
    assert world.get("teachers_room_4").area == Area.BLUE
    assert world.get("storage").area == Area.RED


def test_no_soft_lock_blue_area_has_the_red_card() -> None:
    """Blue area provides the red card without requiring access to Red or Yellow."""
    staff_room = world.get("teachers_room_4")
    assert "red_card" in staff_room.items
    assert staff_room.area == Area.BLUE
    # The blue card is in classroom_2031 in the blue area
    bp_room = world.get("classroom_2031")
    assert bp_room.area == Area.BLUE
    assert bp_room.boss is not None
    assert bp_room.boss.lose_reward_2 == "blue_card"


def test_no_soft_lock_red_area_has_the_yellow_card() -> None:
    """Red area provides the yellow card without requiring access to Yellow."""
    storage_room = world.get("storage")
    assert "yellow_card" in storage_room.items
    assert storage_room.area == Area.RED
    # The storage key is in front_desk_office in the red area
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
