"""The data types every room is built from.

A room in this game is *data*, not control flow.  You describe what your room
is, and the engine decides what happens when the player types something.  That
is why every type here is a frozen dataclass: once a room is built it cannot be
changed by accident from somewhere else in the code.

See CONTRIBUTING.md for the step-by-step recipe for adding a room.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from amazing_delft.game import Game


class Area(StrEnum):
    """The three colour-coded parts of the 2nd floor.

    Areas exist so the fire-gating enabler (issue #112) can block a whole wing
    of the building at once.  Every room belongs to exactly one area.
    """

    BLUE = "blue"
    RED = "red"
    YELLOW = "yellow"


@dataclass(frozen=True, slots=True)
class Item:
    """Something the player can carry in the backpack.

    Args:
        key: The short, lowercase name the player types, e.g. ``"blue_card"``.
        name: How the item is shown on screen, e.g. ``"blue key card"``.
        description: What the player reads when they ``inspect`` the item.
        single_use: If True the item disappears from the backpack after use.
    """

    key: str
    name: str
    description: str
    single_use: bool = False


@dataclass(frozen=True, slots=True)
class Inspectable:
    """A detail in a room the player can look at but cannot pick up.

    Args:
        name: What the player types after ``inspect``, e.g. ``"clock"``.
        text: What they read.
    """

    name: str
    text: str


@dataclass(frozen=True, slots=True)
class Question:
    """One question a boss asks.

    Args:
        prompt: The question itself.
        answers: Every answer that counts as correct.  Matching ignores case
            and surrounding whitespace, so list only meaningfully different
            answers, e.g. ``("42", "forty two")``.
        choices: For a multiple-choice question, the options to show.  Leave it
            empty for an open question.
    """

    prompt: str
    answers: tuple[str, ...]
    choices: tuple[str, ...] = ()

    def is_correct(self, given: str) -> bool:
        """Return True if ``given`` matches one of the accepted answers."""
        return given.strip().casefold() in {a.strip().casefold() for a in self.answers}


@dataclass(frozen=True, slots=True)
class Boss:
    """The challenge guarding a room.

    Args:
        name: Who the player faces, e.g. ``"the Evil Backpack"``.
        intro: What is printed when the encounter starts.
        questions: The questions asked, in order.
        win_text: What is printed when the player answers everything correctly.
        lose_text: What is printed when the player gets one wrong.
        reward: The key of the item handed over on a win, if any.
    """

    name: str
    intro: str
    questions: tuple[Question, ...]
    win_text: str
    lose_text: str
    reward: str | None = None


@dataclass(frozen=True, slots=True)
class Room:
    """One room of the building.  This is the building block you fill in.

    Args:
        key: The unique id of the room, e.g. ``"classroom_2035"``.  Other rooms
            list this in their ``exits``.
        name: How the room is shown on screen, e.g. ``"Classroom 2.035"``.
        area: Which colour-coded part of the floor the room is in.
        description: The short line printed when the player walks in.
        look_around: The longer text printed for ``look around``.
        exits: The keys of the rooms reachable from here.
        aliases: Extra things the player may type to reach this room, e.g.
            ``("2.035", "classroom 2.035")``.  ``key`` and ``name`` already
            work, so only add what they do not cover.
        requires: The key of an item needed to enter.  The engine checks the
            backpack automatically; the player never types "use key".
        locked_text: What the player reads when they lack that item.
        inspectables: Details the player can ``inspect`` here.
        items: The keys of items lying in this room, ready to be picked up.
        boss: The challenge guarding this room, if any.
        on_first_enter: An optional function run once, the first time the
            player enters.  Use it only when plain data is not enough.
    """

    key: str
    name: str
    area: Area
    description: str
    look_around: str
    exits: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    requires: str | None = None
    locked_text: str = "The door does not budge. You need something to get in here."
    inspectables: tuple[Inspectable, ...] = ()
    items: tuple[str, ...] = ()
    boss: Boss | None = None
    on_first_enter: Callable[[Game], None] | None = None

    def find_inspectable(self, name: str) -> Inspectable | None:
        """Return the inspectable called ``name``, or None if there is none."""
        wanted = name.strip().casefold()
        for inspectable in self.inspectables:
            if inspectable.name.casefold() == wanted:
                return inspectable
        return None
