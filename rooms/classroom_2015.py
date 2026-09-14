from __future__ import annotations

from world import register

from models import Area, Boss, Inspectable, Question, Room

ROOM = Room(
    # room ID
    key="classroom_2015",
    name="classroom.2015",
    area=Area.RED,
    description="This place feels odd. What kind of makeshift furniture tarp tent is that? ",
    look_around=(
        "The furniture-tent takes up most of the room, and it smells like "
        "woodsmoke and spilled beer. Something about it feels familiar, like "
        "a campsite you've been to before. A whiteboard still reads "
        "'Intercultural Collaboration' in someone's handwriting. Beer cans "
        "are scattered across the floor, and there's a small fireplace "
        "burning in the corner."
    ),
    exits=("corridor_red",),
    requires="Axe_key",
    locked_text="A washed-out locked door, it looks like its on its last legs."
    "If only there was a way to break it open ",
    inspectables=(
        Inspectable(
            name="the furniture-pile / tent",
            text=(
                "A tent, built out of stacked chairs and tables. and a single tarp."
                " It looks surprisingly sturdy. Someone has clearly done this before."
            ),
        ),
        Inspectable(
            name="whiteboard",
            text=" It looks like someone has written 'Intercultural Collaboration' on it"
            " but the smoke residue is making it hard to see",
        ),
        Inspectable(
            name="fireplace",
            text="A small campfire, somehow burning safely in the middle of a classroom."
            "You decide not to ask why or how.",
        ),
        Inspectable(
            name="cans of beer scattered around",
            text="Beer cans, scattered everywhere. Several brands, all empty.",
        ),
        Inspectable(
            name="an odd smell",
            text="Woodsmoke, spilled beer, and something else - familiar,"
            "though you can't place it.",
        ),
    ),
    items=(),
    #   I still need to make it so that the boss fight starts after inspecting furniture-pile
    #
    #
    boss=Boss(
        name="The drunk german",
        intro="Inspecting the furniture-pile, you hear a rustle - and a "
        "Bavarian guy in full traditional dress ducks out of the "
        "makeshift tent, beer in hand, swaying slightly. You recognise "
        "him from somewhere - a campsite, maybe? That's why this room "
        "looked familiar. He squints at you, then grins. You want the "
        "digit? Answer me about my culture first.",
        questions=(
            Question(
                prompt="When is the Oktoberfest usually held?",
                answers=("september", "october", "september/october", "september and october"),
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
            ),
            Question(
                prompt="What do people traditionally wear at Oktoberfest?",
                answers=("b", "Dirndl and Lederhose"),
                choices=(
                    "Dresses und embroidered shirts",
                    "Dirndl und Lederhose",
                    "Trachten jackets und suits",
                    "Hanbok und lederhosen",
                ),
            ),
        ),
        win_text="Gut gemacht, here your digit. Bis später",
        lose_text="nein, nein, nein, you have to stay ",
        reward="digit_2",
    ),
)

register(ROOM)
# register(classroom_2015)
