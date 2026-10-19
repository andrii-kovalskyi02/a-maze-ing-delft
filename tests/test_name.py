"""The player's name cannot be empty."""

from __future__ import annotations

from main import ask_name


def test_an_empty_name_is_asked_for_again(console) -> None:
    console.script("", "   ", "Kru")
    assert ask_name() == "Kru"
    assert "please enter a valid name" in console.output


def test_a_name_is_kept_without_the_spaces_round_it(console) -> None:
    console.script("  Kru ")
    assert ask_name() == "Kru"
    assert "please enter a valid name" not in console.output
