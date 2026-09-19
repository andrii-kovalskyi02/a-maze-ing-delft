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
    from game import Game


#: Story text: one string, or a tuple of parts typed out one after another.
#: A number in the tuple is a pause, in seconds - see ``ui.narrate``.
type Text = str | tuple[str | float, ...]


def plain(text: Text | None) -> str:
    """Return ``text`` as one plain string, pauses dropped. Handy in tests."""
    if text is None:
        return ""
    if isinstance(text, str):
        return text
    return " ".join(part for part in text if isinstance(part, str))


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
    """Something the player can carry.

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
    text: Text


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
        lose_reward: The key of the item handed over on a loss, if any. Use
            this for a boss that cannot actually be beaten - the "reward" is
            part of losing, e.g. being stuck carrying the thing you fought.
        lose_reward_text: Printed right after the player receives
            ``lose_reward`` (so after the "You are now carrying..." line).
            Use it for whatever the item says or does now that it is
            attached to the player. Ignored if ``lose_reward`` is None.
        lose_reward_2: The key of a second item handed over after
            ``lose_reward_text`` has been printed, if any. Use this when the
            first item's dialogue leads straight into handing over something
            else, e.g. the backpack talks, then immediately produces an item
            of its own. Ignored if ``lose_reward_text`` is None.
        single_attempt: If True, this encounter only ever happens once - the
            room counts as resolved after either a win OR a loss, so the
            "Get closer to X" choice disappears either way. Use this for a
            boss that cannot actually be won, where losing IS the story's
            resolution. Defaults to False, which keeps the normal behaviour:
            only a win resolves the room, so the player can keep retrying
            after a loss.
    """

    name: str
    intro: Text
    questions: tuple[Question, ...]
    win_text: Text
    lose_text: Text
    reward: str | None = None
    lose_reward: str | None = None
    lose_reward_text: Text | None = None
    lose_reward_2: str | None = None
    single_attempt: bool = False


@dataclass(frozen=True, slots=True)
class Room:
    """One room of the building.  This is the building block you fill in.

    Args:
        key: The unique id of the room, e.g. ``"classroom_2035"``.  Other rooms
            list this in their ``exits``.
        name: How the room is shown on screen, e.g. ``"Classroom 2.035"``.
        area: Which colour-coded part of the floor the room is in.
        description: The short line printed when the player walks in.
        look_around: The longer text printed for ``look around``, or None for a
            place with nothing to describe, like a staircase you only pass
            through. The "Look around" choice is then only offered if there
            is still something here to interact with.
        exits: The keys of the rooms reachable from here.
        requires: The key of an item needed to enter.  The engine checks the
            backpack automatically; the player never types "use key".
        locked_text: What the player reads when they lack that item.
        inspectables: Details the player can ``inspect`` here.
        items: The keys of items lying in this room, ready to be picked up.
        boss: The challenge guarding this room, if any.
        on_first_enter: An optional function run once, the first time the
            player enters.  Use it only when plain data is not enough.
        approach_reward: The key of an item handed over the first time the
            player walks up to this room's door, whether or not it opens.
        approach_reward_text: Printed after ``approach_reward`` is handed over.
        is_hallway: If True, this room is a corridor/lobby the player is
            expected to pass through repeatedly, so its door label never
            grows the "(you have been there)" tag - that tag is only useful
            for rooms with a story to remember, not a hallway you walk
            through every trip. Defaults to False, which keeps the normal
            behaviour of tagging any previously visited room.
    """

    key: str
    name: str
    area: Area
    description: Text
    look_around: Text | None = None
    exits: tuple[str, ...] = ()
    requires: str | None = None
    locked_text: str = "The door does not budge. You need something to get in here."
    inspectables: tuple[Inspectable, ...] = ()
    items: tuple[str, ...] = ()
    boss: Boss | None = None
    on_first_enter: Callable[[Game], None] | None = None
    approach_reward: str | None = None
    approach_reward_text: Text | None = None
    is_hallway: bool = False
