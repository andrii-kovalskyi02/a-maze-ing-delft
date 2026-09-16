"""Running a boss encounter (enabler #104, first version).

This handles the two kinds of question every boss needs. A multiple-choice
question is answered with a number, like the rest of the game. An open
question is the one place in the whole game where the player types words.

Timers, per-boss quirks and the health penalties from the hearts enabler
(#108) are still to come - see issue #104.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import ui
from models import Boss, Question

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game


def run(game: Game, boss: Boss) -> bool:
    """Play out ``boss``'s challenge.

    Returns:
        True if the player answered every question correctly.
    """
    ui.say()
    ui.narrate(boss.intro)
    for number, question in enumerate(boss.questions, start=1):
        if not _ask_question(number, len(boss.questions), question):
            ui.say()
            ui.narrate(boss.lose_text)
            if boss.lose_reward is not None:
                item = game.carrying.add(boss.lose_reward)
                ui.say(f"You are now carrying the {item.name}.")
                if boss.lose_reward_text is not None:
                    ui.say()
                    ui.narrate(boss.lose_reward_text)
                    if boss.lose_reward_2 is not None:
                        second_item = game.carrying.add(boss.lose_reward_2)
                        ui.say(f"You are now carrying the {second_item.name}.")
            return False

    ui.say()
    ui.narrate(boss.win_text)
    if boss.reward is not None:
        item = game.carrying.add(boss.reward)
        ui.say(f"You are now carrying the {item.name}.")
    return True


def _ask_question(number: int, total: int, question: Question) -> bool:
    """Ask one question and return whether the player got it right."""
    header = f"Question {number} of {total}: {question.prompt}"

    if question.choices:
        chosen = ui.choose(header, question.choices)
        return question.is_correct(question.choices[chosen])

    ui.say()
    ui.say(header)
    ui.say("Answer in your own words.")
    return question.is_correct(ui.ask())
