"""room/us1f-classroom-2015. Issue #30."""

from __future__ import annotations

from models import Area, Boss, Inspectable, Question, Room, says
from world import register

ROOM = Room(
    # room ID
    key="classroom_2015",
    name="Classroom 2.015",
    area=Area.RED,
    description=(
        "This place feels odd.",
        0.5,
        "What kind of makeshift furniture tarp tent is that?",
    ),
    return_description="The tent still stands. Woodsmoke and spilled beer, same as before.",
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
    locked_text="A washed-out locked door, it looks like its on its last legs. "
    "If only there was a way to break it open.",
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
            name="cans of beer scattered around",
            text="Beer cans, scattered everywhere. Several brands, all empty.",
        ),
    ),
    items=(),
    #   I still need to make it so that the boss fight starts after inspecting furniture-pile
    #   Bosstrigger
    #
    boss=Boss(
        name="The drunk german",
        speaker="german",
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
            says("You want the digit? Answer me about my culture first."),
        ),
        questions=(
            Question(
                prompt="When is the Oktoberfest usually held?",
                answers=(
                    "september",
                    "october",
                    "september/october",
                    "september and october",
                ),
                seconds=20,
            ),
            Question(
                prompt="Name a German beer. Come on... you must know ONE!",
                answers=(
                    "augustiner",
                    "tegernseer",
                    "paulaner",
                    "franziskaner",
                    "becks",
                    "beck's",
                    "warsteiner",
                    "erdinger",
                    "spaten",
                    "hofbräu",
                    "löwenbräu",
                    "bitburger",
                    "krombacher",
                    "andechs",
                ),
                seconds=20,
            ),
            Question(
                prompt="What traditional food is often eaten with beer in a beer hall (Bier-Zelt)?",
                answers=("Sauerkraut", "Pretzel mit Obatzda"),
                choices=(
                    "Pretzel with Obatzda",
                    "Bratwurst",
                    "Sauerkraut",
                    "Bavarian potato salad",
                ),
                seconds=15,
            ),
            Question(
                prompt="What do people traditionally wear at Oktoberfest?",
                answers=(
                    "b",
                    "Dirndl and Lederhose",
                    "Dirndl und Lederhose",
                ),
                choices=(
                    "Dresses und embroidered shirts",
                    "Dirndl und Lederhose",
                    "Trachten jackets und suits",
                    "Hanbok und lederhosen",
                ),
                seconds=15,
            ),
        ),
        win_text=(says("Gut gemacht, here your digit. Bis später"),),
        lose_text=(says("nein, nein, nein, you have to stay "),),
        reward="digit_2",
    ),
)

register(ROOM)
# register(classroom_2015)
