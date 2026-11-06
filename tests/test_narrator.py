"""The Evil Backpack as narrator (enabler #103).

These tests are about *when* it speaks, never about what it says: the lines
are a character's voice and somebody will rewrite them. ``conftest.py``
silences the backpack for every other test, so this file turns it back on.
"""

from __future__ import annotations

import asyncio

import pytest

import commands
import encounters
import narrator
import rooms  # noqa: F401  (importing rooms registers them)
from game import Game
from models import Boss, Question
from narrator import REMARKS, Remark


@pytest.fixture(autouse=True)
def backpack_may_speak() -> None:
    """Undo the silence the other tests run under."""
    narrator.speak_up()


def carrying_the_backpack() -> Game:
    """Return a game whose player has already lost to the Evil Backpack."""
    game = Game()
    game.carrying.add("backpack")
    return game


def test_it_says_nothing_before_classroom_2031(console) -> None:
    """#103: there is no backpack yet, so there is nobody to say anything."""
    game = Game()
    for _ in range(10):
        asyncio.run(narrator.remark(game, "hurt", who="somebody"))
    assert console.lines == []


def test_it_speaks_once_it_is_being_carried(console) -> None:
    game = carrying_the_backpack()
    asyncio.run(narrator.remark(game, "hurt", who="the Test Boss"))
    assert console.lines


def test_it_keeps_quiet_most_of_the_time(console) -> None:
    """#103: a backpack that comments on all forty pickups is one nobody reads."""
    game = carrying_the_backpack()
    every = REMARKS["took"].every
    assert every > 1, "the point of 'took' is that it is not every time"

    for _ in range(every - 1):
        asyncio.run(narrator.remark(game, "took", what="a thing"))
    assert console.lines == []

    asyncio.run(narrator.remark(game, "took", what="a thing"))
    assert console.lines


def test_it_does_not_repeat_itself(console) -> None:
    """Each time it speaks it moves on to its next line."""
    game = carrying_the_backpack()
    said = []
    for _ in range(len(REMARKS["hurt"].lines)):
        console.lines.clear()
        asyncio.run(narrator.remark(game, "hurt", who="the Test Boss"))
        said.append("\n".join(console.lines))
    assert len(set(said)) == len(said)


def test_it_can_be_silenced_completely(console) -> None:
    """#103: so no other test depends on a line somebody may rewrite."""
    game = carrying_the_backpack()
    narrator.silence()
    for _ in range(10):
        asyncio.run(narrator.remark(game, "hurt", who="somebody"))
    assert console.lines == []


def test_an_event_nobody_wrote_lines_for_is_not_a_crash(console) -> None:
    """The engine may report something before the backpack has an opinion on it."""
    asyncio.run(narrator.remark(carrying_the_backpack(), "an_event_from_the_future"))
    assert console.lines == []


def test_every_line_can_be_filled_in_from_what_the_engine_reports() -> None:
    """A ``{what}`` in a line the engine never fills in would crash mid-game.

    So each event may only use the words the engine actually passes it.
    """
    allowed = {"took": {"what"}, "hurt": {"who"}, "boss_won": {"who"}, "boss_lost": {"who"}}
    for event, remark in REMARKS.items():
        for line in remark.lines:
            line.format(**dict.fromkeys(allowed.get(event, set()), "x"))


def test_a_room_never_has_to_call_it(console) -> None:
    """#103: taking an item is enough - the room says nothing about backpacks."""
    game = carrying_the_backpack()
    took = REMARKS["took"]
    for _ in range(took.every):
        asyncio.run(game.take("evacuation_plan"))
        game.taken.clear()
    assert console.lines


def test_the_backpack_has_nothing_to_say_about_arriving(console) -> None:
    """US1c: it does not comment on the fight that handed it over."""
    console.script("anything")
    asyncio.run(
        encounters.run(
            Game(),
            Boss(
                name="the Evil Backpack",
                intro="Hello.",
                questions=(Question("No answer exists.", answers=()),),
                win_text="You win.",
                lose_text="*it attaches itself to you*",
                lose_reward="backpack",
                single_attempt=True,
            ),
        )
    )
    assert "and you thought my questions" not in console.output


def test_the_backpack_notices_a_door_that_keeps_refusing(console, monkeypatch) -> None:
    """#103: one honest try is quiet; rattling the same handle is not."""
    monkeypatch.setitem(REMARKS, "locked_again", Remark(lines=("Still locked.",)))
    game = carrying_the_backpack()
    game.current = "corridor_blue"

    console.script("2", "2")  # the teachers' room, twice, with no blue card
    asyncio.run(commands.do_go(game))
    first_try = list(console.lines)
    asyncio.run(commands.do_go(game))

    assert "still locked." not in "\n".join(first_try).casefold()
    assert "still locked." in console.output
