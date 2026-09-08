"""US1a - Classroom 2.035, where the player wakes up (issue #1).

This is the worked example.  If you are about to build a room, read this file
next to ``_template.py``: this is what a finished one looks like.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from amazing_delft import ui
from amazing_delft.models import Area, Inspectable, Room
from amazing_delft.world import register

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from amazing_delft.game import Game


def wake_up(game: Game) -> None:
    """Run the wake-up sequence, once, the first time the player arrives.

    Most rooms need nothing like this. This one does, because the game has to
    explain why a student is asleep in a classroom during a fire alarm.
    """
    ui.say()
    ui.say("Your cheek is stuck to the desk. The fire alarm is still screaming.")
    ui.say("Everyone else is gone. Their chairs are pushed back at odd angles.")


ROOM = Room(
    key="classroom_2035",
    name="Classroom 2.035",
    area=Area.BLUE,
    description="A lecture room in the blue wing, empty except for you.",
    look_around=(
        "Rows of desks face a whiteboard nobody wiped. The projector is still "
        "warm and throwing a blank rectangle onto the wall. A clock ticks above "
        "the door, somehow audible over the alarm. Your own backpack sits on "
        "the chair beside you, and someone has left a laptop two desks along."
    ),
    exits=("corridor_ew",),
    aliases=("2.035", "classroom 2.035", "2035"),
    inspectables=(
        Inspectable(
            name="clock",
            text="Half past four. You have been asleep for two and a half hours.",
        ),
        Inspectable(
            name="laptop",
            text=(
                "Not yours. The screen shows an unsaved document titled "
                "'evacuation procedure v3 FINAL final'."
            ),
        ),
        Inspectable(
            name="whiteboard",
            text="Formulas, half erased. In the corner, in red: DO NOT USE THE LIFT.",
        ),
    ),
    items=("blue_card",),
    on_first_enter=wake_up,
)

register(ROOM)
