"""US1q - LAB2.003, the Steve Jobs room (issue #73).

The digital ghost of Steve Jobs guards the brass key to Project Room 3 with
four questions about Apple history. Losing is not the end: the encounter
resets, so the player can walk back up to him and try again.
"""

from __future__ import annotations

from models import Area, Boss, Inspectable, Question, Room
from world import register

ROOM = Room(
    key="lab_2003",
    name="LAB2.003",
    area=Area.YELLOW,
    description=(
        "You step into LAB2.003. The room is quiet, lit only by the faint blue "
        "light of dozens of computer screens.",
        "At the front, a glowing, digital ghost of Steve Jobs stands at one of "
        "the desks. He holds a heavy brass key.",
    ),
    look_around=(
        "Rows of monitors glow blue in the dark, every one of them showing the "
        "same bitten-apple logo. The air hums with fans. At the front desk the "
        "ghost of Steve Jobs waits in a black turtleneck, turning the brass key "
        "over in his fingers."
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
            "'Stay hungry. Stay foolish.' He places the brass key in your hand and "
            "fades into the glow of the screens.",
        ),
        lose_text=(
            "Steve shakes his head.",
            0.8,
            "'Not quite. Come back when you have done your homework.' The screens "
            "flicker, and he is waiting at the desk again as if nothing happened.",
        ),
        reward="brass_key",
    ),
)

register(ROOM)
