"""The map: an ASCII plan of the 2nd floor.

NOT BUILT YET - this is issue #120, and it is yours to build.

The engine already calls :func:`render` whenever the player picks "Look at the
map" from the menu, and already gives you everything you need:

* ``world.all_rooms()`` - every room, with its ``name``, ``area``
  and ``exits``
* ``game.visited`` - the keys of the rooms the player has already been in
* ``game.backpack`` - so you can tell which locked rooms are now open

Keep the whole thing inside 80 columns and change nothing outside this file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game


def render(game: Game) -> str:
    """Return the floor plan as text, ready to print.

    Args:
        game: The running game, for what the player has seen and carries.

    Returns:
        The map, as a string of at most 80 characters per line.
    """
    visited = ", ".join(sorted(game.visited)) or "nothing yet"
    return (
        "The evacuation plan is still rolled up under your arm.\n"
        f"(You have seen: {visited}.)\n"
        "Drawing it properly is issue #120."
    )
