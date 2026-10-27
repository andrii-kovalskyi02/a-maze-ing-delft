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


def test_a_flowing_window_adds_no_pause_between_lines(console) -> None:
    ui.set_flowing(True)
    try:
        console.pauses.clear()
        ui.narrate(("One.", 1.5, "Two.", "Three."))
    finally:
        ui.set_flowing(False)
    assert 1.5 not in console.pauses
    assert ui.PART_DELAY not in console.pauses


def test_without_a_flowing_window_the_pauses_stay(console) -> None:
    console.pauses.clear()
    ui.narrate(("One.", 1.5, "Two.", "Three."))
    assert 1.5 in console.pauses
    assert ui.PART_DELAY in console.pauses


def test_a_flowing_window_does_not_wait_before_a_menu(console) -> None:
    ui.set_flowing(True)
    try:
        console.pauses.clear()
        ui.pause(0.4)
    finally:
        ui.set_flowing(False)
    assert console.pauses == []


def test_a_terminal_still_waits_before_a_menu(console) -> None:
    console.pauses.clear()
    ui.pause(0.4)
    assert console.pauses == [0.4]


def test_the_typing_speed_goes_round_slow_normal_fast_instant(console) -> None:
    assert ui.text_speed() == "Slow"
    seen = [ui.cycle_text_speed() for _ in range(4)]
    assert seen == ["Normal", "Fast", "Instant", "Slow"]


def test_each_speed_types_at_its_own_pace(console) -> None:
    delays = {}
    for name, _delay in ui.SPEEDS:
        while ui.text_speed() != name:
            ui.cycle_text_speed()
        delays[name] = ui.CHAR_DELAY
        assert ui.is_instant() == (name == "Instant")
    assert delays["Slow"] > delays["Normal"] > delays["Fast"] > 0
    assert delays["Instant"] == delays["Normal"]  # unused: instant types nothing


def test_the_old_instant_switch_still_works(console) -> None:
    ui.set_instant(True)
    assert ui.text_speed() == "Instant"
    ui.set_instant(False)
    assert ui.text_speed() == "Slow"
    assert not ui.is_instant()


def test_a_new_game_starts_at_the_slow_speed(console) -> None:
    ui.cycle_text_speed()
    ui.use_io(console.write, console.read, sleep=console.pauses.append)
    assert ui.text_speed() == "Slow"


def test_a_speakers_mood_changes_how_fast_they_type(console) -> None:
    waits: dict[str, float] = {}
    for mood in ("speaking", "smiling", "upset"):
        with ui.speaking("steve", mood):
            waits[mood] = ui.CHAR_DELAY * ui._pace
    assert waits["upset"] < waits["speaking"] < waits["smiling"]


def test_the_pace_goes_back_to_normal_when_the_speaker_stops(console) -> None:
    with ui.speaking("steve", "upset"):
        assert ui._pace < 1.0
    assert ui._pace == 1.0


def test_no_speaker_leaves_the_pace_alone(console) -> None:
    with ui.speaking(None, "upset"):
        assert ui._pace == 1.0


def test_the_backpack_always_talks_at_the_same_pace_whatever_its_mood(console) -> None:
    paces = set()
    for mood in ("speaking", "smiling", "upset"):
        with ui.speaking("backpack", mood):
            paces.add(ui._pace)
    assert paces == {1.0}
    assert ui.pace_for("backpack", "upset") == ui.pace_for("backpack", "smiling") == 1.0
    assert ui.pace_for("steve", "upset") < 1.0
