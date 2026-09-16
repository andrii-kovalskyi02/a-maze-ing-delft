

from __future__ import annotations

from models import Area, Room
from world import register

ROOM = Room(
    key="teachers_room_4",
    name="Teachers room 4",
    area=Area.BLUE,
    description=(
        "Four desks, three coats,",
        0.4,
        "and a smell of instant coffee.",
    ),
    look_around=(
        "Somebody's marking is still spread across the nearest desk.",
        0.7,
        "A fire extinguisher is clipped to the wall by the window.",
    ),
    exits=("corridor_blue",),
    requires="blue_card",
    locked_text="The reader by the door blinks red. Staff only - you need a key card.",
    items=("fire_extinguisher",),
)

register(ROOM)