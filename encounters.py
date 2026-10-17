"""Running a boss encounter (enabler #104).

Six rooms, six bosses, six different behaviours - and one engine, because the
alternative is six copies of this file with small differences nobody can keep
straight by week 5. Everything that makes a boss *itself* is declared in the
room, as data on :class:`~models.Boss`, and this file is the only place that
knows how a fight is actually run:

=========================== ============================================
What the design doc asks for How it is declared
=========================== ============================================
multiple choice, 3 or 4      ``Question(choices=(...))``
open answer                  ``Question(answers=(...))`` and no choices
no right answer at all       ``Question(answers=())`` - US1c, question 5
a time limit                 ``Question(seconds=...)``
no time limit                leave ``seconds`` out - US1c
a typing attack              ``models.typing_attack(word, seconds)`` - US1p
a fight you cannot win       ``Boss(single_attempt=True)`` - US1c
a side quest, not a boss     ``Boss(side_quest=True)``
=========================== ============================================

Adding a boss therefore needs no change in here at all. If you find yourself
wanting one, say so in the issue first - it almost always means a new field
belongs on ``Boss``, where every other room can use it too.

Hearts (#108) are spent here, because this is where the player can get
something wrong: a wrong answer or a missed timer costs a whole heart against
a boss and half a one on a side quest, and beating it gives the same back. A
scripted loss - the Evil Backpack, who cannot be beaten - costs nothing, since
losing to him is the story doing what it meant to do.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import health
import narrator
import ui
from models import Boss, Question

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game

#: What the player reads when the clock beats them.
TOO_SLOW = "Too slow."


def run(game: Game, boss: Boss) -> bool:
    """Play out ``boss``'s challenge.

    Returns:
        True if the player answered every question correctly.
    """
    ui.say()
    ui.narrate(boss.intro)
    ui.say()
    ui.say(f"Hearts: {game.hearts}")

    for number, question in enumerate(boss.questions, start=1):
        if _ask_question(number, len(boss.questions), question):
            continue
        _hurt(game, boss)
        ui.say()
        ui.narrate(boss.lose_text)
        _hand_over_the_losing_items(game, boss)
        return False

    _heal(game, boss)
    ui.say()
    ui.narrate(boss.win_text)
    if boss.reward is not None:
        item = game.carrying.add(boss.reward)
        ui.new_page()  # picking something up is a moment of its own
        ui.narrate(f"You are now carrying the {item.name}.")
        ui.new_page()
    narrator.remark(game, "boss_won", who=boss.name)
    return True


def _ask_question(number: int, total: int, question: Question) -> bool:
    """Ask one question and return whether the player got it right in time."""
    header = f"Question {number} of {total}: {question.prompt}"
    seconds = question.seconds
    if seconds is not None:
        header += f"  ({seconds:g} seconds)"

    started = ui.now()
    try:
        if question.choices:
            chosen = ui.choose(header, question.choices, timeout=seconds)
            given = question.choices[chosen]
        else:
            ui.say()
            ui.say(header)
            ui.say("Answer in your own words.")
            given = ui.ask(timeout=seconds)
    except ui.TimedOut:
        # The clock ran out while the player was still thinking or typing.
        ui.say()
        ui.say(TOO_SLOW)
        return False

    if _ran_out_of_time(seconds, ui.now() - started):
        ui.say()
        ui.say(TOO_SLOW)
        return False
    return question.is_correct(given)


def _ran_out_of_time(seconds: float | None, taken: float) -> bool:
    """Return True if the player took longer than ``seconds``.

    In a real terminal :func:`ui.ask` already stops the player when the time
    is up. Everywhere else - tests, piped input, a terminal whose keyboard
    cannot be watched - the answer is simply waited for, and this check on the
    clock afterwards is what makes a slow answer count as wrong.
    """
    return seconds is not None and taken > seconds


def _hurt(game: Game, boss: Boss) -> None:
    """Take a heart off the player for getting it wrong, if this fight costs any."""
    if boss.single_attempt:
        # A fight the story means the player to lose. Losing it is not a
        # mistake, so it does not cost a heart - see US1c.
        return
    game.hearts = game.hearts.lose(_stake(boss))
    ui.say()
    ui.say(f"Hearts: {game.hearts}")
    narrator.remark(game, "hurt", who=boss.name)


def _heal(game: Game, boss: Boss) -> None:
    """Give the player back what beating this was worth, up to three hearts."""
    before = game.hearts
    game.hearts = game.hearts.gain(_stake(boss))
    if game.hearts != before:
        ui.say()
        ui.say(f"Hearts: {game.hearts}")


def _stake(boss: Boss) -> int:
    """Return what this encounter costs when lost, and gives back when won."""
    return health.SIDE_QUEST if boss.side_quest else health.BOSS


def _hand_over_the_losing_items(game: Game, boss: Boss) -> None:
    """Give the player whatever losing to this boss saddles them with (US1c)."""
    if boss.lose_reward is None:
        narrator.remark(game, "boss_lost", who=boss.name)
        return

    item = game.carrying.add(boss.lose_reward)
    ui.new_page()  # picking something up is a moment of its own
    ui.narrate(f"You are now carrying the {item.name}.")
    ui.new_page()
    if boss.lose_reward_text is not None:
        ui.say()
        ui.narrate(boss.lose_reward_text)
        if boss.lose_reward_2 is not None:
            second_item = game.carrying.add(boss.lose_reward_2)
            ui.new_page()
            ui.narrate(f"You are now carrying the {second_item.name}.")
            ui.new_page()
    if not _handed_over_the_backpack(boss):
        narrator.remark(game, "boss_lost", who=boss.name)


def _handed_over_the_backpack(boss: Boss) -> bool:
    """Return True if this is the fight the player loses the backpack to (US1c).

    The backpack has nothing to say about that one: it has only just arrived,
    and "beaten by the backpack" from the backpack reads like a bad echo.
    """
    return narrator.BACKPACK in {boss.lose_reward, boss.lose_reward_2}
