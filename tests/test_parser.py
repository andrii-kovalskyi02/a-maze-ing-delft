"""The parser has to forgive the player (enabler #92)."""

from __future__ import annotations

import pytest

from amazing_delft.parser import Command, parse


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("look around", Command("look around", "")),
        ("LOOK AROUND", Command("look around", "")),
        ("   look    around  ", Command("look around", "")),
        ("look", Command("look around", "")),
        ("l", Command("look around", "")),
        ("?", Command("help", "")),
        ("inventory", Command("backpack", "")),
        ("go 2.031", Command("go", "2.031")),
        ("go to classroom 2.031", Command("go", "classroom 2.031")),
        ("GO Classroom 2.031", Command("go", "classroom 2.031")),
        ("look at clock", Command("inspect", "clock")),
        ("examine clock", Command("inspect", "clock")),
        ("pick up key", Command("take", "key")),
        ("answer 42", Command("answer", "42")),
        ("quit", Command("quit", "")),
        ("exit", Command("quit", "")),
    ],
)
def test_understands_what_the_player_meant(typed: str, expected: Command) -> None:
    assert parse(typed) == expected


@pytest.mark.parametrize("typed", ["", "   ", "dance", "sing a song"])
def test_returns_none_for_nonsense(typed: str) -> None:
    """Unrecognised input is not an error - the caller prints a hint."""
    assert parse(typed) is None
