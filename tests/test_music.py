"""The background music: which track plays, how it fades, and that it can never break the game."""

from __future__ import annotations

import asyncio
import contextlib

import pytest

import health
import music
from health import Health
from music import LEVELS, Music


class FakeBackend:
    """Stands in for the sound player and remembers what it was told."""

    def __init__(self) -> None:
        self.loaded: list[str] = []
        self.volume = 0.0
        self.playing = False
        self.loops = None
        self.fail_on_load = False

    def load(self, path: str) -> None:
        if self.fail_on_load:
            raise OSError("no such file")
        self.loaded.append(path)

    def play(self, loops: int = 0) -> None:
        self.playing = True
        self.loops = loops

    def stop(self) -> None:
        self.playing = False

    def set_volume(self, volume: float) -> None:
        self.volume = volume


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def run(self, seconds: float, music_: Music, step: float = 0.05) -> None:
        for _ in range(int(seconds / step)):
            self.now += step
            music_.update()


def make(steady: frozenset[str] | None = None) -> tuple[Music, FakeBackend, Clock]:
    backend, clock = FakeBackend(), Clock()
    files = {"intro": "intro.wav", "explore": "explore.wav", "boss": "boss.wav"}
    if steady is None:
        return Music(files, backend, clock), backend, clock
    return Music(files, backend, clock, steady=steady), backend, clock


def test_nothing_plays_until_a_track_is_wanted() -> None:
    m, backend, clock = make()
    clock.run(2, m)
    assert not backend.playing
    assert m.playing() is None


def test_a_wanted_track_starts_silent_and_fades_up_looping_for_ever() -> None:
    m, backend, clock = make()
    m.want_track("intro")
    clock.run(0.1, m)
    assert backend.playing and backend.loaded == ["intro.wav"]
    assert backend.loops == -1
    assert backend.volume < 0.05  # it starts silent
    clock.run(4, m)
    assert backend.volume > 0.15  # and comes up to the normal level (0.22)


def test_changing_track_fades_the_old_one_out_before_the_new_one_starts() -> None:
    m, backend, clock = make()
    m.want_track("intro")
    clock.run(4, m)
    full = backend.volume
    m.want_track("explore")
    clock.run(0.5, m)
    assert backend.loaded == ["intro.wav"]  # still the old one, getting quieter
    assert 0 < backend.volume < full
    clock.run(2, m)
    assert backend.loaded == ["intro.wav", "explore.wav"]
    assert m.playing() == "explore"
    clock.run(4, m)
    assert backend.volume > 0.15


def test_wanting_nothing_fades_out_and_stops() -> None:
    m, backend, clock = make()
    m.want_track("intro")
    clock.run(4, m)
    m.want_track(None)
    clock.run(3, m)
    assert not backend.playing
    assert m.playing() is None


def test_the_volume_levels_go_round_off_low_normal() -> None:
    m, backend, clock = make()
    assert m.level_name == "Normal"
    assert [m.cycle_level() for _ in range(3)] == ["Off", "Low", "Normal"]
    m.want_track("intro")
    m.cycle_level()  # Off
    clock.run(5, m)
    assert backend.volume == 0.0
    assert [name for name, _ in LEVELS] == ["Off", "Low", "Normal"]
    assert LEVELS[1][1] < LEVELS[2][1]


def test_a_track_that_is_not_steady_dips_while_text_is_typed_and_comes_back() -> None:
    m, backend, clock = make(steady=frozenset())
    m.want_track("intro")
    clock.run(6, m)
    loud = backend.volume
    m.typing()
    clock.run(0.4, m)
    assert backend.volume < loud * 0.8
    clock.run(3, m)
    assert backend.volume > loud * 0.95


def test_the_music_is_quieter_while_paused() -> None:
    m, backend, clock = make()
    m.want_track("intro")
    clock.run(6, m)
    loud = backend.volume
    m.set_paused(True)
    clock.run(3, m)
    assert backend.volume < loud * 0.6
    m.set_paused(False)
    clock.run(3, m)
    assert backend.volume > loud * 0.95


def test_a_missing_file_means_silence_not_a_crash() -> None:
    m, backend, clock = make()
    backend.fail_on_load = True
    m.want_track("intro")
    clock.run(3, m)
    assert m.playing() is None
    m.want_track("nonsense")  # a track nobody knows about
    clock.run(3, m)
    assert m.playing() is None


def test_a_sound_error_switches_the_music_off_for_good() -> None:
    m, backend, clock = make()

    def broken(volume: float) -> None:
        raise RuntimeError("the sound card went away")

    backend.set_volume = broken  # type: ignore[method-assign]
    m.want_track("intro")
    clock.run(1, m)  # must not raise
    clock.run(1, m)
    assert m.playing() is None


def test_without_a_sound_card_everything_is_a_quiet_no_op(monkeypatch) -> None:
    monkeypatch.setattr(music, "_pygame_backend", lambda: None)
    m = Music({"intro": "intro.wav"})
    m.want_track("intro")
    m.typing()
    m.set_paused(True)
    m.update()
    m.cycle_level()
    m.stop()
    assert m.playing() is None


def test_ui_cue_calls_the_handler_and_a_terminal_ignores_it(console) -> None:
    import ui

    heard: list[str] = []
    ui.cue("combat")  # no handler: nothing happens
    ui.set_cue_handler(heard.append)
    try:
        ui.cue("combat")
    finally:
        ui.set_cue_handler(None)
    assert heard == ["combat"]


def test_the_combat_cue_comes_after_the_intro_and_before_the_questions(console) -> None:
    import encounters
    import ui
    import world
    from game import Game

    boss = world.get("student_society").boss
    assert boss is not None
    game = Game(player_name="T", current="student_society")
    order: list[str] = []
    ui.set_cue_handler(lambda name: order.append(f"cue:{name} after {len(console.lines)} lines"))
    try:
        console.script("1", "1", "1", "1", "1", "1", "1", "1")  # answers, right or wrong
        with contextlib.suppress(health.OutOfHearts, EOFError):  # wrong ones are asked again
            asyncio.run(encounters.run(game, boss))
    finally:
        ui.set_cue_handler(None)
    combat = [entry for entry in order if entry.startswith("cue:combat")]
    assert len(combat) == 1
    out = console.lines
    first_question = next(
        i for i, line in enumerate(out) if "question" in line.lower() or "1)" in line
    )
    cue_line = int(combat[0].split("after ")[1].split(" ")[0])
    intro_end = next(i for i, line in enumerate(out) if "three." in line.lower())
    assert intro_end < cue_line <= first_question


def test_boss_music_starts_with_the_encounter_and_stops_when_it_ends(console) -> None:
    import encounters
    import ui
    import world
    from game import Game

    boss = world.get("student_society").boss
    assert boss is not None
    game = Game(player_name="T", current="student_society")
    heard: list[str] = []
    ui.set_cue_handler(lambda name: heard.append(f"{name}@{len(console.lines)}"))
    try:
        console.script("1", "1", "1", "1", "1", "1", "1", "1")
        with contextlib.suppress(health.OutOfHearts, EOFError):  # wrong ones are asked again
            asyncio.run(encounters.run(game, boss))
    finally:
        ui.set_cue_handler(None)
    names = [entry.split("@")[0] for entry in heard]
    assert names == ["boss_music_on", "combat", "boss_music_off"]
    assert int(heard[0].split("@")[1]) == 0  # it starts before the boss says a word
    assert int(heard[-1].split("@")[1]) == len(console.lines)  # and stops after the last line


def test_boss_music_stops_even_if_the_encounter_is_cut_short(console) -> None:
    import encounters
    import ui
    import world
    from game import Game

    boss = world.get("student_society").boss
    assert boss is not None
    game = Game(player_name="T", current="student_society")
    heard: list[str] = []
    ui.set_cue_handler(heard.append)
    try:
        with contextlib.suppress(EOFError):
            asyncio.run(
                encounters.run(game, boss)
            )  # no answers at all: the game stops waiting for one
    finally:
        ui.set_cue_handler(None)
    assert heard[0] == "boss_music_on" and heard[-1] == "boss_music_off"


def test_a_quick_change_fades_faster_than_a_normal_one() -> None:
    quick, _backend, clock = make()
    quick.want_track("intro")
    clock.run(6, quick)
    quick.want_track("boss", quick=True)
    clock.run(2.2, quick)
    assert quick.playing() == "boss"  # the old track is gone and the boss track has started

    normal, _backend2, clock2 = make()
    normal.want_track("intro")
    clock2.run(6, normal)
    normal.want_track("explore")
    clock2.run(0.9, normal)
    assert normal.playing() == "intro"  # a normal change is still fading the old track out


def test_an_instant_track_starts_at_once_at_full_volume() -> None:
    m, backend, clock = make()
    m.want_track("explore")
    clock.run(6, m)  # the exploring music is playing at its full level
    full = backend.volume
    m.want_track("boss", instant=True)
    clock.now += 0.05
    m.update()  # a single frame later
    assert m.playing() == "boss"
    assert backend.loaded[-1] == "boss.wav"
    assert backend.volume >= full * 0.95  # already at full volume, no fade-in


def test_leaving_the_boss_track_fades_in_gently_as_before() -> None:
    m, backend, clock = make()
    m.want_track("boss", instant=True)
    clock.now += 0.05
    m.update()
    m.want_track("explore")  # the fight is over: a normal change
    clock.run(1.0, m)
    assert m.playing() == "boss"  # still fading the boss track out
    clock.run(0.9, m)
    assert m.playing() == "explore"
    assert backend.volume < 0.15  # and the exploring music is still coming up


def test_the_boss_track_keeps_a_steady_volume_while_text_is_typed() -> None:
    m, backend, clock = make()
    m.want_track("boss", instant=True)
    clock.run(2, m)
    steady = backend.volume
    low = steady
    for _ in range(20):  # a lot of typing, with a letter every frame
        m.typing()
        clock.run(0.05, m)
        low = min(low, backend.volume)
    assert low >= steady * 0.99  # it never dipped
    m.set_paused(True)
    clock.run(2, m)
    assert backend.volume < steady * 0.6  # but it still goes quiet when the game is paused


def test_every_real_track_is_steady_so_typing_never_dips_the_music() -> None:
    import music as music_module

    assert {"intro", "explore", "boss"} <= music_module.STEADY_TRACKS
    for track in ("intro", "explore", "boss"):
        m, backend, clock = make()
        m.want_track(track, instant=True)
        clock.run(2, m)
        steady = backend.volume
        low = steady
        for _ in range(20):
            m.typing()
            clock.run(0.05, m)
            low = min(low, backend.volume)
        assert low >= steady * 0.99, track


def _one_question_boss(answer: str):  # noqa: ANN202
    from models import Boss, Question

    return Boss(
        name="the tester",
        intro="A test.",
        questions=(Question(prompt="Say yes.", answers=("yes",)),),
        win_text="You win.",
        lose_text="You lose.",
    )


def test_winning_plays_the_victory_jingle_just_before_the_win_text(console) -> None:
    import encounters
    import ui
    from game import Game

    game = Game(player_name="T", current="student_society")
    heard: list[str] = []
    ui.set_cue_handler(lambda name: heard.append(f"{name}@{len(console.lines)}"))
    try:
        console.script("yes")
        assert asyncio.run(encounters.run(game, _one_question_boss("yes")))
    finally:
        ui.set_cue_handler(None)
    names = [entry.split("@")[0] for entry in heard]
    assert names == ["boss_music_on", "combat", "victory", "boss_music_off"]
    victory_at = int(heard[2].split("@")[1])
    assert "You win." not in "\n".join(console.lines[:victory_at])
    assert "You win." in "\n".join(console.lines[victory_at:])


def test_losing_does_not_play_the_victory_jingle(console) -> None:
    import encounters
    import ui
    from game import Game

    game = Game(player_name="T", current="student_society", hearts=Health(health.BOSS))
    heard: list[str] = []
    ui.set_cue_handler(heard.append)
    try:
        console.script("no")
        with pytest.raises(health.OutOfHearts):  # the one heart left goes on the wrong answer
            asyncio.run(encounters.run(game, _one_question_boss("yes")))
    finally:
        ui.set_cue_handler(None)
    assert "victory" not in heard
