"""All screen output and keyboard input goes through here.

Keeping ``print`` and ``input`` in one small module means the tests can play
the game without a human at the keyboard.  Never call ``print`` or ``input``
directly from a room.
"""

from __future__ import annotations

import sys
import textwrap
import time
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from models import Text

#: Room descriptions are wrapped to this width so they stay readable, and so
#: nobody has to hand-wrap the text they write.
WIDTH = 80

#: How long :func:`narrate` waits after each character, in seconds. This is
#: what makes the text look like it is being typed rather than dumped.
CHAR_DELAY = 0.02

#: How long :func:`narrate` waits between two parts of a text, in seconds, when
#: the room does not ask for a pause of its own.
PART_DELAY = 0.5

#: Swapped out by the tests. Do not call these directly; use say/narrate/ask.
_write: Callable[[str], None] = print
_read: Callable[[str], str] = input
_sleep: Callable[[float], None] = time.sleep


def say(text: str = "") -> None:
    """Show ``text`` to the player, wrapped to :data:`WIDTH` columns.

    Write your room text as one long string; the wrapping happens here.
    Blank lines and leading indentation are preserved.
    """
    for line in _wrap(text):
        _write(line)


def narrate(text: Text) -> None:
    """Type ``text`` out to the player a character at a time.

    Use this for the story - room descriptions, and what a boss says - so it
    reads like somebody talking instead of a wall of text. Menus stay instant
    with :func:`say`.

    ``text`` is either one string, or a tuple of parts. Between two strings
    the game pauses for :data:`PART_DELAY`; put a number in the tuple to pause
    for that many seconds instead::

        ("The ghost looks up at you.", 1.5, "'Let's begin.'")
    """
    parts = (text,) if isinstance(text, str) else text
    previous_was_text = False
    for part in parts:
        if isinstance(part, int | float):
            _sleep(part)
            previous_was_text = False
            continue
        if previous_was_text:
            _sleep(PART_DELAY)
        for line in _wrap(part):
            _type_line(line)
        previous_was_text = True


def _wrap(text: str) -> list[str]:
    """Split ``text`` into lines wrapped to :data:`WIDTH`, keeping blank lines."""
    return [
        textwrap.fill(line, width=WIDTH, subsequent_indent=" " * _indent_of(line))
        if line.strip()
        else ""
        for line in text.split("\n")
    ]


def _type_line(line: str) -> None:
    """Write one line, a character at a time when a real terminal is watching."""
    if _write is not print or not sys.stdout.isatty():
        # The tests, or output piped into a file: nobody is there to watch.
        _write(line)
        return
    for character in line:
        sys.stdout.write(character)
        sys.stdout.flush()
        _sleep(CHAR_DELAY)
    sys.stdout.write("\n")


def _indent_of(line: str) -> int:
    """Return how far ``line`` is indented, so wrapped lines line up under it."""
    return len(line) - len(line.lstrip())


def ask(prompt: str = "> ") -> str:
    """Ask the player for a line of input and return it stripped."""
    return _read(prompt).strip()


def choose(prompt: str, options: Sequence[str], back: str | None = None) -> int | None:
    """Show a numbered list and let the player pick one.

    The player never types a word: they type the number next to what they
    want. Anything else is answered with a nudge and the list is shown again,
    so it is impossible to get stuck.

    Args:
        prompt: The question above the list, e.g. "What do you do?".
        options: What the player can choose, in the order shown.
        back: The label for a "0" option that returns without choosing, or
            None for a list that must be answered.

    Returns:
        The index of the chosen option, or None if the player chose ``back``.
    """
    while True:
        say()
        say(prompt)
        for number, option in enumerate(options, start=1):
            say(f"  {number}) {option}")
        if back is not None:
            say(f"  0) {back}")

        typed = ask()
        if back is not None and typed == "0":
            return None
        if typed.isdigit() and 1 <= int(typed) <= len(options):
            return int(typed) - 1
        say("Type the number of the thing you want.")


def use_io(
    write: Callable[[str], None],
    read: Callable[[str], str],
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Replace the input, output and waiting functions. Used by the tests only."""
    global _write, _read, _sleep
    _write, _read, _sleep = write, read, sleep
