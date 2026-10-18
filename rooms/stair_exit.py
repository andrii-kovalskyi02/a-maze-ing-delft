"""The stairs down to the main exit, locked behind the four-digit code."""

from __future__ import annotations

from models import Area, Inspectable, Room
from world import register

ROOM = Room(
    key="stair_exit",
    name="Stair Exit",
    area=Area.BLUE,
    description="The stairs leading to the main exit.",
    exits=("corridor_blue",),
    is_exit=True,
    locked_text="The exit is locked. A 4 digit pin is needed to unlock.",
    inspectables=(Inspectable(name="poster", text="A notice poster, curling at the corners."),),
    items=(),
    boss=None,
    approach_reward_text=(
        'Something is scratched into the doorframe: a single digit, "1".... '
        "You decide to pick it up"
    ),
    approach_reward="digit_1",
)

register(ROOM)
