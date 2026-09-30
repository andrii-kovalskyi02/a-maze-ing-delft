"""The item catalogue and what the player is carrying (enabler #100).

This is deliberately *not* called the backpack. The player has no backpack
when the game starts: they pick one up in classroom 2.031 (US1c), where the
Evil Backpack becomes their inventory and their narrator. Until then they are
simply carrying things in their hands.

Rooms refer to items by their key only, so the description of an item lives in
exactly one place: ``ITEM_CATALOGUE`` below. Add your room's items here.
"""

from __future__ import annotations

from collections.abc import Iterator

from models import Item

#: Every item in the game, keyed by the word the room refers to it by.
ITEM_CATALOGUE: dict[str, Item] = {
    item.key: item
    for item in (
        Item(
            key="evacuation_plan",
            name="evacuation plan",
            description=(
                "The plan of the 2nd floor, taken off the corridor wall. "
                "It shows the blue passage, and names the red and yellow ones."
            ),
        ),
        Item(
            key="brass_key",
            name="brass key",
            description="A small brass key. It looks old, but still fits a lock.",
        ),
        Item(
            key="backpack",
            name="the Evil Backpack",
            description=(
                "It has eyes, legs, and a zip for a mouth. It carries your "
                "things, and complains about it constantly."
            ),
        ),
        # The four digits of the exit code (enabler #116). ``colour`` says
        # which passage a digit belongs to and ``value`` is the character it
        # shows; the door assembles the code from these - see digits.py.
        Item(
            key="digit_4",
            name="digit 4",
            description="The fourth digit of the code.",
            colour="final",
            value="4",
        ),
        Item(
            key="digit_3",
            name="digit 3",
            description="The third digit of the code, carved into a piece of bark.",
            colour="yellow",
            value="7",
        ),
        Item(
            key="digit_1",
            name="digit 1",
            description="The first digit used to unlock exit door",
            colour="blue",
            value="1",
        ),
        Item(
            key="blue_card",
            name="blue key card",
            description="A staff key card giving you access to the Teachers room",
        ),
        Item(
            key="storage_key",
            name="storage key",
            description="A small brass key labeled 'Storage Room'.",
        ),
        Item(
            key="fire_extinguisher",
            name="fire extinguisher",
            description="Heavy, red, and good for exactly one fire.",
            single_use=True,
        ),
        Item(
            key="axe_key",
            name="Axe",
            description="A sturdy axe made out of good material",
            single_use=False,
        ),
        Item(
            key="digit_2",
            name="digit 2",
            description="A small piece of paper with a 6 or 9 on it, you can't tell",
            single_use=False,
            colour="red",
            value="9",
        ),
        Item(
            key="lab_2001_key",
            name="LAB 2.001 key",
            description="A key labeled 'LAB 2.001' that unlocks the door to LAB 2.001.",
            single_use=False,
        ),
    )
}


def get_item(key: str) -> Item:
    """Return the item registered under ``key``.

    Raises:
        KeyError: If no such item exists.  This almost always means a room
            listed an item that was never added to ``ITEM_CATALOGUE``.
    """
    try:
        return ITEM_CATALOGUE[key]
    except KeyError:
        raise KeyError(f"Unknown item {key!r}. Add it to ITEM_CATALOGUE in inventory.py.") from None


class Inventory:
    """What the player is carrying right now.

    Once the Evil Backpack has joined (US1c) this is what it holds, and the
    "Open your backpack" choice appears in the menu. Before that the player
    is carrying things in their hands and the choice is not offered.
    """

    def __init__(self) -> None:
        """Start empty."""
        self._items: list[Item] = []

    def __contains__(self, key: object) -> bool:
        """Return True if an item with this key is being carried."""
        return any(item.key == key for item in self._items)

    def __iter__(self) -> Iterator[Item]:
        """Iterate over the carried items, in the order they were picked up."""
        return iter(self._items)

    def __len__(self) -> int:
        """Return how many items are being carried."""
        return len(self._items)

    def add(self, key: str) -> Item:
        """Put the item called ``key`` in the backpack and return it."""
        item = get_item(key)
        if item.key not in self:
            self._items.append(item)
        return item

    def consume(self, key: str) -> bool:
        """Use up a single-use item.

        Returns:
            True if the item was there and has now been used up, False if the
            player was not carrying it.
        """
        for index, item in enumerate(self._items):
            if item.key == key:
                if item.single_use:
                    del self._items[index]
                return True
        return False
