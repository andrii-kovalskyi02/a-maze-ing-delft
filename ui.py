"""All screen output and keyboard input goes through here.

Keeping ``print`` and ``input`` in one small module means the tests can play
the game without a human at the keyboard.  Never call ``print`` or ``input``
directly from a room.
"""

from __future__ import annotations

import textwrap
from collections.abc import Callable, Sequence

#: Room descriptions are wrapped to this width so they stay readable, and so
#: nobody has to hand-wrap the text they write.
WIDTH = 80

#: Swapped out by the tests. Do not call these two directly; use say/ask.
_write: Callable[[str], None] = print
_read: Callable[[str], str] = input


def say(text: str = "") -> None:
    """Show ``text`` to the player, wrapped to :data:`WIDTH` columns.

    Write your room text as one long string; the wrapping happens here.
    Blank lines and leading indentation are preserved.
    """
    for line in text.split("\n"):
        if not line.strip():
            _write("")
            continue
        _write(textwrap.fill(line, width=WIDTH, subsequent_indent=" " * _indent_of(line)))


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


def use_io(write: Callable[[str], None], read: Callable[[str], str]) -> None:
    """Replace the input and output functions. Used by the tests only."""
    global _write, _read
    _write, _read = write, read
