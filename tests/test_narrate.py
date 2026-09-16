"""Story text is typed out bit by bit, with pauses between its parts."""

from __future__ import annotations

import ui
from models import plain


def test_a_single_string_is_shown_without_pausing(console) -> None:
    ui.narrate("Hello there.")
    assert console.lines == ["Hello there."]
    assert console.pauses == []


def test_parts_are_separated_by_the_default_pause(console) -> None:
    ui.narrate(("First.", "Second."))
    assert console.lines == ["First.", "Second."]
    assert console.pauses == [ui.PART_DELAY]


def test_a_number_is_a_pause_of_that_many_seconds(console) -> None:
    ui.narrate(("The ghost looks up.", 1.5, "'Let's begin.'"))
    assert console.lines == ["The ghost looks up.", "'Let's begin.'"]
    assert console.pauses == [1.5]


def test_long_parts_are_still_wrapped(console) -> None:
    ui.narrate(("word " * 40,))
    screen_lines = console.output.split("\n")
    assert len(screen_lines) > 1
    assert all(len(line) <= ui.WIDTH for line in screen_lines)


def test_plain_joins_the_parts_and_drops_the_pauses() -> None:
    assert plain(("One.", 2, "Two.")) == "One. Two."
    assert plain("Just one.") == "Just one."
    assert plain(None) == ""
