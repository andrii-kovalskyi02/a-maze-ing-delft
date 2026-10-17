"""US1q - LAB2.003, the Steve Jobs room (issue #73).

The digital ghost of Steve Jobs guards the brass key to Project Room 3 with
four questions about Apple history. Losing is not the end: the encounter
resets, so the player can walk back up to him and try again.
"""

from __future__ import annotations

from models import Area, Boss, Inspectable, Question, Room, Unless
from world import register

ROOM = Room(
    key="lab_2003",
    name="LAB2.003",
    area=Area.YELLOW,
    description=(
        "You step into LAB2.003.",
        0.4,
        "The room is quiet.",
        0.3,
        "It's lit only by the faint blue light of dozens of computer screens.",
        0.6,
        "At the front stands a glowing, digital ghost of Steve Jobs.",
        0.4,
        "He holds a heavy brass key.",
    ),
    return_description="The monitors still glow blue, every one showing the bitten apple.",
    look_around=(
        "Rows of monitors glow blue in the dark.",
        0.4,
        "Every one of them shows the same bitten-apple logo.",
        0.6,
        "The air hums with fans.",
        Unless(
            "brass_key",
            (
                0.6,
                "At the front desk, the ghost of Steve Jobs waits in a black turtleneck.",
                0.4,
                "He's turning the brass key over in his fingers.",
            ),
        ),
    ),
    exits=("lobby",),
    inspectables=(
        Inspectable(
            name="the screens",
            text="Every screen shows the same slide: 'One more thing...'",
        ),
        Inspectable(
            name="the brass key",
            text="Old and heavy. A paper tag on it reads 'Project Room 3'.",
            gone_once_taken="brass_key",
        ),
    ),
    boss=Boss(
        name="Steve Jobs",
        intro=(
            "The ghost looks up at you.",
            1.0,
            "'To get this key to Project Room 3, you must prove you know your history.'",
            "'Let's begin.'",
        ),
        questions=(
            Question(
                prompt=(
                    "In 2007, I introduced the first iPhone. It lacked a feature "
                    "that many cannot imagine a smartphone without today. What was it?"
                ),
                answers=("App Store",),
                choices=("Maps", "Notes", "Stocks", "App Store"),
                seconds=15,
            ),
            Question(
                prompt=(
                    "I introduced the MacBook Air and wanted to show how thin it was. "
                    "So, during the presentation, I pulled it out of an object usually "
                    "used for documents. Where did I pull it from?"
                ),
                answers=("envelope", "an envelope", "manila envelope", "a manila envelope"),
                seconds=20,
            ),
            Question(
                prompt=(
                    "When Apple created the first Macintosh, one of its main features was "
                    "a device that allowed you to control the computer without typing "
                    "commands. What was it?"
                ),
                answers=("mouse", "a mouse", "the mouse"),
                seconds=20,
            ),
            Question(
                prompt=(
                    "In 1984, the Macintosh was introduced to the world through a famous "
                    "commercial inspired by George Orwell's novel. What was the name of "
                    "this commercial?"
                ),
                answers=("1984",),
                choices=("Think Different", "Big Brother", "1984", "The Crazy Ones"),
                seconds=15,
            ),
        ),
        win_text=(
            "Steve smiles and nods slowly.",
            0.8,
            "'Stay hungry. Stay foolish.'",
            0.5,
            "He places the brass key in your hand and fades into the glow of the screens.",
        ),
        lose_text=(
            "Steve shakes his head.",
            0.8,
            "'Not quite. Come back when you have done your homework.'",
            0.5,
            "The screens flicker, and he waits at the desk again as if nothing happened.",
        ),
        reward="brass_key",
    ),
)

register(ROOM)
