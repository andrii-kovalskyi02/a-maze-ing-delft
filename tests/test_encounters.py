"""The boss engine (enabler #104) and what a fight costs (#108, E5.2).

Every boss in the design document has a quirk, and E4.3 asks for a test per
quirk. They are all here, written against made-up bosses rather than against
anybody's room: a room's questions are its owner's to rewrite, and no test of
the engine should fail because somebody improved a joke.
"""

from __future__ import annotations

import encounters
import health
import rooms  # noqa: F401  (importing rooms registers them)
from game import Game
from health import Health
from models import Boss, Question, typing_attack


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
    assert not encounters.run(Game(), boss(questions=(question,)))


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

    assert not encounters.run(Game(), boss(questions=(question,)))
    assert encounters.TOO_SLOW.casefold() in console.output


def test_a_timed_question_is_won_by_being_quick(console) -> None:
    question = typing_attack("photosynthesis", seconds=10)
    console.script("photosynthesis")
    console.take_seconds(9)
    assert encounters.run(Game(), boss(questions=(question,)))


def test_a_wrong_answer_to_a_boss_costs_a_whole_heart(console) -> None:
    """E5.2: the penalty the design document gives for a boss."""
    game = Game()
    console.script("wrong")
    assert not encounters.run(game, boss())
    assert game.hearts == Health().lose(health.BOSS)


def test_a_wrong_answer_to_a_side_quest_costs_half_a_heart(console) -> None:
    """E5.2: a side quest is worth half of what a boss is."""
    game = Game()
    console.script("wrong")
    assert not encounters.run(game, boss(side_quest=True))
    assert game.hearts == Health().lose(health.SIDE_QUEST)


def test_running_out_of_time_costs_the_same_as_getting_it_wrong(console) -> None:
    """E5.2: "if not completed" and "answered wrongly" cost the same."""
    game = Game()
    console.script("photosynthesis")
    console.take_seconds(30)
    assert not encounters.run(game, boss(questions=(typing_attack("photosynthesis", 5),)))
    assert game.hearts == Health().lose(health.BOSS)


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


def test_running_out_of_hearts_ends_the_run(console) -> None:
    """E5.3: the team's decision - the last heart ends the play-through."""
    game = Game(hearts=Health(health.BOSS))
    game.enter()
    console.script("wrong")
    encounters.run(game, boss())
    assert game.hearts.is_empty

    game._collapse_if_out_of_hearts()
    assert not game.running
    assert "last heart" in console.output


def test_a_run_with_hearts_left_carries_on(console) -> None:
    """The other half of E5.3: nothing ends while there is a heart left."""
    game = Game()
    console.script("wrong")
    encounters.run(game, boss())
    game._collapse_if_out_of_hearts()
    assert game.running
