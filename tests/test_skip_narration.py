"""Skipping the story text (issue #151).

The typing animation is lovely once. On a second or third run it is in the
way, so a key press dumps the rest of the text and the Options menu can turn
the typing off for good.
"""

from __future__ import annotations

import asyncio

import commands
import ui
from game import Game


def test_the_story_is_typed_out_by_default(console) -> None:
    """Nothing about the first run changes."""
    assert not ui.is_instant()
    asyncio.run(ui.narrate(("First.", 2.0, "Second.")))
    assert console.lines == ["First.", "Second."]
    assert console.pauses == [2.0]


def test_instant_text_drops_every_pause(console) -> None:
    """A player who has read it all still gets every word - just at once."""
    ui.set_instant(True)
    asyncio.run(ui.narrate(("First.", 2.0, "Second.")))
    assert console.lines == ["First.", "Second."]
    assert console.pauses == []


def test_instant_text_still_wraps(console) -> None:
    """Skipping the animation is not an excuse to print a 500-column line."""
    ui.set_instant(True)
    asyncio.run(ui.narrate("word " * 40))
    assert all(len(line) <= ui.WIDTH for line in console.output.split("\n"))


def test_the_options_menu_turns_the_typing_off_and_on(console) -> None:
    """One choice, named after what it will do next."""
    game = Game()

    assert "instantly" in commands._text_speed_label()
    asyncio.run(commands.do_text_speed(game))
    assert ui.is_instant()

    assert "Type the story out" in commands._text_speed_label()
    asyncio.run(commands.do_text_speed(game))
    assert not ui.is_instant()


def test_a_key_press_dumps_the_rest_of_the_text(console, monkeypatch) -> None:
    """The heart of it: one press, and the remaining lines land at once.

    The fake console cannot press a key, so the keyboard peek is replaced by
    one that says "yes, once" - which is what a player pressing Enter looks
    like from inside ``narrate``.
    """
    presses = iter([True])
    monkeypatch.setattr(ui, "_pressed_a_key", lambda: next(presses, False))
    # The story is only typed out when somebody is watching, and the keyboard
    # is only quietened then too, so both are pretended here. The typing has
    # to be the path under test - see pretend_somebody_is_watching.
    written = pretend_somebody_is_watching(monkeypatch)

    asyncio.run(ui.narrate(("Skip me.", 5.0, "And me.")))

    # The line being typed finishes in one go, at the press...
    assert "".join(written) == "Skip me.\n"
    # ...and everything after it lands at once, the 5 second pause included.
    assert console.lines == ["And me."]
    assert console.pauses == []
    assert next(presses, "used") == "used", "the skip was never reached"


def pretend_somebody_is_watching(monkeypatch) -> list[str]:
    """Make ``ui`` believe a real terminal is there, and collect what it writes."""
    monkeypatch.setattr(ui, "_at_a_real_terminal", lambda: True)
    monkeypatch.setattr(ui, "_sleep", lambda seconds: None)
    written: list[str] = []
    monkeypatch.setattr(ui.sys.stdout, "write", written.append)
    monkeypatch.setattr(ui.sys.stdout, "flush", lambda: None)
    return written


def test_the_story_is_typed_a_character_at_a_time(console, monkeypatch) -> None:
    """The other half of it: with nobody pressing anything, every letter is typed."""
    monkeypatch.setattr(ui, "_pressed_a_key", lambda: False)
    written = pretend_somebody_is_watching(monkeypatch)

    asyncio.run(ui.narrate("Hi."))

    assert written == ["H", "i", ".", "\n"]


def test_the_keyboard_is_left_exactly_as_it_was_found(console) -> None:
    """A terminal with the echo still off after the game would be a bug worth having.

    There is no terminal under the tests, so this asks the smaller question:
    does the switch cope with there being nothing to switch?
    """
    with ui._keys_not_echoed():
        pass


def test_starting_a_new_game_types_the_story_out_again(console) -> None:
    """Skipping is a choice about this sitting, not a change to the game."""
    ui.set_instant(True)
    ui.use_io(console.write, console.read, sleep=console.pauses.append)
    assert not ui.is_instant()
