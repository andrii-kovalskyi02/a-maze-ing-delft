"""US1h - Room: Storage (Issue #42)."""

from __future__ import annotations

from models import Area, Inspectable, Room
from world import register

ROOM = Room(
    key="storage",
    name="Storage Room",
    area=Area.RED,
    description=(
        "A cramped, windowless storage room smelling of cedar shavings, "
        "machine oil, and damp cardboard."
    ),
    look_around=(
        "Tall metal shelves line the walls, packed tight with cleaning fluids, "
        "spare light tubes, and heavy maintenance equipment. On a sturdy workbench "
        "near the back rests a heavy fire axe and a spare fire extinguisher, "
        "sharp and ready for emergencies."
    ),
    exits=("corridor_red",),
    requires="storage_key",
    locked_text=(
        "The sturdy metal door is locked tight. A small label beside the "
        "keyhole reads 'Storage Room - Authorized Staff Only'."
    ),
    inspectables=(
        Inspectable(
            name="metal shelves",
            text=(
                "Galvanized steel shelving loaded with spare cables, boxes of fluorescent "
                "tubes, and plastic bottles of industrial floor cleaner."
            ),
        ),
        Inspectable(
            name="workbench",
            text=(
                "A scarred wooden workbench covered in dust circles, stray washers, "
                "and an empty oil can. A red fire extinguisher sits next to a heavy fire axe."
            ),
        ),
        Inspectable(
            name="cleaning cart",
            text=(
                "A yellow janitorial trolley holding a dry mop, a squeegee, "
                "and a box of heavy-duty rubber gloves."
            ),
        ),
        Inspectable(
            name="cardboard boxes",
            text=(
                "Old cardboard boxes labeled 'Building Maintenance 2024'. "
                "Inside are spare hinges, doorknobs, and rolls of caution tape."
            ),
        ),
    ),
    items=("axe_key", "fire_extinguisher"),
)

register(ROOM)
