"""US1b - the east-west corridor (issue #7).

SKELETON.  This is the smallest room that keeps the game playable while the
foundation lands.  Whoever picks up US1b replaces the text below and adds the
evacuation-plan discovery; the shape of the file does not need to change.
"""

from __future__ import annotations

from amazing_delft.models import Area, Inspectable, Room
from amazing_delft.world import register

ROOM = Room(
    key="corridor_ew",
    name="the east-west corridor",
    area=Area.BLUE,
    description="A long corridor with glass walls and far too many doors.",
    look_around=(
        "Doors line both sides, each with a room number screwed to it. An "
        "evacuation plan hangs behind glass halfway down."
    ),
    exits=("classroom_2035", "teachers_room_4"),
    aliases=("corridor", "hallway"),
    inspectables=(
        Inspectable(
            name="evacuation plan",
            text="A floor plan of the 2nd floor. Type 'map' to look at it properly.",
        ),
    ),
)

register(ROOM)
