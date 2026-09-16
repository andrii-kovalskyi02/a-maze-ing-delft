"""US1m - the Lobby, hub of the yellow area (issue #56).

SKELETON. Just enough to connect LAB2.003 to the rest of the floor. Whoever
picks up US1m writes the real text, the blocked-exit inspectable, and the
doors to the other yellow rooms.
"""

from __future__ import annotations

from models import Area, Room
from world import register

ROOM = Room(
    key="lobby",
    name="The Lobby",
    area=Area.YELLOW,
    description="A wide lobby at the top of the main stairs, thick with smoke.",
    exits=("corridor_red", "lab_2003"),
)

register(ROOM)
