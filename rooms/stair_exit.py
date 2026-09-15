from __future__ import annotations

from world import register

from models import Area, Boss, Inspectable, Question, Room

ROOM = Room(

    key="stair_exit",
    name="Stair Exit",
    area=Area.BLUE,
    description="The stairs leading to the main exit.",
    look_around=("should never see this"),
    exits=("corridor_blue",),
    requires="digit_4",
    locked_text="The exit is locked. A 4 digit pin is needed to unlock.",
    inspectables=(
        Inspectable(name="poster", text="A fire evacuation poster, curling at the corners."),
    ),

    items=(),
    boss=None,
    approach_reward_text="Something is scratched into the doorframe: a single digit, \"1\".... You decide to pick it up",
    approach_reward="digit_1",
)
register(ROOM)
