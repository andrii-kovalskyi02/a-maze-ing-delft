"""Running a boss encounter (enabler #104).

Everything that makes a boss different is declared in its room, as data on
:class:`~models.Boss`; this file is the only place that knows how a fight is run:

=========================== ============================================
Behaviour                    How it is declared
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

Hearts (#108) are spent here: a wrong answer or a missed timer costs a whole heart against a
boss and half a one on a side quest, and winning gives the same back. A scripted loss (the Evil
Backpack, who cannot be beaten) costs nothing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import health
import narrator
import ui
from models import Boss, Question, Says, Text

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game

#: What the player reads when the clock beats them.
TOO_SLOW = "Too slow."

#: What the player reads after a wrong answer that has cost them a heart: the same question again.
TRY_AGAIN = "Not quite. Try that one again."


async def run(game: Game, boss: Boss, from_question: int | None = None) -> bool:
    """Play out ``boss``'s challenge.

    A wrong answer does not end the fight: it costs a heart and the same question is asked
    again, until the player gets it right or runs out of hearts.

    While a question is being asked, ``game.in_question`` says which one, so a save made
    right then (pause, the pause menu) comes back to it. ``from_question`` is that number,
    for a game resumed in the middle of a fight: the intro has been heard already, so it
    goes straight back to that question.

    Returns:
        True if the player answered every question correctly. False only for a fight the
        story means them to lose (``single_attempt``).

    Raises:
        health.OutOfHearts: If the last heart goes on a wrong answer.
    """
    ui.cue("boss_music_on")  # the boss music starts as you get closer
    try:
        return await _play(game, boss, from_question)
    finally:
        game.in_question = None  # however it ended, no question is being asked any more
        ui.cue("boss_music_off")  # and stops when the encounter is over, however it ended


async def _play(game: Game, boss: Boss, from_question: int | None) -> bool:
    """The encounter itself, from the boss's intro to its win or lose text."""
    await ui.say()
    if from_question is None:
        await _tell(boss, boss.intro, "speaking")
    else:
        await ui.narrate(f"You are back in front of {boss.name}, right where you left off.")
    ui.cue("combat")  # the questions are about to begin
    await ui.say()
    await ui.say(f"Hearts: {game.hearts}")

    for number, question in enumerate(boss.questions):
        if from_question is not None and number < from_question:
            continue  # answered before the game was saved
        game.in_question = number
        # A wrong answer costs a heart and the same question comes back, until it is answered
        # right or the last heart goes (health.OutOfHearts ends the fight there and then).
        while not await _ask_question(number + 1, len(boss.questions), question):
            if boss.single_attempt:
                # the story's own loss (US1c): there is no second go at this one
                await ui.say()
                await _tell(boss, boss.lose_text, "smiling")
                await _hand_over_the_losing_items(game, boss)
                return False
            await _hurt(game, boss)
            await ui.say()
            await ui.say(TRY_AGAIN)

    await _heal(game, boss)
    ui.cue("victory")  # every question answered: a happy little jingle
    await ui.say()
    await _tell(boss, boss.win_text, "upset")
    if boss.reward is not None:
        item = game.carrying.add(boss.reward)
        await ui.new_page()  # picking something up is a moment of its own
        await ui.narrate(f"You are now carrying the {item.name}.")
        await ui.new_page()
    await narrator.remark(game, "boss_won", who=boss.name)
    return True


async def _tell(boss: Boss, text: Text, mood: str) -> None:
    """Tell a boss's text: its own words in its voice (with its face), the rest as narration.

    Only the parts marked with ``says(...)`` are the boss speaking. Everything else is typed
    with the narrator's soft sound, so "The table shudders to life" is not said in the
    machine's voice. A pause number stays with the part before it.
    """
    runs: list[tuple[bool, list[str | float]]] = []
    for part in (text,) if isinstance(text, str) else text:
        if isinstance(part, Says):
            runs.append((True, list(part.parts)))
        elif isinstance(part, str):
            if runs and not runs[-1][0]:
                runs[-1][1].append(part)
            else:
                runs.append((False, [part]))
        elif runs:  # a pause belongs to the part before it
            runs[-1][1].append(part)
    for spoken, parts in runs:
        if spoken and boss.speaker is not None:
            with ui.speaking(boss.speaker, _mood(boss, mood)):
                await ui.narrate(tuple(parts))
        else:
            await ui.narrate(tuple(parts))


def _mood(boss: Boss, mood: str) -> str:
    """The mood a boss speaks in. Only the backpack has a face to show it, so only it changes."""
    return mood if boss.speaker == narrator.BACKPACK else "speaking"


async def _ask_question(number: int, total: int, question: Question) -> bool:
    """Ask one question and return whether the player got it right in time."""
    header = f"Question {number} of {total}: {question.prompt}"
    seconds = question.seconds
    if seconds is not None:
        header += f"  ({seconds:g} seconds)"

    started = ui.now()
    try:
        if question.choices:
            chosen = await ui.choose(header, question.choices, timeout=seconds)
            given = question.choices[chosen]
        else:
            await ui.say()
            await ui.say(header)
            await ui.say("Answer in your own words.")
            given = await ui.ask(timeout=seconds)
    except ui.TimedOut:
        # The clock ran out while the player was still thinking or typing.
        await ui.say()
        await ui.say(TOO_SLOW)
        return False

    if _ran_out_of_time(seconds, ui.now() - started):
        await ui.say()
        await ui.say(TOO_SLOW)
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


async def _hurt(game: Game, boss: Boss) -> None:
    """Take a heart off the player for getting it wrong, if this fight costs any."""
    if boss.single_attempt:
        # A fight the story means the player to lose. Losing it is not a
        # mistake, so it does not cost a heart - see US1c.
        return
    game.hearts = game.hearts.lose(_stake(boss))
    await ui.say()
    await ui.say(f"Hearts: {game.hearts}")
    if game.hearts.is_empty:
        # The battle is lost: the boss has its say, then the run goes back to the last save -
        # see health.OutOfHearts (#217).
        await ui.say()
        await _tell(boss, boss.lose_text, "smiling")
        raise health.OutOfHearts
    await narrator.remark(game, "hurt", who=boss.name)


async def _heal(game: Game, boss: Boss) -> None:
    """Give the player back what beating this was worth, up to three hearts."""
    before = game.hearts
    game.hearts = game.hearts.gain(_stake(boss))
    if game.hearts != before:
        await ui.say()
        await ui.say(f"Hearts: {game.hearts}")


def _stake(boss: Boss) -> int:
    """Return what this encounter costs when lost, and gives back when won."""
    return health.SIDE_QUEST if boss.side_quest else health.BOSS


async def _hand_over_the_losing_items(game: Game, boss: Boss) -> None:
    """Give the player whatever losing to this boss saddles them with (US1c)."""
    if boss.lose_reward is None:
        await narrator.remark(game, "boss_lost", who=boss.name)
        return

    item = game.carrying.add(boss.lose_reward)
    await ui.new_page()  # picking something up is a moment of its own
    await ui.narrate(f"You are now carrying the {item.name}.")
    await ui.new_page()
    if boss.lose_reward_text is not None:
        await ui.say()
        await _tell(boss, boss.lose_reward_text, "smiling")
        if boss.lose_reward_2 is not None:
            second_item = game.carrying.add(boss.lose_reward_2)
            await ui.new_page()
            await ui.narrate(f"You are now carrying the {second_item.name}.")
            await ui.new_page()
    if not _handed_over_the_backpack(boss):
        await narrator.remark(game, "boss_lost", who=boss.name)


def _handed_over_the_backpack(boss: Boss) -> bool:
    """Return True if this is the fight the player loses the backpack to (US1c).

    The backpack has nothing to say about that one: it has only just arrived,
    and "beaten by the backpack" from the backpack reads like a bad echo.
    """
    return narrator.BACKPACK in {boss.lose_reward, boss.lose_reward_2}
