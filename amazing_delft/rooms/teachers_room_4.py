"""US1d - Teachers room 4, where the fire extinguisher lives (issue #19).

SKELETON.  It exists at this point only to show a locked door working: it
needs the blue key card from Classroom 2.035.  Whoever picks up US1d fills in
the rest.
"""

from __future__ import annotations

from amazing_delft.models import Area, Room
from amazing_delft.world import register

ROOM = Room(
    key="teachers_room_4",
    name="Teachers room 4",
    area=Area.BLUE,
    description="Four desks, three coats, and a smell of instant coffee.",
    look_around=(
        "Somebody's marking is still spread across the nearest desk. A fire "
        "extinguisher is clipped to the wall by the window."
    ),
    exits=("corridor_ew",),
    aliases=("teachers room", "teachers room 4", "staff room"),
    requires="blue_card",
    locked_text="The reader by the door blinks red. Staff only - you need a key card.",
    items=("fire_extinguisher",),
)

register(ROOM)
