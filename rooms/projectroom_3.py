"""Project Room 3 and its Memory Keeper encounter."""

import memories
from models import Area, Boss, Inspectable, Question, Room
from world import register

QUESTIONS = (
    Question(
        # This room's own clock — the twin of the one in 2.035 (see memories.py).
        prompt="What time does the clock in Project Room 3 show?",
        answers=(memories.CLOCK_TIME,),
        seconds=20,
    ),
    Question(
        # Answer lives in memories.py: this is what was on the desk in 2.035,
        # not something found in this room. Read from there so the two rooms
        # can never drift apart.
        prompt="What did you find on your desk in classroom 2.035?",
        answers=(memories.DESK_CONTENTS,),
        seconds=20,
    ),
    Question(
        prompt="What did you find inside the storage room?",
        answers=("axe",),
        seconds=20,
    ),
    Question(
        prompt="In which room was the second digit?",
        answers=("classroom2015",),
        seconds=20,
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
        seconds=15,
    ),
)

ROOM = Room(
    key="projectroom_3",
    name="Project Room 3",
    area=Area.RED,
    requires="brass_key",
    description="The room feels strangely familiar, though you can't say why.",
    look_around=(
        "A clock on the wall shows 23:17.",
        0.6,
        'A whiteboard displays the word "REMEMBER".',
        0.6,
        "A laptop sits on a nearby desk, and the desk feels familiar.",
        0.6,
        "The Memory Keeper watches you silently.",
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
        intro=(
            "The Memory Keeper steps forward",
            0.6,
            "he asks you to prove what you remember.",
        ),
        questions=QUESTIONS,
        win_text=(
            "Correct. Now you remember.",
            0.5,
            "You were sitting at the desk, working on your project.",
            0.4,
            "You were looking at the clock...",
            0.5,
            "And then you fell asleep.",
        ),
        lose_text="The Memory Keeper shakes its head. You cannot remember enough.",
        reward="digit_4",
    ),
)

register(ROOM)
