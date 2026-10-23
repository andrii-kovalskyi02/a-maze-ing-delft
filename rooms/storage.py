"""US1h - Room: Storage (Issue #42)."""

from __future__ import annotations

from models import Area, Inspectable, Room, Unless
from world import register

ROOM = Room(
    key="storage",
    name="Storage Room",
    area=Area.RED,
    description="A cramped, windowless storage room that smells of cedar, oil, and cardboard.",
    look_around=(
        "Metal shelves line the walls, packed with cleaning supplies and spare parts.",
        Unless(
            "axe_key",
            (
                0.6,
                "On a sturdy workbench near the back rests a heavy axe.",
                0.4,
                "It looks sharp and ready for emergencies.",
            ),
        ),
        Unless("yellow_card", (0.4, "A yellow key card lies on a shelf beside the door.")),
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
                "Galvanized steel shelving, loaded with spare cables.",
                0.4,
                "Also boxes of fluorescent tubes and bottles of industrial floor cleaner.",
            ),
        ),
    ),
    items=("axe_key", "yellow_card"),
)

register(ROOM)
