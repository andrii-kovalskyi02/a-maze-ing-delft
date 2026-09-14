"""US1b - the east-west corridor (issue #7).

SKELETON. The smallest room that keeps the game playable while the foundation
lands. Whoever picks up US1b writes the real text, makes the evacuation plan a
forced pickup on the first look around, and adds the fire gating.
"""

from __future__ import annotations

from models import Area, Inspectable, Room
from world import register

ROOM = Room(
    key="corridor_blue",
    name="the east-west corridor",
    area=Area.BLUE,
    description="A long corridor with glass walls and far too many doors.",
    look_around=(
        "Doors line both sides, each with a room number screwed to it. An "
        "evacuation plan hangs on the wall halfway down."
    ),
    exits=("classroom_2035", "teachers_room_4", "corridor_red"),
    inspectables=(
        Inspectable(
            name="the evacuation plan",
            text="A plan of the 2nd floor. You could take it off the wall.",
        ),
    ),
    items=("evacuation_plan",),
)

register(ROOM)
