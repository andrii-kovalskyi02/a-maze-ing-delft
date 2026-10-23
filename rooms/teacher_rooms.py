"""Main Teachers Room - the merged Teachers Rooms 1, 2 and 3.

In the real building these were three separate rooms. For the game they are
treated as one combined space: the wall between them looks like it has been
torn down, deliberately dramatic - like something blew a hole clean through
rather than a renovation.
"""

from __future__ import annotations

from models import Area, Inspectable, Room
from world import register

ROOM = Room(
    key="teacher_rooms",
    name="Main Teachers Room",
    area=Area.RED,
    description=(
        "What used to be three separate teachers' rooms is now one long space.",
        0.4,
        "The dividing walls are gone.",
        0.5,
        "Chunks of plaster and brick are scattered across the floor.",
        0.4,
        "It looks like something blew straight through them.",
    ),
    look_around=(
        "The gaps where the walls used to be are ragged, not sawn.",
        0.4,
        "Brick and torn drywall sit at odd angles, dust over everything.",
        0.6,
        "Three desks, coat racks, and nameplates still stand in a neat row.",
        0.4,
        "They're untouched by the wreckage around them.",
        0.6,
        "Less renovation, more explosion that stopped just short of the furniture.",
    ),
    exits=("corridor_red",),
    requires=None,
    inspectables=(
        Inspectable(
            name="the torn walls",
            text="Brick and plaster, broken rather than removed. Whatever did this did it fast.",
        ),
        Inspectable(
            name="sticky note",
            text=(
                "A sticky note on one of the desks reads:",
                0.4,
                "'Reminder: submit renovation feedback form.'",
                0.5,
                "Someone has written underneath,",
                0.4,
                "'5 stars, would get blown up again.'",
            ),
        ),
    ),
)
register(ROOM)
