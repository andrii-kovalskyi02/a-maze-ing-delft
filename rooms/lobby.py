"""US1m - Room: Lobby, hub of the yellow area (issue #56)."""

from __future__ import annotations

from models import Area, Room
from world import register

ROOM = Room(
    key="lobby",
    name="The Lobby",
    area=Area.YELLOW,
    description=(
        "A spacious open lobby at the heart of the yellow wing,",
        0.5,
        "the air still and cold.",
    ),
    look_around=(
        "Yellow-accented signs and glass partitions define this central hub.",
        0.6,
        "Doors lead to the computer labs, but the main central staircase down "
        "to the ground floor is blocked by a pulled-down security shutter.",
    ),
    exits=(
        "corridor_red",
        "lab_2001",
        "lab_2003",
        "project_room_1",
        "projectroom_2",
    ),
    requires="yellow_card",
    locked_text=(
        "The reader beside the door blinks amber. You need a yellow key card to get into the lobby."
    ),
    is_hallway=True,
)

register(ROOM)
