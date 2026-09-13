"""Tests for Project Room 3 and its Memory Keeper encounter (US1l, #55).

Assumes pytest, and that ``projectroom_3`` and ``memories`` import the same
way they do in the room module itself. Adjust the import path below if your
project nests rooms under a package (e.g. ``rooms.projectroom_3``).
"""

from __future__ import annotations

import memories
from models import Area
from rooms.projectroom_3 import ROOM


def test_room_metadata() -> None:
    assert ROOM.key == "projectroom_3"
    assert ROOM.area is Area.RED
    assert ROOM.requires == "brass_key"


def test_room_has_no_exits_yet() -> None:
    # Left empty on purpose until #52 wires up the map connection.
    assert ROOM.exits == ()


def test_boss_exists_and_has_five_questions() -> None:
    boss = ROOM.boss
    assert boss is not None
    assert boss.name == "the Memory Keeper"
    assert len(boss.questions) == 5


def test_clock_question_matches_shared_memory() -> None:
    """Question 1 must always agree with 2.035's clock (the twist)."""
    clock_question = ROOM.boss.questions[0]
    assert clock_question.is_correct(memories.CLOCK_TIME)
    assert clock_question.is_correct("23:17")
    assert not clock_question.is_correct("00:00")


def test_desk_note_question_matches_shared_memory() -> None:
    """Question 2 is about 2.035's desk, not this room — must read from memories."""
    desk_question = ROOM.boss.questions[1]
    assert desk_question.is_correct(memories.DESK_CONTENTS)
    assert desk_question.is_correct("A NOTE")  # case/whitespace-insensitive


def test_no_duplicate_note_question() -> None:
    """Regression test: Q2 and Q5 both used to ask about the note. They must not."""
    desk_answers = [q for q in ROOM.boss.questions if q.is_correct(memories.DESK_CONTENTS)]
    assert len(desk_answers) == 1


def test_laptop_question_is_answerable() -> None:
    laptop_question = ROOM.boss.questions[4]
    assert laptop_question.is_correct("working on your project")
    assert laptop_question.choices  # multiple-choice, per design (5 questions = boss)


def test_boss_reward_is_the_final_digit() -> None:
    assert ROOM.boss.reward == "digit_4"


def test_win_and_lose_text_present() -> None:
    assert ROOM.boss.win_text
    assert ROOM.boss.lose_text
