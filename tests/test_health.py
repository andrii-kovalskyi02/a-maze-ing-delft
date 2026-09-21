"""Hearts, in halves (enabler #108, E5.1).

The design document spends hearts in halves, so the one thing these tests care
about is that half a heart is *exactly* half a heart, however many times it is
taken and given back.
"""

from __future__ import annotations

import health
from health import Health


def test_a_new_player_has_three_hearts() -> None:
    """US1a: three hearts, and the drawing shows three."""
    assert Health().hearts == 3
    assert str(Health()) == "♥♥♥"


def test_half_hearts_are_exact_however_often_they_move() -> None:
    """E5.1: no floats, so no rounding can drift the player off a whole heart."""
    hearts = Health()
    for _ in range(3):
        hearts = hearts.lose(health.SIDE_QUEST)
    for _ in range(3):
        hearts = hearts.gain(health.SIDE_QUEST)
    assert hearts == Health()
    assert hearts.halves == health.MAX


def test_a_boss_costs_a_whole_heart_and_a_side_quest_half_of_one() -> None:
    """The two numbers the design document actually gives."""
    assert Health().lose(health.BOSS).hearts == 2
    assert Health().lose(health.SIDE_QUEST).hearts == 2.5


def test_healing_stops_at_three_hearts() -> None:
    """E5.1: nobody banks a fourth heart for later."""
    assert Health().gain(health.BOSS) == Health()
    assert Health(1).gain(health.BOSS * 5).halves == health.MAX


def test_hearts_never_go_below_empty() -> None:
    """There is no such thing as minus one heart."""
    assert Health(1).lose(health.BOSS).halves == 0
    assert Health(0).lose(health.BOSS).halves == 0


def test_empty_is_empty_and_nothing_else_is() -> None:
    assert Health(0).is_empty
    assert not Health(1).is_empty


def test_the_drawing_shows_the_halves() -> None:
    """The player has to be able to see half a heart, or it may as well not exist."""
    assert str(Health(5)) == "♥♥(♥)"
    assert str(Health(4)) == "♥♥·"
    assert str(Health(1)) == "(♥)··"
    assert str(Health(0)) == "···"


def test_losing_a_heart_leaves_the_old_health_alone() -> None:
    """Health is frozen: nothing can drain hearts from the far side of the engine."""
    before = Health()
    before.lose(health.BOSS)
    assert before == Health()
