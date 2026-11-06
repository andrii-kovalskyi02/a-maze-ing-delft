"""The map: an ASCII plan of the 2nd floor (issue #120).

The plan is a drawing of the real 2nd floor of THUAS Delft: :data:`PLAN` below is the map.
The only thing that changes while playing is that the player's room is shaded, by
:func:`_shade`: it finds the room's label (from :data:`ON_THE_PLAN`) in the drawing and floods
outwards until it hits a wall character. Doorways are drawn ``X``, which counts as a wall, so the
shading never leaks into the next room, and no line or column numbers are needed anywhere.

Adding a room to the plan means drawing its box and adding one line to :data:`ON_THE_PLAN`. A
registered room that is missing from the plan is listed underneath it. Every line fits in
:data:`ui.WIDTH`, so the plan can be printed with :func:`ui.say`.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import ui
import world

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game

#: The 2nd floor, drawn with WEST at the top. Edit this and the map changes.
#: Given a little breathing room around the busier boxes (the classrooms,
#: the corridors, the lobby); the smaller, single-purpose rooms stay tight.
PLAN = """\
 +--------------------------+---------------------------------+
 |                          |                                 |
 |  Classroom 2.031         |  Classroom 2.035                |
 |                          |                                 |
 +-----------X--------------+---------------X-----------------+
 |                                                            |
 |   b l u e    c o r r i d o r                               |
 |                                                            |
 +----X----+----X----+=========+------------------------------+
 |Teachers | Stair   |         X Storage                      |
 |Room 4   | exit    |         |                              |
 +---------+---------+         +------------------------------+
 | Classroom 2.021   X   red   X Project room 3               |
 |                   |         |                              |
 |                   |         +------------------------------+
 |                   |  corr.  X Equinox student society      |
 +-------------------+         +------------------------------+
 | Classroom 2.015   X         X Main Teachers Room           |
 |                   |         |                              |
 +-------------------+         |                              |
 | Front Desk Office X         |                              |
 +-------------------+=========+------------------------------+
 |                                                            |
 |   L o b b y                                                |
 |                                                            |
 |                                       +--------------------+
 |                                       X Project room 2     |
 |                                       +--------------------+
 |                                       X Project room 1     |
 +--------X----------+---------X---------+--------------------+
 |  L A B 2 . 0 0 3  |  L A B 2 . 0 0 1  |
 |                   |                   |
 +-------------------+-------------------+
"""

#: Every room drawn on the plan. The key on the left must be the room's
#: ``key``. Then two pieces of text: what the room is *labelled* on the plan
#: above, which has to appear there exactly once and is how the shading finds
#: the room, and what to *call* it in a sentence underneath. The two differ
#: because a label has to fit in a box and be spaced out to read as a room on
#: a plan, while a sentence has to read like English: the corridor labelled
#: "red" is "the red corridor" when you are standing in it.
#: Add a line here when you draw a new room.
ON_THE_PLAN: dict[str, tuple[str, str]] = {
    # the blue wing
    "classroom_2031": ("Classroom 2.031", "Classroom 2.031"),
    "classroom_2035": ("Classroom 2.035", "Classroom 2.035"),
    "corridor_blue": ("b l u e    c o r r i d o r", "the blue corridor"),
    "teachers_room_4": ("Room 4", "Teachers Room 4"),
    "stair_exit": ("Stair", "the stair exit"),
    # the red wing
    "corridor_red": ("red", "the red corridor"),
    "classroom_2021": ("Classroom 2.021", "Classroom 2.021"),
    "classroom_2015": ("Classroom 2.015", "Classroom 2.015"),
    "front_desk_office": ("Front Desk Office", "the Front Desk Office"),
    "storage": ("Storage", "the storage room"),
    "projectroom_3": ("Project room 3", "Project room 3"),
    "student_society": ("Equinox student society", "the Equinox student society"),
    "teacher_rooms": ("Main Teachers Room", "the Main Teachers Room"),
    # the east end
    "lobby": ("L o b b y", "the lobby"),
    "projectroom_2": ("Project room 2", "Project room 2"),
    "project_room_1": ("Project room 1", "Project room 1"),
    "lab_2003": ("L A B 2 . 0 0 3", "LAB2.003"),
    "lab_2001": ("L A B 2 . 0 0 1", "LAB2.001"),
}

#: What the shading cannot cross. A doorway is one of these on purpose: it is
#: what keeps one room's shading out of the next room.
WALLS = frozenset("+-|=X")

#: The room the player is standing in. It is the only thing the plan shades:
#: every other room is drawn the same, whether it has been visited, is locked,
#: or has not been built yet. The plan is a plan, not a HUD.
HERE = ":"


def render(game: Game) -> str:
    """Return the floor plan as text, ready to print.

    Args:
        game: The running game, for where the player is and what they carry.

    Returns:
        The map, as a string of at most 80 characters per line.
    """
    sheet = [list(line) for line in PLAN.rstrip("\n").split("\n")]
    _shade(sheet, _label(game.current), HERE)

    lines = [
        *("".join(line).rstrip() for line in sheet),
        "",
        *_key(),
        *_where(game),
    ]
    return "\n".join(line[: ui.WIDTH] for line in lines)


# ------------------------------------------------------------ the shading


def _label(key: str) -> str | None:
    """Return the text this room is labelled with on the plan, or None if undrawn."""
    drawn = ON_THE_PLAN.get(key)
    return drawn[0] if drawn else None


def _called(key: str) -> str:
    """Return what to call this room in a sentence.

    The plan does the naming, so that the map calls a corridor by the same
    colour the player is looking at. A room the plan does not know falls back
    to the name the room gives itself.
    """
    drawn = ON_THE_PLAN.get(key)
    return drawn[1] if drawn else world.get(key).name


def _shade(sheet: list[list[str]], label: str | None, texture: str) -> None:
    """Fill the room labelled ``label`` with ``texture``.

    Does nothing if the room is not on the plan.
    """
    found = _find(sheet, label)
    if found is None or label is None:
        return

    row, col = found
    name = range(col, col + len(label))
    for spot in _inside(sheet, found):
        line = sheet[spot[0]]
        if line[spot[1]] != " ":
            continue
        if spot[0] == row and spot[1] in name:
            continue  # a gap in the room's own name
        if _between_letters(line, spot[1]):
            continue  # the space in "Room 4"
        line[spot[1]] = texture


def _find(sheet: list[list[str]], label: str | None) -> tuple[int, int] | None:
    """Return where ``label`` starts on the plan, or None if it is not drawn."""
    if not label:
        return None
    for row, line in enumerate(sheet):
        col = "".join(line).find(label)
        if col != -1:
            return row, col
    return None


def _inside(sheet: list[list[str]], start: tuple[int, int]) -> set[tuple[int, int]]:
    """Return every square of the room that ``start`` is standing in.

    This is the flood fill. It walks outwards from one square and stops at
    walls, so the shape of the room comes from the drawing rather than from
    anything written down here - an L-shaped lobby needs no special case.
    """
    seen = {start}
    queue = deque([start])
    while queue:
        row, col = queue.popleft()
        for down, across in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            spot = (row + down, col + across)
            if spot in seen or not 0 <= spot[0] < len(sheet):
                continue
            line = sheet[spot[0]]
            if not 0 <= spot[1] < len(line) or line[spot[1]] in WALLS:
                continue
            seen.add(spot)
            queue.append(spot)
    return seen


def _between_letters(line: list[str], col: int) -> bool:
    """Return True if this square is a gap inside a word, e.g. "Room 4"."""
    before = line[col - 1] if col else " "
    after = line[col + 1] if col + 1 < len(line) else " "
    return before.isalnum() and after.isalnum()


# ----------------------------------------------------------- the small print


def _key() -> list[str]:
    """Return the lines that say what the marks on the plan mean."""
    return [f" {HERE * 4} where you are        X  a doorway"]


def _where(game: Game) -> list[str]:
    """Return the line naming the room, and any room the plan is missing."""
    lines = ["", f" You are in {_called(game.current)}."]

    sheet = [list(line) for line in PLAN.rstrip("\n").split("\n")]
    missing = [room.name for room in world.all_rooms() if _find(sheet, _label(room.key)) is None]
    if missing:
        lines.append(f" Not on the plan yet: {', '.join(sorted(missing))}.")

    twice = _drawn_twice()
    if twice:
        lines.append(f" Careful - the plan says this more than once: {', '.join(twice)}.")
    return lines


def _drawn_twice() -> list[str]:
    """Return any label that appears on the plan more than once.

    A label has to be unique or :func:`_shade` finds the wrong room and the
    map quietly lies about where the player is standing. It is the one mistake
    this file cannot spot by itself, so it is worth saying out loud - the name
    "Teachers" alone, for instance, matches Teachers Room 4 *and* the Main
    Teachers Room.
    """
    labels = {label for label, _ in ON_THE_PLAN.values()}
    return sorted(label for label in labels if PLAN.count(label) > 1)
