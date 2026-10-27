"""The boss engine (enabler #104) and what a fight costs (#108, E5.2).

Every boss in the design document has a quirk, and E4.3 asks for a test per
quirk. They are all here, written against made-up bosses rather than against
anybody's room: a room's questions are its owner's to rewrite, and no test of
the engine should fail because somebody improved a joke.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

import commands
import encounters
import health
import persistence
import rooms  # noqa: F401  (importing rooms registers them)
import ui
import world
from game import Game
from health import Health
from models import Area, Boss, Question, Room, typing_attack


def boss(**changes) -> Boss:
    """Return a plain one-question boss, changed however the test needs."""
    fields = {
        "name": "the Test Boss",
        "intro": "It looks at you.",
        "questions": (Question(prompt="1 + 1?", answers=("2",)),),
        "win_text": "You win.",
        "lose_text": "You lose.",
    }
    return Boss(**(fields | changes))


def test_a_boss_tells_its_intro_once(console) -> None:
    console.script("2")
    encounters.run(Game(), boss())
    assert console.output.count("it looks at you.") == 1


def test_an_open_question_ignores_case_and_spacing(console) -> None:
    """E4.1: the one place the player types words must not be picky about them."""
    console.script("  TWO ")
    assert encounters.run(Game(), boss(questions=(Question("1 + 1?", ("two",)),)))


def test_a_multiple_choice_question_is_answered_with_a_number(console) -> None:
    """E4.1: 3 or 4 options, picked by number like everything else."""
    question = Question("Colour?", ("blue",), choices=("red", "blue", "green", "grey"))
    console.script("2")
    assert encounters.run(Game(), boss(questions=(question,)))


def test_a_question_with_no_right_answer_cannot_be_won(console) -> None:
    """US1c: the Evil Backpack's last question. Any answer loses."""
    question = Question("What is the deep state of ↸∷ᒷᔑᒲ?", answers=())
    console.script("anything at all")
    with pytest.raises(health.OutOfHearts):
        encounters.run(Game(hearts=Health(health.BOSS)), boss(questions=(question,)))


def test_an_untimed_question_can_be_thought_about_for_as_long_as_you_like(console) -> None:
    """US1c: the Evil Backpack's questions have no clock on them."""
    console.script("2")
    console.take_seconds(600)
    assert encounters.run(Game(), boss())


def test_a_timed_question_is_lost_by_being_slow(console) -> None:
    """E4.1: a right answer that arrives too late is still a loss."""
    question = typing_attack("photosynthesis", seconds=10)
    console.script("photosynthesis")
    console.take_seconds(11)

    with pytest.raises(health.OutOfHearts):
        encounters.run(Game(hearts=Health(health.BOSS)), boss(questions=(question,)))
    assert encounters.TOO_SLOW.casefold() in console.output


def test_a_timed_question_is_won_by_being_quick(console) -> None:
    question = typing_attack("photosynthesis", seconds=10)
    console.script("photosynthesis")
    console.take_seconds(9)
    assert encounters.run(Game(), boss(questions=(question,)))


def test_a_wrong_answer_to_a_boss_costs_a_whole_heart(console) -> None:
    """E5.2: the penalty the design document gives for a boss."""
    game = Game()
    console.script("wrong", "2")
    assert encounters.run(game, boss())
    assert f"hearts: {Health().lose(health.BOSS)}".casefold() in console.output


def test_a_wrong_answer_to_a_side_quest_costs_half_a_heart(console) -> None:
    """E5.2: a side quest is worth half of what a boss is."""
    game = Game()
    console.script("wrong", "2")
    assert encounters.run(game, boss(side_quest=True))
    assert f"hearts: {Health().lose(health.SIDE_QUEST)}".casefold() in console.output


def test_running_out_of_time_costs_the_same_as_getting_it_wrong(console) -> None:
    """E5.2: "if not completed" and "answered wrongly" cost the same."""
    game = Game(hearts=Health(health.BOSS))
    console.script("photosynthesis")
    console.take_seconds(30)
    with pytest.raises(health.OutOfHearts):
        encounters.run(game, boss(questions=(typing_attack("photosynthesis", 5),)))


def test_being_cut_off_by_the_clock_costs_the_same_as_getting_it_wrong(
    console, monkeypatch
) -> None:
    """E4.1: in a real terminal the clock stops the player mid-answer."""

    def clock_runs_out(*args, **kwargs) -> str:
        raise ui.TimedOut

    monkeypatch.setattr(ui, "ask", clock_runs_out)
    game = Game(hearts=Health(health.BOSS))
    with pytest.raises(health.OutOfHearts):
        encounters.run(game, boss(questions=(typing_attack("photosynthesis", 5),)))
    assert encounters.TOO_SLOW.casefold() in console.output


def test_quit_can_be_typed_in_the_middle_of_a_fight(console) -> None:
    """US2: quit works at every prompt, including a boss's question."""
    console.script("quit", "1")
    ui.set_quit_handler(commands.confirm_quit)
    try:
        with pytest.raises(ui.QuitRequested):
            encounters.run(Game(), boss())
    finally:
        ui.set_quit_handler(None)


def test_beating_a_boss_gives_a_heart_back(console) -> None:
    """E5.2: a full heart for a boss, half for a side quest, capped at three."""
    game = Game(hearts=Health(2))
    console.script("2")
    assert encounters.run(game, boss())
    assert game.hearts == Health(2).gain(health.BOSS)

    game = Game(hearts=Health(2))
    console.script("2")
    assert encounters.run(game, boss(side_quest=True))
    assert game.hearts == Health(2).gain(health.SIDE_QUEST)


def test_a_fight_the_story_means_you_to_lose_costs_nothing(console) -> None:
    """US1c: losing to the Evil Backpack is the plot, not a mistake."""
    game = Game()
    console.script("anything")
    unwinnable = boss(
        questions=(Question("No answer exists.", answers=()),),
        single_attempt=True,
        lose_reward="backpack",
    )
    assert not encounters.run(game, unwinnable)
    assert game.hearts == Health()
    assert "backpack" in game.carrying


def test_hearts_are_shown_before_the_fight_starts(console) -> None:
    """#108: the player sees what they are risking before they risk it."""
    console.script("2")
    encounters.run(Game(), boss())
    assert f"hearts: {Health()}".casefold() in console.output


def test_losing_the_last_heart_stops_the_fight_there_and_then(console) -> None:
    """#217: the last heart goes, the boss has its say, and the fight is over."""
    game = Game(hearts=Health(health.BOSS))
    console.script("wrong")
    with pytest.raises(health.OutOfHearts):
        encounters.run(game, boss())
    assert game.hearts.is_empty
    assert "you lose." in console.output


def test_a_run_with_hearts_left_carries_on(console) -> None:
    """The other half of E5.3: nothing ends while there is a heart left."""
    game = Game()
    console.script("wrong")
    with pytest.raises(EOFError):  # it asks the same question again: nobody left to answer
        encounters.run(game, boss())
    assert not game.hearts.is_empty


def test_a_wrong_answer_asks_the_same_question_again(console) -> None:
    questions = (Question("1 + 1?", ("2",)), Question("2 + 2?", ("4",)))
    console.script("2", "wrong", "4")
    assert encounters.run(Game(), boss(questions=questions))
    assert console.output.count("question 2 of 2") == 2
    assert encounters.TRY_AGAIN.casefold() in console.output


def _arena(monkeypatch) -> Room:
    """Register a made-up room with the test boss in it, for this test only."""
    arena = Room(
        key="test_arena",
        name="Test Arena",
        area=Area.BLUE,
        description="A room built for this test.",
        look_around="Bare walls.",
        boss=boss(),
    )
    monkeypatch.setitem(world._ROOMS, arena.key, arena)
    return arena


def test_running_out_of_hearts_with_no_save_ends_the_run(console, monkeypatch) -> None:
    """#217, E5.3: with nothing to go back to, the last heart ends the run at once.

    Nothing more is scripted: one more menu would read past the end of the
    script and say "nobody at the keyboard" instead.
    """
    game = Game(player_name="Tester", current=_arena(monkeypatch).key)
    game.hearts = Health(health.BOSS)

    console.script("1", "1", "wrong")  # look around, get closer, answer wrong
    game.run()

    assert not game.running
    assert "last heart" in console.output
    assert "nobody at the keyboard" not in console.output


def test_running_out_of_hearts_goes_back_to_the_save_on_full_hearts(console, monkeypatch) -> None:
    """#217: dying sends the player back to their last save, hearts restored."""
    arena = _arena(monkeypatch)
    saved = Game(player_name="Tester", current="classroom_2035")
    saved.hearts = Health(health.BOSS)
    saved.visited = {"classroom_2035"}
    persistence.save_game(saved)

    game = Game(player_name="Tester", current=arena.key, hearts=Health(health.BOSS))
    game.carrying.add("brass_key")  # picked up after the save: lost with the death
    console.script("1", "1", "wrong")
    game.run()

    assert "last heart" in console.output
    assert game.current == "classroom_2035"
    assert game.hearts == Health()
    assert "brass_key" not in game.carrying
    reloaded = persistence.load_game("Tester")
    assert reloaded is not None
    assert reloaded.hearts == Health()


def test_pausing_mid_question_resumes_on_that_question(console, monkeypatch) -> None:
    questions = (Question("1 + 1?", ("2",)), Question("2 + 2?", ("4",)))
    arena = _arena(monkeypatch)
    monkeypatch.setitem(world._ROOMS, arena.key, replace(arena, boss=boss(questions=questions)))
    game = Game(player_name="Tester", current=arena.key)
    console.script("1", "1", "2", "pause")  # look around, get closer, answer 1, pause at 2
    game.run()

    saved = persistence.load_game("Tester")
    assert saved is not None and saved.in_question == 1

    console.lines.clear()
    console.script("4")  # straight back to question 2: no menu, no intro
    saved.resumed = True
    saved.run()
    assert "question 1 of 2" not in console.output
    assert "question 2 of 2" in console.output
    assert "it looks at you." not in console.output
    assert arena.key in saved.defeated
    assert saved.in_question is None
