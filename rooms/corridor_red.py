"""The Red Corridor connecting the main east-west hallway to the red wing."""

from __future__ import annotations

from models import Area, Room
from world import register

ROOM = Room(
    key="corridor_red",
    name="The Red corridor",
    area=Area.RED,
    description="A long, straight corridor with a bunch of rooms on both sides.",
    look_around=(
        "You can see numerous badges and nameplates with room names next to each "
        "door, while flickering overhead lights hum quietly along the hallway."
    ),
    exits=("corridor_blue", "front_desk_office"),
    requires="fire_extinguisher"
)

register(ROOM)
