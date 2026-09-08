"""Turning what the player typed into something the engine can act on (#92).

Players are allowed to be sloppy: capitals, extra spaces and a few natural
phrasings all work.  Everything that makes that true lives here, so no room
ever has to think about it.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The commands the engine understands. Longest first so that "look around"
#: is recognised before the shorter verbs are tried.
VERBS: tuple[str, ...] = (
    "look around",
    "backpack",
    "options",
    "inspect",
    "answer",
    "help",
    "quit",
    "take",
    "map",
    "go",
)

#: Whole inputs that mean exactly the same as another command.
PHRASE_ALIASES: dict[str, str] = {
    "?": "help",
    "h": "help",
    "l": "look around",
    "look": "look around",
    "inventory": "backpack",
    "items": "backpack",
    "bag": "backpack",
    "exit": "quit",
}

#: Openings that mean the same as a shorter verb, e.g. "look at clock".
PREFIX_ALIASES: dict[str, str] = {
    "look at ": "inspect ",
    "examine ": "inspect ",
    "pick up ": "take ",
    "go to ": "go ",
    "walk to ": "go ",
    "move to ": "go ",
}


@dataclass(frozen=True, slots=True)
class Command:
    """A recognised command.

    Args:
        verb: One of :data:`VERBS`.
        argument: Everything the player typed after the verb, possibly empty.
    """

    verb: str
    argument: str


def parse(raw: str) -> Command | None:
    """Turn a raw line of input into a :class:`Command`.

    Returns:
        The command, or None if nothing recognisable was typed.  An
        unrecognised command is never an error: the caller prints a hint.
    """
    text = " ".join(raw.strip().casefold().split())
    if not text:
        return None

    text = PHRASE_ALIASES.get(text, text)
    for opening, replacement in PREFIX_ALIASES.items():
        if text.startswith(opening):
            text = replacement + text[len(opening) :]
            break

    for verb in VERBS:
        if text == verb:
            return Command(verb, "")
        if text.startswith(f"{verb} "):
            return Command(verb, text[len(verb) + 1 :].strip())
    return None
