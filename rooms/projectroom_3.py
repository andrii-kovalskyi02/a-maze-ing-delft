"""Project Room 3 and its Memory Keeper encounter."""

from models import Area, Inspectable, Room
from world import register

ROOM = Room(
    key="projectroom_3",
    name="Project Room 3",
    area=Area.RED,
    description=(
        "The room feels strangely familiar, although you cannot immediately understand why."
    ),
    look_around=(
        "A clock on the wall shows 23:17. "
        'A whiteboard displays the word "REMEMBER". '
        "A laptop sits on a nearby desk, and the desk feels familiar. "
        "The Memory Keeper watches you silently."
    ),
    exits=(),
    inspectables=(
        Inspectable(
            name="the clock",
            text="The clock shows 23:17.",
        ),
        Inspectable(
            name="the whiteboard",
            text='The whiteboard displays the word "REMEMBER".',
        ),
        Inspectable(
            name="the laptop",
            text="The laptop sits open on a familiar-looking desk.",
        ),
    ),
)

register(ROOM)
