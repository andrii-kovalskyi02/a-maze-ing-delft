"""US1a - Classroom 2.035, where the player wakes up (issue #1).

This is the worked example. If you are about to build a room, read this file
next to ``_template.py``: this is what a finished one looks like.

The three inspectable objects here - the clock, the laptop and the desk - are
**load-bearing** for the ending, each in a different way. ``memories.py``
explains which is which and holds their wording, so this room and Project
room 3 (US1l) cannot drift apart. Read it before changing any of them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import memories
import ui
from models import Area, Inspectable, Room
from world import register

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game


def wake_up(game: Game) -> None:
    """Run the wake-up sequence, once, the first time the player arrives.

    Most rooms need nothing like this. This one does, because the game has to
    explain why a student is asleep in a classroom during a fire alarm, and it
    is where the player is told how the game is played.
    """
    ui.say()
    ui.narrate("Your cheek is stuck to the desk. The fire alarm is screaming.")
    ui.narrate("Everyone else is gone. Their chairs are pushed back at odd angles.")
    ui.narrate("Somewhere below you, something is burning.")


ROOM = Room(
    key="classroom_2035",
    name="Classroom 2.035",
    area=Area.BLUE,
    description="A lecture room in the blue wing, empty except for you.",
    look_around=(
        "Rows of desks face a whiteboard nobody wiped.",
        0.6,
        "The clock above the door is somehow still audible over the alarm.",
        0.6,
        "Your own desk is the only one that looks used.",
        0.4,
        "A laptop is still lit, with something folded beside it.",
    ),
    exits=("corridor_blue",),
    inspectables=(
        Inspectable(
            name="the clock",
            text=f"It reads {memories.CLOCK_TIME}. You have been asleep for hours.",
        ),
        Inspectable(
            name="the laptop",
            text=(
                f'A notification sits in the corner of the screen: "{memories.LAPTOP_NOTIFICATION}"'
            ),
        ),
        Inspectable(
            name="the desk",
            text=(
                "The desk you fell asleep at. Beside your elbow lies "
                f"{memories.DESK_CONTENTS}, folded once, in your own handwriting. "
                "You do not remember writing it."
            ),
        ),
    ),
    on_first_enter=wake_up,
)

register(ROOM)
