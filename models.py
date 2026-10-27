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


@dataclass(frozen=True, slots=True)
class Unless:
    """A part of a text that is only told while an item has not been picked up.

    Use it for a line like "A key card hangs on a hook by the window": once the
    player has taken it, the line is left out instead of describing what is gone.

    Args:
        item: The key of the item the line is about.
        parts: What is told while the player has not got the item: strings, and
            numbers for pauses, like any other text.
        after: What is told instead once they have it, if anything.
    """

    item: str
    parts: tuple[str | float, ...]
    after: tuple[str | float, ...] = ()


@dataclass(frozen=True, slots=True)
class Says:
    """Part of a boss's text that the boss itself speaks, as opposed to what is narrated.

    Everything in a text that is not wrapped in this is narration: it is typed with the soft
    narrator sound, and the speaker's face is not shown. What is wrapped, the boss's own words,
    gets the boss's voice. Make one with :func:`says`.

    Args:
        parts: What is spoken: strings, and numbers for pauses, like any other text.
    """

    parts: tuple[str | float, ...]


def says(*parts: str | float) -> Says:
    """Mark ``parts`` as spoken by the boss: ``says("PENALTY.", 0.3, "SHOOTOUT.")``."""
    return Says(parts)


#: Story text: one string, or a tuple of parts typed out one after another.
#: A number in the tuple is a pause, in seconds - see ``ui.narrate``. A part can also
#: be an :class:`Unless`, told only while an item is still lying there, or a :class:`Says`,
#: the words a boss speaks.
type Text = str | tuple[str | float | Unless | Says, ...]


def plain(text: Text | None) -> str:
    """Return ``text`` as one plain string, pauses dropped. Handy in tests."""
    if text is None:
        return ""
    if isinstance(text, str):
        return text
    words: list[str] = []
    for part in text:
        if isinstance(part, Unless):
            words += [piece for piece in part.parts + part.after if isinstance(piece, str)]
        elif isinstance(part, Says):
            words += [piece for piece in part.parts if isinstance(piece, str)]
        elif isinstance(part, str):
            words.append(part)
    return " ".join(words)


def resolve(text: Text, has_taken: Callable[[str], bool]) -> tuple[str | float, ...]:
    """Return ``text`` as it should be told now, given which items the player has taken.

    Args:
        text: The story text, which may hold :class:`Unless` parts.
        has_taken: Says whether the player has picked up an item, by key.

    Returns:
        Only strings and pauses, ready for ``ui.narrate``.
    """
    if isinstance(text, str):
        return (text,)
    told: list[str | float] = []
    for part in text:
        if isinstance(part, Unless):
            told += part.after if has_taken(part.item) else part.parts
        else:
            told.append(part)
    return tuple(told)


class Area(StrEnum):
    """The three colour-coded parts of the 2nd floor.

    Areas exist so the key-card gating enabler (issue #112) can block a whole wing
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
        colour: For a digit of the exit code, which passage it belongs to -
            one of ``digits.ORDER``. Leave it out for anything else.
        value: For a digit of the exit code, the character it shows. The door's
            code is assembled from these, so changing a digit here changes the
            code and nothing else - see ``digits.py``.
        use_text: What is told when the item opens a locked door. ``{item}`` and
            ``{door}`` are filled in. Leave it out for a plain "You use the ...".
    """

    key: str
    name: str
    description: str
    single_use: bool = False
    colour: str | None = None
    value: str | None = None
    use_text: str = "You use the {item}, and the door to {door} opens."


@dataclass(frozen=True, slots=True)
class Inspectable:
    """A detail in a room the player can look at but cannot pick up.

    Args:
        name: What the player types after ``inspect``, e.g. ``"clock"``.
        text: What they read.
        gone_once_taken: The key of an item that, once the player has it, takes this
            detail away - the floor plan is not on the wall any more.
        shows_map: True if looking at it also shows the drawn floor map, where the
            window can draw one (the floor plan on the wall).
    """

    name: str
    text: Text
    gone_once_taken: str | None = None
    shows_map: bool = False


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
        seconds: How long the player has to answer, or None for a question
            with no clock on it.  The Evil Backpack's questions are untimed on
            purpose (US1c); the forest boss's typing attack is not (US1p).

    A question with **no** accepted answers is allowed, and means exactly what
    it looks like: there is no right answer and the player cannot win it.  The
    Evil Backpack's last question is one (US1c).

    A **typing attack** - "type this word before the timer runs out" - is just
    an open question with a clock on it; :func:`typing_attack` builds one.
    """

    prompt: str
    answers: tuple[str, ...]
    choices: tuple[str, ...] = ()
    seconds: float | None = None

    def is_correct(self, given: str) -> bool:
        """Return True if ``given`` matches one of the accepted answers."""
        return given.strip().casefold() in {a.strip().casefold() for a in self.answers}


def typing_attack(word: str, seconds: float) -> Question:
    """Return a question that asks the player to type ``word`` in time (US1p).

    Args:
        word: What the player has to type back.
        seconds: How long they get.
    """
    return Question(
        prompt=f'Type "{word}" before the timer runs out.',
        answers=(word,),
        seconds=seconds,
    )


@dataclass(frozen=True, slots=True)
class Boss:
    """The challenge guarding a room.

    Args:
        name: Who the player faces, e.g. ``"the Evil Backpack"``.
        intro: What is printed when the encounter starts.
        questions: The questions asked, in order.
        win_text: What is printed when the player answers everything correctly.
        lose_text: What is printed when the player loses the fight. A wrong answer alone
            does not lose it: it costs a heart and the same question is asked again. The
            fight is lost when the last heart goes (then the player goes back to their
            last save), or at once in a ``single_attempt`` fight.
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
        side_quest: If True this is a side quest rather than a boss, so it
            costs and heals half a heart instead of a whole one - see
            ``health.py`` (#108).
        single_attempt: If True, this encounter only ever happens once - the
            room counts as resolved after either a win OR a loss, so the
            "Get closer to X" choice disappears either way. Use this for a
            boss that cannot actually be won, where losing IS the story's
            resolution. Defaults to False, which keeps the normal behaviour:
            only a win resolves the room, so the player can keep retrying
            after a loss. A scripted loss like this costs no hearts: losing
            is the story, not a mistake the player made.
    """

    name: str
    intro: Text
    questions: tuple[Question, ...]
    win_text: Text
    lose_text: Text
    reward: str | None = None
    side_quest: bool = False
    lose_reward: str | None = None
    lose_reward_text: Text | None = None
    lose_reward_2: str | None = None
    single_attempt: bool = False
    speaker: str | None = None


@dataclass(frozen=True, slots=True)
class Room:
    """One room of the building.  This is the building block you fill in.

    Args:
        key: The unique id of the room, e.g. ``"classroom_2035"``.  Other rooms
            list this in their ``exits``.
        name: How the room is shown on screen, e.g. ``"Classroom 2.035"``.
        area: Which colour-coded part of the floor the room is in.
        description: The short line printed when the player walks in.
        return_description: What is printed instead on every later visit. None tells
            nothing again: the player has read ``description`` already.
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
        approach_reward_text: Printed when ``approach_reward`` is handed over,
            just before the "You are now carrying..." line.
        is_exit: If True, this is the way out of the building. The engine
            asks for the four-digit code here instead of an item, and walking
            through ends the game - see ``digits.py`` (enabler #116).
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
    return_description: Text | None = None
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
    is_exit: bool = False
    is_hallway: bool = False
