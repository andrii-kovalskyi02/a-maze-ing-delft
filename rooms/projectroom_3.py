"""Project Room 3 and its Memory Keeper encounter."""

from models import Area, Boss, Inspectable, Question, Room, Unless, says
from world import register

QUESTIONS = (
    Question(
        prompt="What time does the clock in Project Room 3 show?",
        answers=("23:17",),
        choices=(
            "23:17",
            "08:30",
            "12:00",
            "18:45",
        ),
        seconds=20,
    ),
    Question(
        prompt="What word is written on the whiteboard?",
        answers=("remember",),
        choices=(
            "REMEMBER",
            "WELCOME",
            "ESCAPE",
            "FORGET",
        ),
        seconds=20,
    ),
    Question(
        prompt="What did you find inside the storage room?",
        answers=("axe",),
        choices=(
            "Axe",
            "Flashlight",
            "Book",
            "First-aid kit",
        ),
        seconds=20,
    ),
    Question(
        prompt="In which room was the second digit?",
        answers=("Classroom 2015",),
        choices=(
            "Classroom 2015",
            "Classroom 2035",
            "Project Room 1",
            "Front Office",
        ),
        seconds=20,
    ),
    Question(
        prompt="What object is sitting on the desk in Project Room 3?",
        answers=("laptop",),
        choices=(
            "Laptop",
            "Backpack",
            "Book",
            "Clock",
        ),
        seconds=20,
    ),
)

ROOM = Room(
    key="projectroom_3",
    name="Project Room 3",
    area=Area.RED,
    requires="brass_key",
    description="The room feels strangely familiar, though you can't say why.",
    return_description="The clock, the whiteboard, the laptop: all as you remember them.",
    look_around=(
        "A clock on the wall shows 23:17.",
        0.6,
        'A whiteboard displays the word "REMEMBER".',
        0.6,
        "A laptop sits on a nearby desk, and the desk feels familiar.",
        Unless("digit_4", (0.6, "The Memory Keeper watches you silently.")),
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
        speaker="memory_keeper",
        intro=(
            "The Memory Keeper steps forward",
            0.6,
            "he asks you to prove what you remember.",
        ),
        questions=QUESTIONS,
        win_text=(
            says(
                "Correct. Now you remember.",
                0.5,
                "You were sitting at the desk, working on your project.",
                0.4,
                "You were looking at the clock...",
                0.5,
                "And then you fell asleep.",
            ),
        ),
        lose_text="The Memory Keeper shakes its head. You cannot remember enough.",
        reward="digit_4",
    ),
)

register(ROOM)
