"""US1d - Room: Teachers room 4 (the red key card) Issue #19."""

from __future__ import annotations

from models import Area, Room, Unless
from world import register

ROOM = Room(
    key="teachers_room_4",
    name="Teachers Room 4",
    area=Area.BLUE,
    description=(
        "Four desks, three coats,",
        0.4,
        "and a smell of instant coffee.",
    ),
    look_around=(
        "Somebody's marking is still spread across the nearest desk.",
        Unless("red_card", (0.7, "A red key card hangs on a hook by the window.")),
    ),
    exits=("corridor_blue",),
    requires="blue_card",
    locked_text="The reader by the door blinks red. Staff only - you need a key card.",
    items=("red_card",),
)

register(ROOM)
