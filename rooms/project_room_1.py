"""US1n - Room: Project room 1 (Yellow area).

An unlocked project room in the yellow wing containing the LAB 2.001 key.
"""

from __future__ import annotations

from models import Area, Inspectable, Room, Unless
from world import register

ROOM = Room(
    key="project_room_1",
    name="Project room 1",
    area=Area.YELLOW,
    description=(
        "A quiet project room in the yellow wing,",
        0.5,
        "with large glass windows overlooking the lobby.",
    ),
    look_around=(
        "Whiteboards full of diagrams and architectural sketches cover the walls.",
        Unless(
            "lab_2001_key",
            ("On a table near the back, a shiny key rests next to an open notebook.",),
            after=("An open notebook lies on a table near the back.",),
        ),
    ),
    exits=("lobby",),
    inspectables=(
        Inspectable(
            name="the whiteboard",
            text="Sketches of network topologies and project milestone timelines.",
        ),
        Inspectable(
            name="the notebook",
            text="A spiral notebook with notes on plant genetics and lab equipment.",
        ),
    ),
    items=("lab_2001_key",),
)

register(ROOM)
