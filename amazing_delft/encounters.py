"""Running a boss encounter (enabler #104, first version).

This handles the two question types every boss needs: multiple choice and open
answer.  Timers, per-boss quirks and the health penalties from the hearts
enabler (#108) are still to come - see issue #104.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from amazing_delft import ui
from amazing_delft.models import Boss, Question

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from amazing_delft.game import Game


def run(game: Game, boss: Boss) -> bool:
    """Play out ``boss``'s challenge.

    Returns:
        True if the player answered every question correctly.
    """
    ui.say()
    ui.say(boss.intro)
    for number, question in enumerate(boss.questions, start=1):
        if not _ask_question(number, len(boss.questions), question):
            ui.say(boss.lose_text)
            return False

    ui.say(boss.win_text)
    if boss.reward is not None:
        item = game.backpack.add(boss.reward)
        ui.say(f"You put the {item.name} in your backpack.")
    return True


def _ask_question(number: int, total: int, question: Question) -> bool:
    """Ask one question and return whether the player got it right."""
    ui.say()
    ui.say(f"Question {number} of {total}: {question.prompt}")
    for label, choice in zip("abcd", question.choices, strict=False):
        ui.say(f"  {label}) {choice}")

    given = ui.ask("answer> ")
    if question.choices:
        given = _choice_for_letter(given, question.choices)
    return question.is_correct(given)


def _choice_for_letter(given: str, choices: tuple[str, ...]) -> str:
    """Turn "b" into the text of the second choice, leaving anything else be."""
    letters = "abcd"[: len(choices)]
    stripped = given.strip().casefold()
    if len(stripped) == 1 and stripped in letters:
        return choices[letters.index(stripped)]
    return given
