"""The numbered menu, which is the only thing the player ever uses."""

from __future__ import annotations

import pytest

import ui


def test_choosing_returns_the_index(console) -> None:
    console.script("2")
    assert ui.choose("Pick:", ["first", "second", "third"]) == 1


def test_the_options_are_numbered_from_one(console) -> None:
    console.script("1")
    ui.choose("Pick:", ["first", "second"])
    assert "1) first" in console.output
    assert "2) second" in console.output


def test_zero_goes_back_when_offered(console) -> None:
    console.script("0")
    assert ui.choose("Pick:", ["first"], back="Never mind") is None
    assert "0) never mind" in console.output


def test_zero_is_not_accepted_when_there_is_no_way_back(console) -> None:
    console.script("0", "1")
    assert ui.choose("Pick:", ["first"]) == 0


@pytest.mark.parametrize("typed", ["", "  ", "banana", "9", "-1", "1.5", "quit"])
def test_anything_that_is_not_a_number_on_the_list_asks_again(typed: str, console) -> None:
    """The player cannot get stuck: a bad answer just shows the list again."""
    console.script(typed, "1")
    assert ui.choose("Pick:", ["first", "second"]) == 0
    assert "type the number" in console.output


def test_running_out_of_input_is_not_a_crash(console) -> None:
    """A real terminal raises EOFError at end of input; so does the fake one."""
    with pytest.raises(EOFError):
        ui.choose("Pick:", ["first"])
