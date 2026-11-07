"""After looking around once in a room, "Look around" becomes "Interact" until the player leaves."""

from __future__ import annotations

import asyncio

from commands import build_menu, do_look_around
from game import Game


def labels(game: Game) -> list[str]:
    return [item.label for item in build_menu(game)]


def test_the_first_time_it_is_look_around_and_it_tells_the_room(console) -> None:
    game = Game(current="corridor_blue")
    assert "Look around" in labels(game)
    console.script("0")
    asyncio.run(do_look_around(game))
    assert "doors line both sides" in console.output


def test_after_looking_it_becomes_interact_and_skips_the_telling(console) -> None:
    game = Game(current="corridor_blue")
    console.script("0")
    asyncio.run(do_look_around(game))
    assert "Look around" not in labels(game)
    assert "Interact" in labels(game)

    console.lines.clear()
    console.script("0")
    asyncio.run(do_look_around(game))  # the "Interact" choice
    assert "doors line both sides" not in console.output
    assert "take the" in console.output  # what is in the room is offered at once


def test_walking_into_another_room_starts_over(console) -> None:
    game = Game(current="corridor_blue")
    console.script("0")
    asyncio.run(do_look_around(game))
    asyncio.run(game.move_to("classroom_2035"))
    assert "Look around" in labels(game)
    assert "Interact" not in labels(game)
    asyncio.run(
        game.move_to("corridor_blue")
    )  # and coming back to the first room starts over there too
    assert "Look around" in labels(game)


def test_nothing_to_interact_with_means_no_interact_choice(console) -> None:
    lobby = Game(current="lobby")  # a hallway with nothing to look at or take
    lobby.looked_around = True
    assert "Interact" not in labels(lobby)
    office = Game(current="classroom_2035")  # a room with things to look at
    office.looked_around = True
    assert "Interact" in labels(office)
