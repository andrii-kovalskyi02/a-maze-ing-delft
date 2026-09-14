"""Project Room 3 and its Memory Keeper encounter."""

import memories
from models import Area, Boss, Inspectable, Question, Room
from world import register

QUESTIONS = (
    Question(
        # This room's own clock — the twin of the one in 2.035 (see memories.py).
        prompt="What time does the clock in Project Room 3 show?",
        answers=(memories.CLOCK_TIME,),
    ),
    Question(
        # Answer lives in memories.py: this is what was on the desk in 2.035,
        # not something found in this room. Read from there so the two rooms
        # can never drift apart.
        prompt="What did you find on your desk in classroom 2.035?",
        answers=(memories.DESK_CONTENTS,),
    ),
    Question(
        prompt="What did you find inside the storage room?",
        answers=("axe",),
    ),
    Question(
        prompt="In which room was the second digit?",
        answers=("classroom2015",),
    ),
    Question(
        # This is the one memories.py calls out as answered only by the
        # laptop notification in 2.035 ("Project deadline: Tomorrow.").
        prompt="What were you doing before you fell asleep?",
        answers=("working on your project", "your project"),
        choices=(
            "Working on your project",
            "Reading a book",
            "Watching a movie",
            "Doing homework",
        ),
    ),
)

ROOM = Room(
    key="projectroom_3",
    name="Project Room 3",
    area=Area.RED,
    requires="brass_key",
    description=(
        "The room feels strangely familiar, although you cannot immediately understand why."
    ),
    look_around=(
        "A clock on the wall shows 23:17. "
        'A whiteboard displays the word "REMEMBER". '
        "A laptop sits on a nearby desk, and the desk feels familiar. "
        "The Memory Keeper watches you silently."
    ),
    exits=("corridor_red",),
    inspectables=(
        Inspectable(
            name="the clock",
            text="The clock shows 23:17.",
        ),
        Inspectable(
            name="the whiteboard",
            text='The whiteboard displays the word "REMEMBER".',
        ),
        Inspectable(
            name="the laptop",
            text="The laptop sits open on a familiar-looking desk.",
        ),
    ),
    boss=Boss(
        name="the Memory Keeper",
        intro="The Memory Keeper steps forward and asks you to prove what you remember.",
        questions=QUESTIONS,
        win_text=(
            "Correct. Now you remember. You were sitting at the desk, "
            "working on your project, looking at the clock... and then "
            "you fell asleep."
        ),
        lose_text="The Memory Keeper shakes its head. You cannot remember enough.",
        # NOTE: "digit_4" is a guess at the naming convention for the digit
        # items — confirm this matches whatever key the other boss rooms use
        # (e.g. classroom_2015's boss, lab_0_1's boss) before merging.
        reward="digit_4",
    ),
)

register(ROOM)
