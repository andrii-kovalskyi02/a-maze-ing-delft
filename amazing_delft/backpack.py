"""The item catalogue and the player's backpack (enabler #100).

Rooms refer to items by their key only, so the description of an item lives in
exactly one place: ``ITEM_CATALOGUE`` below.  Add your room's items here.
"""

from __future__ import annotations

from collections.abc import Iterator

from amazing_delft.models import Item

#: Every item in the game, keyed by the word the player types.
ITEM_CATALOGUE: dict[str, Item] = {
    item.key: item
    for item in (
        Item(
            key="note",
            name="crumpled note",
            description=(
                "A page torn from a notebook. It lists everything you can do. "
                "Type '?' to read it again at any time."
            ),
        ),
        Item(
            key="blue_card",
            name="blue key card",
            description="A staff key card. The blue stripe means the blue wing.",
        ),
        Item(
            key="fire_extinguisher",
            name="fire extinguisher",
            description="Heavy, red, and good for exactly one fire.",
            single_use=True,
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
        raise KeyError(
            f"Unknown item {key!r}. Add it to ITEM_CATALOGUE in amazing_delft/backpack.py."
        ) from None


class Backpack:
    """What the player is carrying.

    In the story this is the Evil Backpack from US1c, so it is a real object
    rather than a plain list: later it also gets to talk back.
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

    def find(self, name: str) -> Item | None:
        """Return the carried item matching ``name`` (key or display name)."""
        wanted = name.strip().casefold()
        for item in self._items:
            if wanted in (item.key.casefold(), item.name.casefold()):
                return item
        return None

    def describe(self) -> str:
        """Return the text shown by the ``backpack`` command."""
        if not self._items:
            return "Your backpack is empty."
        lines = ["You are carrying:"]
        lines += [f"  - {item.name}: {item.description}" for item in self._items]
        return "\n".join(lines)
