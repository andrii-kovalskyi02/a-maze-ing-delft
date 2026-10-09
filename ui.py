"""All screen output and keyboard input goes through here.

Keeping ``print`` and ``input`` in one small module means the tests can play
the game without a human at the keyboard.  Never call ``print`` or ``input``
directly from a room.
"""

from __future__ import annotations

import contextlib
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

#: True once the player has said they would rather not watch the story being
#: typed. Set by the Options menu, and by pressing a key during a narration -
#: see :func:`narrate` (issue #151).
_instant = False

#: Swapped out by the tests. Do not call these directly; use say/narrate/ask.
_write: Callable[[str], None] = print
_read: Callable[[str], str] = input
_sleep: Callable[[float], None] = time.sleep

_clock: Callable[[], float] = time.monotonic

#: What to do when the player types one of the words that work at any prompt
#: (see :func:`ask`). None while no game is running - at the name prompt, say.
_pause_handler: Callable[[], None] | None = None
_quit_handler: Callable[[], bool] | None = None
_scoreboard_handler: Callable[[], None] | None = None


class PauseRequested(Exception):
    """Raised when the player asks to pause the game."""


class QuitRequested(Exception):
    """Raised when the player has typed ``quit`` and confirmed it."""


class TimedOut(Exception):
    """Raised when the player did not answer in time."""


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

    A player who has read this before can press Enter (or any key) while it is
    being typed: the rest of the text appears at once, pauses included. The
    Options menu turns the typing off for good - see :func:`set_instant`.
    """
    parts = (text,) if isinstance(text, str) else text
    skipped = False
    previous_was_text = False
    with _keys_not_echoed():
        for part in parts:
            if isinstance(part, int | float):
                if not (skipped or _instant):
                    _sleep(part)
                previous_was_text = False
                continue
            if previous_was_text and not (skipped or _instant):
                _sleep(PART_DELAY)
            for line in _wrap(part):
                if skipped or _instant:
                    _write(line)
                elif _type_line(line):
                    # The player pressed a key: they have read this before.
                    # The rest of this text lands at once, pauses and all.
                    skipped = True
            previous_was_text = True


def _wrap(text: str) -> list[str]:
    """Split ``text`` into lines wrapped to :data:`WIDTH`, keeping blank lines."""
    return [
        textwrap.fill(line, width=WIDTH, subsequent_indent=" " * _indent_of(line))
        if line.strip()
        else ""
        for line in text.split("\n")
    ]


def _type_line(line: str) -> bool:
    """Write one line, a character at a time when a real terminal is watching.

    Returns:
        True if the player pressed a key to skip the rest of the story.
    """
    if not _at_a_real_terminal():
        # The tests, or output piped into a file: nobody is there to watch.
        _write(line)
        return False
    for index, character in enumerate(line):
        if _pressed_a_key():
            sys.stdout.write(line[index:] + "\n")
            sys.stdout.flush()
            return True
        sys.stdout.write(character)
        sys.stdout.flush()
        _sleep(CHAR_DELAY)
    sys.stdout.write("\n")
    return False


def _indent_of(line: str) -> int:
    """Return how far ``line`` is indented, so wrapped lines line up under it."""
    return len(line) - len(line.lstrip())


@contextlib.contextmanager
def _keys_not_echoed():
    """Stop the terminal printing the keys the player presses, while it lasts.

    A terminal normally echoes what you type, and it does it the moment you
    press the key - not when the program gets round to reading it. So a player
    pressing Enter to skip the typing would see their own newline land in the
    middle of a word, splitting it in half.

    Turning the echo off for as long as the story is being typed is the fix.
    The same switch also turns off line-buffering, which is what lets *any*
    key skip the text rather than only Enter.

    Does nothing at all unless a real terminal is on the other end - under the
    tests, or with the output piped into a file, there is nothing to echo. The
    old settings go back on the way out, including if the player presses
    Ctrl-C, so the terminal is never left in a strange state.
    """
    if not _at_a_real_terminal() or sys.platform == "win32":
        # Windows needs none of this: it is read with ``msvcrt.getwch``, which
        # does not echo in the first place.
        yield
        return

    try:
        import termios

        keyboard = sys.stdin.fileno()
        before = termios.tcgetattr(keyboard)
        quiet = termios.tcgetattr(keyboard)
        quiet[3] &= ~(termios.ECHO | termios.ICANON)  # the "local" flags
        quiet[6][termios.VMIN] = 0  # never wait for a key that is not there
        quiet[6][termios.VTIME] = 0
    except (ImportError, OSError, ValueError):  # pragma: no cover
        # No termios, or a stdin that is not really a keyboard - an IDE's
        # console, say. Nothing to quieten, so type it out as it comes.
        yield
        return

    try:
        termios.tcsetattr(keyboard, termios.TCSADRAIN, quiet)
        yield
    finally:
        termios.tcsetattr(keyboard, termios.TCSADRAIN, before)


def _at_a_real_terminal() -> bool:
    """Return True if a person is watching this, rather than a test or a pipe."""
    try:
        return _write is print and sys.stdout.isatty() and sys.stdin.isatty()
    except (AttributeError, ValueError):  # pragma: no cover - a closed stream
        return False


def _pressed_a_key() -> bool:
    """Return True if the player has hit a key, and swallow what they typed.

    This is how "press Enter to skip" works: while a line is being typed out
    we peek at the keyboard between characters without waiting for it. Whatever
    they pressed is read and thrown away, so it does not turn up later as an
    answer to a menu.

    Both halves are guarded, because the team is on macOS, Linux and Windows,
    and neither way of peeking exists on all three. If neither works, nothing
    is skipped and the story is simply typed out as before.
    """
    try:
        if sys.platform == "win32":  # pragma: no cover - only reachable on Windows
            import msvcrt

            if not msvcrt.kbhit():
                return False
            while msvcrt.kbhit():
                msvcrt.getwch()
            return True

        import select
        import termios

        if not select.select([sys.stdin], [], [], 0)[0]:
            return False
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
        return True
    except Exception:  # pragma: no cover - no keyboard to peek at (a pipe, an IDE)
        return False


def is_instant() -> bool:
    """Return True if the story is being shown all at once instead of typed."""
    return _instant


def set_instant(instant: bool) -> None:
    """Show the story instantly from now on, or go back to typing it out.

    Offered in the Options menu for the player on their second or third run,
    who has read every word already (issue #151).
    """
    global _instant
    _instant = instant


def ask(prompt: str = "> ", timeout: float | None = None) -> str:
    """Ask the player for a line of input, and handle the words that work anywhere.

    ``pause``, ``quit`` and ``scoreboard`` work at every prompt, even in the
    middle of a fight. After a look at the scoreboard, or a quit the player
    takes back, the same question is simply asked again.

    Args:
        prompt: What to show in front of the cursor.
        timeout: How many seconds the player has, or None to wait for ever.

    Raises:
        TimedOut: If the clock runs out before the player presses Enter. This
            only happens where the keyboard can be watched while waiting - a
            real terminal. Anywhere else the answer is simply waited for, and
            whoever asked looks at the clock afterwards.
        PauseRequested: If the player typed ``pause``; the game is saved.
        QuitRequested: If the player typed ``quit`` and confirmed it.
    """
    while True:
        answer = _answer_or_none(prompt, timeout)
        if answer is not None:
            return answer


def _answer_or_none(prompt: str, timeout: float | None) -> str | None:
    """Read one answer, or return None if it was one of the words that work anywhere.

    None means "that was dealt with - ask the same thing again". :func:`choose`
    uses it to show its list again, so the player is not left looking at a
    scoreboard with nothing to pick from.
    """
    answer = _read_line(prompt, timeout).strip()
    word = answer.lower()

    if word == "pause" and _pause_handler is not None:
        _pause_handler()
        raise PauseRequested
    if word == "quit" and _quit_handler is not None:
        if _quit_handler():
            raise QuitRequested
        return None
    if word == "scoreboard" and _scoreboard_handler is not None:
        _scoreboard_handler()
        return None
    return answer


def _read_line(prompt: str, timeout: float | None) -> str:
    """Read one line, giving up after ``timeout`` seconds where that is possible."""
    # Only a real keyboard can be watched while waiting. A test has its own
    # way of getting input, so it is simply waited for.
    if timeout is not None and _read is input and _at_a_real_terminal():
        return _read_from_keyboard(prompt, timeout)
    return _read(prompt)


def _read_from_keyboard(prompt: str, timeout: float) -> str:  # pragma: no cover
    """Read a line from the real keyboard, or raise :class:`TimedOut`.

    ``input()`` cannot be interrupted, so the keyboard is watched instead. As
    with :func:`_pressed_a_key`, there is one way to do that on Windows and
    another on macOS and Linux.
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()
    end = time.monotonic() + max(0.0, timeout)

    if sys.platform == "win32":
        import msvcrt

        typed: list[str] = []
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getwch()
                if key in "\r\n":
                    sys.stdout.write("\n")
                    return "".join(typed)
                if key == "\x03":
                    raise KeyboardInterrupt
                if key in "\x00\xe0":  # an arrow or function key: two codes
                    msvcrt.getwch()
                elif key == "\x08":
                    if typed:
                        typed.pop()
                        sys.stdout.write("\b \b")
                else:
                    typed.append(key)
                    sys.stdout.write(key)
                sys.stdout.flush()
            elif time.monotonic() >= end:
                sys.stdout.write("\n")
                raise TimedOut
            else:
                time.sleep(0.01)

    import select
    import termios

    if not select.select([sys.stdin], [], [], max(0.0, end - time.monotonic()))[0]:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)  # drop a half-typed answer
        sys.stdout.write("\n")
        raise TimedOut
    line = sys.stdin.readline()
    if not line:
        raise EOFError
    return line.rstrip("\n")


def now() -> float:
    """Return the time, in seconds, for anything that has to be timed.

    Everything that watches a clock goes through here for the same reason
    everything that prints goes through :func:`say`: a test can hand the game
    a clock it controls, and time a question without waiting for one.
    """
    return _clock()


def pause(seconds: float) -> None:
    """Wait ``seconds`` before continuing. Uses the same clock as narrate."""
    _sleep(seconds)


def set_pause_handler(handler: Callable[[], None] | None) -> None:
    """Set the function called when the player types ``pause``."""
    global _pause_handler
    _pause_handler = handler


def set_quit_handler(handler: Callable[[], bool] | None) -> None:
    """Set the function that asks whether a typed ``quit`` is meant."""
    global _quit_handler
    _quit_handler = handler


def set_scoreboard_handler(handler: Callable[[], None] | None) -> None:
    """Set the function called when the player types ``scoreboard``."""
    global _scoreboard_handler
    _scoreboard_handler = handler


def choose(
    prompt: str,
    options: Sequence[str],
    back: str | None = None,
    timeout: float | None = None,
) -> int | None:
    """Show a numbered list and let the player pick one.

    The player never types a word: they type the number next to what they
    want. Anything else is answered with a nudge and the list is shown again,
    so it is impossible to get stuck.

    Args:
        prompt: The question above the list, e.g. "What do you do?".
        options: What the player can choose, in the order shown.
        back: The label for a "0" option that returns without choosing, or
            None for a list that must be answered.
        timeout: How many seconds the player has in all, counting any wrong
            tries, or None to wait for ever. See :func:`ask`.

    Returns:
        The index of the chosen option, or None if the player chose ``back``.
    """
    deadline = None if timeout is None else now() + timeout
    while True:
        say()
        say(prompt)
        for number, option in enumerate(options, start=1):
            say(f"  {number}) {option}")
        if back is not None:
            say(f"  0) {back}")

        typed = _answer_or_none("> ", None if deadline is None else max(0.0, deadline - now()))
        if typed is None:
            continue
        if back is not None and typed == "0":
            return None
        if typed.isdigit() and 1 <= int(typed) <= len(options):
            return int(typed) - 1
        say("Type the number of the thing you want.")


def use_io(
    write: Callable[[str], None],
    read: Callable[[str], str],
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Replace the input, output, waiting and timing functions. Tests only."""
    global _write, _read, _sleep, _clock, _instant
    _write, _read, _sleep, _clock = write, read, sleep, clock
    _instant = False
