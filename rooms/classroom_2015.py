"""room/us1f-classroom-2015. Issue #30."""

from __future__ import annotations

from models import Area, Boss, Inspectable, Question, Room
from world import register

ROOM = Room(
    # room ID
    key="classroom_2015",
    name="Classroom.2015",
    area=Area.RED,
    description=(
        "This place feels odd.",
        0.5,
        "What kind of makeshift furniture tarp tent is that?",
    ),
    look_around=(
        "The furniture-tent takes up most of the room.",
        0.4,
        "It smells like woodsmoke and spilled beer.",
        0.6,
        "Something about it feels familiar, like a campsite you've been to before.",
        0.6,
        "A whiteboard still reads 'Intercultural Collaboration' in someone's handwriting.",
        0.6,
        "Beer cans are scattered across the floor.",
        0.4,
        "There's a small fireplace burning in the corner.",
    ),
    exits=("corridor_red",),
    requires="axe_key",
    locked_text=(
        "A washed-out locked door, it looks like its on its last legs. "
        "If only there was a way to break it open."
    ),
    inspectables=(
        Inspectable(
            name="the furniture-pile / tent",
            text=(
                "A tent, built out of stacked chairs and tables, and a single tarp.",
                0.5,
                "It looks surprisingly sturdy. Someone has clearly done this before.",
            ),
        ),
        Inspectable(
            name="whiteboard",
            text=(
                "Someone has written 'Intercultural Collaboration' on it.",
                0.4,
                "The smoke residue is making it hard to see.",
            ),
        ),
        Inspectable(
            name="fireplace",
            text=(
                "A small campfire, somehow burning safely in the middle of a classroom.",
                0.5,
                "You decide not to ask why or how.",
            ),
        ),
        Inspectable(
            name="cans of beer scattered around",
            text="Beer cans, scattered everywhere. Several brands, all empty.",
        ),
        Inspectable(
            name="an odd smell",
            text=(
                "Woodsmoke and spilled beer, and something else that's familiar.",
                0.4,
                "You can't place it.",
            ),
        ),
    ),
    items=(),
    # Boss fight: The Drunk German
    boss=Boss(
        name="The drunk german",
        intro=(
            "Inspecting the furniture-pile, you hear a rustle.",
            0.5,
            "A Bavarian guy in full traditional dress ducks out of the makeshift tent.",
            0.5,
            "He's swaying slightly, beer in hand.",
            0.6,
            "You recognise him from somewhere - a campsite, maybe?",
            0.6,
            "That's why this room looked familiar.",
            0.6,
            "He squints at you, then grins.",
            0.5,
            "You want the digit? Answer me about my culture first.",
        ),
        questions=(
            Question(
                prompt="What is the capital of Germany?",
                answers=("berlin",),
                choices=(
                    "Berlin",
                    "Munich",
                    "Hamburg",
                    "Frankfurt",
                ),
                seconds=20,
            ),
            Question(
                prompt="What language is mainly spoken in Germany?",
                answers=("german",),
                choices=(
                    "German",
                    "French",
                    "Spanish",
                    "Italian",
                ),
                seconds=20,
            ),
            Question(
                prompt="What are the colours of the German flag?",
                answers=("black, red and gold",),
                choices=(
                    "Black, red and gold",
                    "Blue, white and red",
                    "Green, white and orange",
                    "Black, white and green",
                ),
                seconds=20,
            ),
            Question(
                prompt="Which traditional outfits are associated with Oktoberfest?",
                answers=("dirndl and lederhosen",),
                choices=(
                    "Dirndl and Lederhosen",
                    "Kimonos and sandals",
                    "Kilts and sweaters",
                    "Saris and scarves",
                ),
                seconds=20,
            ),
        ),
        win_text="Gut gemacht, here your digit. Bis später",
        lose_text="nein, nein, nein, you have to stay ",
        reward="digit_2",
    ),
)

register(ROOM)
