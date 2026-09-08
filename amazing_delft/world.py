"""The world graph: every room, and the rules for moving between them (#96).

Rooms register themselves here when their module is imported.  The engine then
enforces the locks, so no room has to check the backpack itself.
"""

from __future__ import annotations

from amazing_delft.models import Room

#: Every registered room, keyed by ``Room.key``.
_ROOMS: dict[str, Room] = {}


def register(room: Room) -> Room:
    """Add ``room`` to the world. Call this once at the bottom of a room module.

    Raises:
        ValueError: If a room with the same key is already registered.
    """
    if room.key in _ROOMS:
        raise ValueError(f"Two rooms share the key {room.key!r}. Room keys must be unique.")
    _ROOMS[room.key] = room
    return room


def get(key: str) -> Room:
    """Return the room registered under ``key``.

    Raises:
        KeyError: If no such room exists.
    """
    try:
        return _ROOMS[key]
    except KeyError:
        raise KeyError(
            f"Unknown room {key!r}. Did you register it in amazing_delft/rooms/__init__.py?"
        ) from None


def all_rooms() -> tuple[Room, ...]:
    """Return every registered room, in registration order."""
    return tuple(_ROOMS.values())


def find(text: str) -> Room | None:
    """Return the room the player meant by ``text``, or None.

    The player is allowed to be loose about it: "go 2.031", "go classroom
    2.031" and "go classroom_2031" all reach the same room.
    """
    wanted = _normalise(text)
    if not wanted:
        return None
    for room in _ROOMS.values():
        names = {_normalise(room.key), _normalise(room.name)}
        names |= {_normalise(alias) for alias in room.aliases}
        if wanted in names:
            return room
    # Nothing matched exactly, so accept an unambiguous partial match.
    partial = [room for room in _ROOMS.values() if wanted in _normalise(room.name)]
    return partial[0] if len(partial) == 1 else None


def can_enter(room: Room, backpack) -> bool:
    """Return True if the player carrying ``backpack`` may enter ``room``."""
    return room.requires is None or room.requires in backpack


def exits_of(room: Room) -> tuple[Room, ...]:
    """Return the rooms reachable from ``room``."""
    return tuple(get(key) for key in room.exits)


def _normalise(text: str) -> str:
    """Lowercase ``text`` and strip the punctuation players are loose about."""
    return text.strip().casefold().replace("_", " ").replace("-", " ").replace("  ", " ")
