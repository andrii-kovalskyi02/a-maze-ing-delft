"""The window is told who is talking, so it can show their face."""

from __future__ import annotations

import narrator
import ui
import world
from game import Game


def watch() -> list[tuple[str | None, str]]:
    """Start listening for speaker changes; return the list they are written to."""
    seen: list[tuple[str | None, str]] = []
    ui.set_speaker_handler(lambda who, mood: seen.append((who, mood)))
    return seen


def test_speaking_says_who_starts_and_stops(console) -> None:
    seen = watch()
    try:
        with ui.speaking("backpack", "upset"):
            ui.narrate("Hello.")
    finally:
        ui.set_speaker_handler(None)
    assert seen == [("backpack", "upset"), (None, "")]
    assert "hello." in console.output


def test_nobody_is_announced_when_there_is_no_speaker(console) -> None:
    seen = watch()
    try:
        with ui.speaking(None):
            ui.narrate("The wind blows.")
    finally:
        ui.set_speaker_handler(None)
    assert seen == []


def test_the_speaker_is_cleared_even_if_the_text_fails(console) -> None:
    seen = watch()
    try:
        try:
            with ui.speaking("backpack"):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
    finally:
        ui.set_speaker_handler(None)
    assert seen[-1] == (None, "")


def test_a_terminal_without_a_window_ignores_it(console) -> None:
    ui.set_speaker_handler(None)
    with ui.speaking("backpack", "smiling"):
        ui.narrate("Fine.")
    assert "fine." in console.output


def test_the_backpack_remarks_carry_their_mood(console) -> None:
    narrator.speak_up()
    game = Game()
    game.carrying.add("backpack")
    seen = watch()
    try:
        narrator.remark(game, "locked_again")  # speaks every time, and is smug about it
        for _ in range(3):  # "took" speaks on every third, and complains
            narrator.remark(game, "took", what="key")
    finally:
        ui.set_speaker_handler(None)
    assert seen == [
        ("backpack", "smiling"),
        (None, ""),
        ("backpack", "upset"),
        (None, ""),
    ]


def test_every_remark_has_a_mood_the_window_has_a_face_for() -> None:
    for event, remark in narrator.REMARKS.items():
        assert remark.mood in ("speaking", "smiling", "upset"), event


def test_the_backpack_boss_speaks_with_its_face() -> None:
    boss = world.get("classroom_2031").boss
    assert boss is not None
    assert boss.speaker == "backpack"


def test_looking_at_something_in_the_backpack_is_the_backpack_speaking(console) -> None:
    from commands import do_backpack

    game = Game()
    game.carrying.add("backpack")
    game.carrying.add("blue_card")
    seen = watch()
    try:
        console.script("1")  # the blue card: the backpack is not in its own list
        do_backpack(game)
    finally:
        ui.set_speaker_handler(None)
    assert ("backpack", "speaking") in seen
    assert seen[-1] == (None, "")
    assert "staff key card" in console.output


def test_the_backpack_greets_a_player_who_comes_back_to_a_save(console) -> None:
    game = Game(current="corridor_blue")
    game.carrying.add("backpack")
    game.visited.add("corridor_blue")
    game.resumed = True
    seen = watch()
    try:
        game.enter()
    finally:
        ui.set_speaker_handler(None)
    out = console.output
    assert "== the blue corridor ==" in out
    assert "right where you left off... in the blue corridor." in out
    assert "far too many doors" not in out  # the room does not describe itself again
    assert "you have been here before" not in out
    assert ("backpack", "speaking") in seen
    assert game.resumed is False


def test_the_greeting_only_comes_once(console) -> None:
    game = Game(current="classroom_2031")
    game.carrying.add("backpack")
    game.resumed = True
    game.enter()
    console.lines.clear()
    game.enter()
    assert "right where you left off" not in console.output


def test_without_the_backpack_the_room_describes_itself_as_usual(console) -> None:
    game = Game(current="corridor_blue")
    game.resumed = True
    game.enter()
    assert "right where you left off" not in console.output
    assert "far too many doors" in console.output


def test_resuming_a_saved_game_from_the_start_screen_greets_you(console) -> None:
    import main
    import persistence

    game = Game(player_name="Kru", current="classroom_2031")
    game.carrying.add("backpack")
    game.visited.add("classroom_2031")
    persistence.save_game(game)

    console.script("Kru")  # the name, then nobody is at the keyboard any more
    main.main()
    out = console.output
    assert "welcome back, kru!" in out
    assert "right where you left off... in classroom 2.031." in out


def test_the_backpack_is_not_listed_in_itself(console) -> None:
    from commands import do_backpack

    game = Game()
    game.carrying.add("backpack")
    game.carrying.add("blue_card")
    console.script("0")
    do_backpack(game)
    out = console.output
    assert "blue key card" in out
    assert "1) the evil backpack" not in out
    assert "evil backpack" not in out


def test_an_empty_backpack_says_so_instead_of_listing_itself(console) -> None:
    from commands import do_backpack

    game = Game()
    game.carrying.add("backpack")
    seen = watch()
    try:
        do_backpack(game)  # no answer is needed: there is nothing to choose
    finally:
        ui.set_speaker_handler(None)
    assert "there is nothing in here but me" in console.output
    assert ("backpack", "upset") in seen


def test_only_what_a_boss_says_gets_its_voice_not_the_narration(console) -> None:
    import encounters
    from models import Boss, says

    boss = Boss(
        name="the Kicker",
        speaker="kicker",
        intro=(
            "The table shudders to life.",
            0.4,
            says("PENALTY.", 0.3, "SHOOTOUT."),
            "A ball appears.",
        ),
        questions=(),
        win_text="x",
        lose_text="x",
    )
    seen = watch()
    try:
        encounters._tell(boss, boss.intro, "speaking")
    finally:
        ui.set_speaker_handler(None)
    # the speaker is announced once, for the spoken part only, and cleared straight after
    assert seen == [("kicker", "speaking"), (None, "")]
    out = console.output
    assert "the table shudders to life." in out
    assert "penalty." in out
    assert "a ball appears." in out


def test_a_boss_with_no_marked_lines_is_all_narration(console) -> None:
    import encounters
    from models import Boss

    boss = Boss(
        name="b", speaker="b", intro="Plain text.", questions=(), win_text="x", lose_text="x"
    )
    seen = watch()
    try:
        encounters._tell(boss, boss.intro, "speaking")
    finally:
        ui.set_speaker_handler(None)
    assert seen == []


def test_says_reads_as_plain_text_for_the_tests_and_the_console(console) -> None:
    from models import plain, says

    assert plain(("a", says("b", 0.3, "c"), "d")) == "a b c d"
    ui.narrate(("one", says("two")))
    assert "one" in console.output and "two" in console.output
