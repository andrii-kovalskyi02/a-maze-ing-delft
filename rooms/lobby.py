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
        "thick with drifting smoke.",
    ),
    look_around=(
        "Yellow-accented signs and glass partitions define this central hub.",
        0.6,
        "Doors lead to the computer labs, but the main central staircase down "
        "to the ground floor is blocked by heavy smoke and fallen debris.",
    ),
    exits=("corridor_red", "lab_2001", "lab_2003"),
    requires="fire_extinguisher",
    locked_text=(
        "A wall of raging fire and thick smoke blocks the way into the lobby. "
        "You need a fire extinguisher to get through."
    ),
    is_hallway=True,
)

register(ROOM)
