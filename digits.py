"""The four digits of the exit code, and the door that asks for them (#116).

This is the spine of the game. Four digits are hidden on the floor, one per
passage, and together they open the stairs exit:

====== ====================================== ======
Colour Where it comes from                    Story
====== ====================================== ======
blue   scratched into the exit doorframe      US1e
red    Classroom 2.015 - the Drunk German     US1f
yellow LAB 2.001 - the forest boss            US1p
final  Project room 3 - the Memory Keeper     US1l
====== ====================================== ======

A digit is an ordinary :class:`~models.Item` with a ``colour`` and a ``value`` (see
``ITEM_CATALOGUE`` in ``inventory.py``), so it is picked up and carried like any other item, and
cannot be collected twice. The code is not written down anywhere: it is assembled from the
digits in :data:`ORDER`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import inventory

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game
    from models import Item

#: The colours of the four digits, in the order the door reads them.
ORDER: tuple[str, ...] = ("blue", "red", "yellow", "final")

#: Shown in place of a digit the player has not found yet.
BLANK = "_"


def all_digits() -> tuple[Item, ...]:
    """Return every digit in the game, in the order the door reads them."""
    by_colour = {
        item.colour: item for item in inventory.ITEM_CATALOGUE.values() if item.value is not None
    }
    return tuple(by_colour[colour] for colour in ORDER if colour in by_colour)


def code() -> str:
    """Return the code that opens the exit door."""
    return "".join(digit.value or BLANK for digit in all_digits())


def carried(game: Game) -> tuple[Item, ...]:
    """Return the digits the player has found so far, in colour order."""
    return tuple(digit for digit in all_digits() if digit.key in game.carrying)


def missing(game: Game) -> tuple[str, ...]:
    """Return the colours of the digits the player has still to find."""
    found = {digit.colour for digit in carried(game)}
    return tuple(colour for colour in ORDER if colour not in found)


def assemble(game: Game) -> str:
    """Return the code as the player can key it in right now.

    Every digit they are carrying, in colour order, with :data:`BLANK` where
    one is still missing - so ``"1_74"`` means the red digit is the gap.
    """
    return "".join(
        digit.value or BLANK if digit.key in game.carrying else BLANK for digit in all_digits()
    )


def is_complete(game: Game) -> bool:
    """Return True if the player is carrying all four digits."""
    return not missing(game)


def opens_the_door(game: Game) -> bool:
    """Return True if what the player can key in is the code the door wants."""
    return is_complete(game) and assemble(game) == code()


def summary(game: Game) -> str:
    """Return one line for the backpack: the code so far, and what is missing.

    The player reads this instead of writing the digits down on paper.
    """
    if is_complete(game):
        return f"The code: {assemble(game)}. You have every digit."
    still_missing = ", ".join(missing(game))
    return f"The code so far: {assemble(game)}. Still missing: {still_missing}."
