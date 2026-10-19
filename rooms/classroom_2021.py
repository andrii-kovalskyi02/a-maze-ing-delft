"""room/US1j Classroom 2.021- #162 Issue #162."""

from __future__ import annotations

from models import Area, Inspectable, Room
from world import register

ROOM = Room(
    key="classroom_2021",
    name="Classroom 2.021",
    area=Area.RED,
    description=(
        "You push the door to Classroom 2.021 open.",
        0.6,
        "The silence sounds different in here... like the room itself is holding its breath.",
        0.7,
        "Every chair is still tucked neatly under its desk.",
        0.5,
        "Too tidy for a room that just emptied out in a hurry.",
        0.5,
        "So quiet you can hear the clock ticking",
    ),
    return_description="The same spotless room. The clock is still ticking.",
    look_around=(
        "The whiteboard is covered edge to edge in tiny, obsessive handwriting,",
        0.6,
        "One chair by the window is knocked over...",
        0.5,
        "The only thing out of place in an otherwise spotless room.",
    ),
    exits=("corridor_red",),
    requires=None,
    locked_text="shouldnt see this",
    inspectables=(
        Inspectable(
            name="the whiteboard",
            text=(
                "Someone filled every inch of board space with the same seven digits over and over",
                0.6,
                "Its just the numbers written faster and messier toward the bottom, like whoever",
                0.4,
                " wrote them ran out of room... or time.",
            ),
        ),
    ),
    items=(),
)
register(ROOM)
