"""The Red Corridor connecting the main east-west hallway to the red wing."""

from __future__ import annotations

from models import Area, Room
from world import register

ROOM = Room(
    key="corridor_red",
    name="The Red corridor",
    area=Area.RED,
    description=(
        "A long, straight corridor",
        0.5,
        "with a bunch of rooms on both sides.",
    ),
    look_around=(
        "You can see numerous badges and nameplates with room names next to each door,",
        0.6,
        "while flickering overhead lights hum quietly along the hallway.",
    ),
    exits=(
        "corridor_blue",
        "front_desk_office",
        "classroom_2015",
        "projectroom_3",
        "lobby",
        "storage",
        "student_society",
        "teacher_rooms",
        "classroom_2021",
    ),
    requires="fire_extinguisher",
    locked_text=(
        "A wall of roaring fire blocks the way into the Red corridor. "
        "You need a fire extinguisher to get through."
    ),
    is_hallway=True,
)
register(ROOM)
