"""The Evil Backpack, talking over the game (enabler #103).

US1c hands the player a backpack with eyes, legs and opinions. From then on it
is not just where the items live - it is the voice of the game. There is no
written list of rules in this project any more (#122 closed it): the menu says
what you can do, and anything the player needs telling *later* is told by this
character instead of by a document.

Three rules hold the whole thing together:

1. **Rooms never call it.** The engine reports what happened - an item taken,
   a door that refused you again - and the backpack answers or stays quiet.
   A room author cannot make it talk, and does not have to remember to.
2. **It does not exist before classroom 2.031.** There is no backpack in the
   player's hands until they lose to it, so :func:`remark` is silent until
   they are carrying one. Nothing before that room can lean on it.
3. **It is a character, not a hint system.** It boasts, complains about being
   carried, and is smug about its own questions. If the player genuinely
   cannot work out what to do, that is the menu's fault and belongs in an
   issue - not in a line here that quietly solves the room for them.

Everything it says is data, in :data:`REMARKS` below. Tuning its voice means
editing that dictionary and nothing else.

Silence
-------

Every remark has an ``every``: say this on every ``n``-th time it happens.
That is what keeps it from becoming wallpaper - a backpack that comments on
all forty items you pick up is one the player stops reading by the third room.

The tests silence it completely (see ``conftest.py``), so no other test
depends on a line somebody may want to rewrite tomorrow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import ui

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game

#: The item whose presence means there is anybody there to talk (US1c).
BACKPACK = "backpack"

#: False while the tests are running, so nothing depends on what it says.
_enabled = True


@dataclass(frozen=True, slots=True)
class Remark:
    """What the backpack has to say about one kind of event.

    Args:
        lines: The things it might say, used in turn so the player does not
            hear the same line twice in a row. ``{what}`` and ``{who}`` are
            filled in from whatever the engine reports.
        every: Say something on every n-th time this happens. 1 is every
            time; 3 means it keeps quiet twice and speaks on the third.
        mood: The face it makes while saying it: "speaking", "smiling" or "upset".
    """

    lines: tuple[str, ...]
    every: int = 1
    mood: str = "speaking"


#: Everything the backpack says, and how often it says it.
REMARKS: dict[str, Remark] = {
    "took": Remark(
        every=3,
        mood="upset",
        lines=(
            '"Oh, wonderful. The {what}. I\'ll carry that, shall I. As usual."',
            '"Another thing for me to hold. You know I have a bad back?"',
            '"The {what}. Riveting. Truly, you\'re a born adventurer."',
        ),
    ),
    "left_behind": Remark(
        every=2,
        mood="upset",
        lines=(
            '"You\'re just going to leave that lying there? Fine. Not my building."',
            '"Something back there is still on the floor. I\'m not going back for it."',
        ),
    ),
    "locked_again": Remark(
        mood="smiling",
        lines=(
            '"Still locked. Shocking. Try it a third time, that usually works."',
            '"That door and I have something in common: neither of us is impressed."',
            "\"It's locked. It was locked a minute ago. I'll let you know if that changes.\"",
        ),
    ),
    "backtrack": Remark(
        every=3,
        lines=(
            '"We have been here. I remember, because I was carried here."',
            '"Round and round. You do know we are going in circles?"',
        ),
    ),
    "hurt": Remark(
        mood="smiling",
        lines=(
            '"Ooh. That looked like it hurt. My questions were harder, you know."',
            '"{who} got you. To be fair, I\'d have got you faster."',
        ),
    ),
    "boss_won": Remark(
        mood="upset",
        lines=(
            '"Fine. You beat {who}. {who} was not me, though. Remember that."',
            '"Lucky. My questions would have finished you, and don\'t you forget it."',
        ),
    ),
    "boss_lost": Remark(
        mood="smiling",
        lines=(
            '"Beaten by {who}. And you thought MY questions were hard."',
            '"I would say better luck next time, but I\'ve met you."',
        ),
    ),
}


def silence() -> None:
    """Stop the backpack talking. Used by the tests only."""
    global _enabled
    _enabled = False


def speak_up() -> None:
    """Let the backpack talk again. Used by the tests only."""
    global _enabled
    _enabled = True


def remark(game: Game, event: str, **about: str) -> None:
    """Let the backpack say something about ``event``, if it feels like it.

    Called by the engine when something happens to the player. Does nothing
    at all when the player has no backpack yet, when this event has no lines,
    or when this is not the turn the backpack chooses to speak up on - which
    is most of them, on purpose.

    Args:
        game: The play-through, for the backpack and for what has been heard.
        event: Which key of :data:`REMARKS` this is, e.g. ``"took"``.
        about: Anything the lines can fill in, e.g. ``what="brass key"``.
    """
    if not _enabled or BACKPACK not in game.carrying:
        return
    remark_for_event = REMARKS.get(event)
    if remark_for_event is None:
        return

    times = game.heard.get(event, 0) + 1
    game.heard[event] = times
    if times % remark_for_event.every:
        return

    # Each time it does speak, it moves on to its next line, so the player
    # never hears the same complaint twice running.
    spoken = times // remark_for_event.every - 1
    line = remark_for_event.lines[spoken % len(remark_for_event.lines)]
    ui.say()
    with ui.speaking(BACKPACK, remark_for_event.mood):
        ui.narrate(line.format(**about))
