"""US-status (Project Guide 3.1): name, time played, and world completion.

The percentage is the game's completion metric, so it counts every room in
the world graph - finished or still a skeleton - not just what is playable
today. A room with no boss counts once it is walked into; a room with a boss
only counts once that boss is resolved (game.defeated), so peeking at a boss
and walking away is not "done". Checking status must never cost a turn or a
heart.
"""

from __future__ import annotations

import time

import commands
import rooms  # noqa: F401  (importing rooms registers them)
import world
from commands import build_menu, do_status
from game import Game
from inventory import ITEM_CATALOGUE


def start() -> Game:
    """Return a game that has been walked into, ready for a turn."""
    game = Game()
    game.enter()
    return game


def option(game: Game, label: str) -> str:
    """Return the number the player would press for the menu line ``label``."""
    for number, item in enumerate(build_menu(game), start=1):
        if label.casefold() in item.label.casefold():
            return str(number)
    raise AssertionError(f"the menu has no option matching {label!r}")


def _some_plain_rooms(count: int) -> list[str]:
    """Return the keys of ``count`` rooms that have no boss."""
    plain = [room.key for room in world.all_rooms() if room.boss is None]
    assert len(plain) >= count, "the world needs more boss-free rooms for this test"
    return plain[:count]


def _some_boss_room() -> str:
    """Return the key of a room that has a boss."""
    for room in world.all_rooms():
        if room.boss is not None:
            return room.key
    raise AssertionError("the world needs at least one boss room for this test")


def test_status_shows_name_time_and_percentage(console, monkeypatch) -> None:
    game = Game()
    game.name = "Krug"
    game.started_at = 0.0
    monkeypatch.setattr(time, "monotonic", lambda: 125.0)  # 2:05 played

    plain_rooms = _some_plain_rooms(2)
    game.visited.update(plain_rooms)
    expected_percent = round(2 / len(world.all_rooms()) * 100)

    do_status(game)

    assert "krug" in console.output
    assert "02:05 played" in console.output
    assert f"{expected_percent}%" in console.output


def test_a_boss_room_only_counts_once_the_boss_is_resolved(console) -> None:
    """Walking up to a boss and walking away does not finish that room."""
    boss_room = _some_boss_room()

    peeked = Game()
    peeked.visited.add(boss_room)  # stood at the door, never fought
    do_status(peeked)
    percent_after_peeking = _percent_in(console.output)

    console.lines.clear()
    resolved = Game()
    resolved.visited.add(boss_room)
    resolved.defeated.add(boss_room)  # fought it - won, or lost to a single_attempt boss
    do_status(resolved)
    percent_after_resolving = _percent_in(console.output)

    assert percent_after_resolving > percent_after_peeking


def _percent_in(output: str) -> int:
    """Pull the whole-number percentage out of a rendered status line."""
    import re

    match = re.search(r"(\d+)% of the floor explored", output)
    assert match, f"no percentage found in {output!r}"
    return int(match.group(1))


def test_percentage_counts_skeleton_rooms_too(console) -> None:
    """The completion metric is the whole world graph, not the finished rooms."""
    game = Game()
    game.visited.update(["classroom_2035"])

    do_status(game)

    # A skeleton room like the lobby still counts in the denominator, so
    # visiting one room out of everything registered is well under 100%.
    assert len(world.all_rooms()) > 1
    assert "100% of the floor explored" not in console.output


def test_status_shows_hearts_and_digits_collected(console) -> None:
    game = Game()
    digit_keys = [key for key in ITEM_CATALOGUE if key.startswith("digit_")]
    game.carrying.add(digit_keys[0])

    do_status(game)

    assert f"hearts: {game.hearts}" in console.output
    assert f"digits: 1/{len(digit_keys)}" in console.output


def test_status_is_reachable_from_options_on_any_turn(console) -> None:
    game = start()
    console.script(option(game, "Options"), option_from(game, "Status"), "0")
    game.turn()
    assert "explored" in console.output


def option_from(game: Game, label: str) -> str:
    """Return the number for ``label`` inside the Options submenu."""
    for number, item in enumerate(commands.options_menu(game), start=1):
        if label.casefold() in item.label.casefold():
            return str(number)
    raise AssertionError(f"Options has no choice matching {label!r}")


def test_status_does_not_cost_a_turn_or_a_heart(console) -> None:
    game = start()
    hearts_before = game.hearts
    room_before = game.current

    console.script(option(game, "Options"), option_from(game, "Status"), "0")
    game.turn()

    assert game.hearts == hearts_before
    assert game.current == room_before
    assert game.running is True


def test_opening_menu_is_unchanged_by_the_status_feature(console) -> None:
    """Status lives inside Options, so the top-level menu contract still holds."""
    assert [item.label for item in build_menu(start())] == [
        "Look around",
        "Go through a door",
        "Options",
    ]
