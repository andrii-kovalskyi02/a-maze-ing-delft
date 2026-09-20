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
    name="Teachers room",
    area=Area.RED,
    description=(
        "What used to be three separate teachers' rooms is now one long "
        "space - the dividing walls are gone, chunks of plaster and brick "
        "scattered across the floor like something blew straight through them."
    ),
    look_around=(
        "The gaps where the walls used to be are ragged, not sawn - brick "
        "and torn drywall at odd angles, dust over everything. Three desks, "
        "coat racks, and nameplates still stand in a neat row, untouched by "
        "the wreckage around them. Less renovation, more explosion that "
        "stopped just short of the furniture."
    ),
    exits=("corridor_red",),
    requires=None,
    inspectables=(
        Inspectable(
            name="the torn walls",
            text=(
                "Brick and plaster, broken rather than removed. Whatever did this did it fast."),
        ),
        Inspectable(
            name="the nameplates",
            text="Three nameplates, still lined up neatly: 'Room 1', 'Room 2', 'Room 3'.",
        ),
        Inspectable(
            name="the desks",
            text="Three desks, untouched by the wreckage around them, "
            "as if the walls avoided them on purpose.",
        ),
        Inspectable(
            name="sticky note",
            text=(
                "A sticky note on one of the desks reads: 'Reminder: submit "
                "renovation feedback form.' Someone has written underneath, "
                "'5 stars, would get blown up again.'"
            ),
        ),
    ),
)
register(ROOM)
