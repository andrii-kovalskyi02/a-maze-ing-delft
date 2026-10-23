"""The player's hearts (enabler #108).

The design document gives the player three hearts and then spends them in
halves: a side quest you run out of time on costs half a heart, a boss costs a
whole one. So hearts are counted here in **halves, as whole numbers** - three
hearts is ``6``, not ``3.0``. Nothing in this file is ever a float, which is
the point: half a heart plus half a heart is exactly one heart, every time, and
no rounding can ever leave the player on 2.9999 hearts.

What costs and what heals is written down once, in the constants below, so the
numbers can be balanced by editing this file and nothing else::

    hearts = Health()            # three hearts
    hearts = hearts.lose(BOSS)   # got a boss question wrong
    hearts = hearts.gain(BOSS)   # beat a boss: a full heart back

:class:`Health` is frozen, like everything else in ``models.py``: losing a
heart gives you a new Health rather than changing the old one, so nothing can
quietly drain the player's hearts from the other side of the engine.
"""

from __future__ import annotations

from dataclasses import dataclass

#: How many halves make one heart. Here so no other file writes a bare 2.
PER_HEART = 2

#: US1a: the player starts on three hearts, and can never hold more.
MAX = 3 * PER_HEART

#: What a boss costs: a whole heart, for a wrong answer or for running out of
#: time. Beating one gives the same back.
BOSS = 2

#: What a side quest costs, and gives back: half a heart.
SIDE_QUEST = 1

#: A full heart, an empty one, and the half in between, as the player sees them.
FULL = "♥"
HALF = "♥"
EMPTY = "·"


class OutOfHearts(Exception):
    """The player has just lost their last heart (#217).

    Raised where the heart is lost, so nothing else happens in between: not
    the rest of the fight, not another "What do you do?". The main loop in
    ``game.py`` catches it and ends the run.
    """


@dataclass(frozen=True, slots=True)
class Health:
    """How many hearts the player has left, counted in halves.

    Args:
        halves: The number of half-hearts left. Defaults to a full three
            hearts, which is where every play-through starts.
    """

    halves: int = MAX

    @property
    def hearts(self) -> float:
        """How many hearts that is, for anything that wants the number."""
        return self.halves / PER_HEART

    @property
    def is_empty(self) -> bool:
        """Return True if the player has run out of hearts."""
        return self.halves <= 0

    def lose(self, halves: int) -> Health:
        """Return the health left after losing ``halves`` half-hearts.

        Never goes below empty - there is no such thing as minus one heart.
        """
        return Health(max(0, self.halves - halves))

    def gain(self, halves: int) -> Health:
        """Return the health after healing ``halves``, capped at :data:`MAX`.

        A player on full hearts who beats a boss is simply still on full
        hearts; healing is never banked for later.
        """
        return Health(min(MAX, self.halves + halves))

    def __str__(self) -> str:
        """Draw the hearts: ``♥♥♥`` full, ``♥♥·`` for two, ``♥♥(♥)`` for two and a half.

        A half heart is drawn as the heart in brackets, ``(♥)``, because half
        a heart glyph does not exist in a font we can count on across three
        operating systems - and a bracket reads as "not quite" to anybody.
        """
        full, half = divmod(max(0, self.halves), PER_HEART)
        drawn = FULL * full + (f"({HALF})" if half else "")
        return drawn + EMPTY * (MAX // PER_HEART - full - half)
