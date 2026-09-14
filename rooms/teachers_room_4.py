"""US1d - Teachers room 4, where the fire extinguisher lives (issue #19).

SKELETON. It exists at this point only to show a locked door working: it
needs the blue key card, which the player cannot have yet because it comes
from classroom 2.031 (US1c). Whoever picks up US1d fills in the rest.
"""

from __future__ import annotations

from models import Area, Room
from world import register

ROOM = Room(
    key="teachers_room_4",
    name="Teachers room 4",
    area=Area.BLUE,
    description="Four desks, three coats, and a smell of instant coffee.",
    look_around=(
        "Somebody's marking is still spread across the nearest desk. A fire "
        "extinguisher is clipped to the wall by the window."
    ),
    exits=("corridor_blue",),
    requires="blue_card",
    locked_text="The reader by the door blinks red. Staff only - you need a key card.",
    items=("fire_extinguisher",),
)

register(ROOM)
