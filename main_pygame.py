"""Runs the real console game inside a Pygame window that acts like a terminal.

We used to reimplement say()/narrate()/ask()/choose() for Pygame, but that
broke every time ui.py changed. This version runs your actual main.py
unchanged in a background thread, and only fakes stdout/stdin so the game
never knows it's not a real terminal.

Run it with:

    python main_pygame.py

Type + Enter like a normal console. Any key skips typing/pauses. Escape
(or closing the window) saves and quits, the same as typing "pause". A timed
question shows its seconds counting down, and presses Enter for you when
they run out.

Quick map of the file:
    _StreamToQueue                   -> the fake stdout - also where typed
                                         vs instant lines get told apart and
                                         the game thread gets blocked (see
                                         its docstring)
    _QueueToStream                   -> the fake stdin
    _make_dialogue_sleep             -> lets a keypress fast-forward mid-typing
    TerminalWindow.__init__          -> all the state the window tracks
    TerminalWindow.wait_for_line_advance -> blocks the game thread until a press
    TerminalWindow.start_game_thread -> wires the fakes in, starts the game
    TerminalWindow._pump_output      -> turns printed text into screen lines
    TerminalWindow._handle_events    -> turns keypresses into "advance the box" or typed answers
    TerminalWindow._check_clock      -> presses Enter when a timed question runs out
    TerminalWindow._draw             -> draws everything each frame
    TerminalWindow._draw_intro       -> the old full-screen layout, before the first room
    TerminalWindow._draw_dialogue_box -> draws the Undertale-style box, lower-center
    TerminalWindow._draw_map_overlay -> draws the map in its own corner panel
    TerminalWindow._render_map_line  -> renders one map line with the same shadow as the main text
    TerminalWindow._load_room_image  -> loads/scales a room's background image, if it has one
    TerminalWindow._load_static_image -> the shared loader behind that, and
                                          the intro screen's background
    TerminalWindow.run               -> the main loop tying it all together
"""

from __future__ import annotations

import ctypes
import math
import os
import queue
import sys
import threading
import time
import traceback

import pygame

import ui  # the real console ui.py - nothing here reimplements any of it
from main import main as run_console_game

# an exe built with `pyinstaller --windowed` has no console at all, so
# Windows hands it fake stdout/stderr that crash on the first write instead
# of just being empty - avoid that whole trap by building WITH a console
# (leave off --windowed) and hiding that console the instant we start, so
# it never flashes on screen but stdout/stderr stay real, working streams
if sys.platform == "win32" and getattr(sys, "frozen", False):
    console_window = ctypes.windll.kernel32.GetConsoleWindow()
    if console_window:
        ctypes.windll.user32.ShowWindow(console_window, 0)  # 0 = SW_HIDE

# belt-and-suspenders: if stdout/stderr are still missing or broken for any
# other reason (a different packager, a future PyInstaller change, etc.),
# give them somewhere harmless to write instead of crashing the game
try:
    sys.stdout.write("")
except Exception:
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115 - stays open all program
try:
    sys.stderr.write("")
except Exception:
    sys.stderr = open(os.devnull, "w")  # noqa: SIM115 - stays open all program

# tells the game "stop waiting" - the game reads it as the end of the input
_EOF = object()

# tells the game "the clock ran out" - sent by the window, never typed
_TIMED_OUT = object()

FPS = 60

# fonts with glyphs for the unusual Unicode some puzzle text uses - the main
# font alone can't draw these, so they live next to this file as small files
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# the game's main font, bundled as an actual file rather than asked for by
# name - see TerminalWindow._load_main_font for why. Free, redistributable,
# monospaced, and designed for exactly this (small, screen-rendered text) -
# see assets/JetBrainsMono-OFL.txt for its license.
_MAIN_FONT_FILE = "JetBrainsMono-Regular.ttf"

_FALLBACK_FONT_FILES = ["unifont-subset.otf", "unifont-upper-subset.otf"]

# background image per room, keyed by the exact "== Room Name ==" header
# text the game prints when you walk in (see TerminalWindow._is_room_header)
# - a room with no entry here just shows a plain black background, same as
# every room did before this existed. Photos are reused across rooms that
# are the same kind of real-world space (two ordinary classrooms, two plain
# hallways) - rooms written as something stranger than the real room they're
# based on (classroom_2015's furniture-tent, lab_2001's forest) are left
# without a photo on purpose, since a straight photo of the real room would
# fight the text instead of matching it.
_ROOM_IMAGES = {
    "== Classroom 2.035 ==": "classroom_2035.jpg",
    "== Classroom 2031 ==": "classroom_2035.jpg",
    "== The Blue corridor ==": "hallway.jpg",
    "== The Red corridor ==": "hallway.jpg",
    "== LAB2.003 ==": "computer_lab.jpg",
    "== Student society ==": "student_society.jpg",
    "== Project Room 3 ==": "project_room.jpg",
}

# the background behind the very first screen - the name prompt and intro
# blurb, before any room header exists (see TerminalWindow._draw_intro) -
# same "just don't draw anything if it's missing" fallback as _ROOM_IMAGES
_INTRO_IMAGE = "intro.jpg"

# the exact characters rooms/classroom_2031.py's last puzzle question uses
# (Canadian syllabics, box-drawing, math symbols, ...) that the main font
# (_MAIN_FONT_FILE) has no glyph for - everything else (ascii, the heart
# symbol, accented letters elsewhere in the game) keeps using it as normal.
# This has to be an
# exact list rather than asking pygame "can you draw this character" at
# runtime: that check (Font.metrics()) turned out to report a character as
# drawable even when the installed font can't actually draw it, so it
# can't be trusted to decide this. Add a room with similarly unusual
# Unicode later? Add its non-ascii characters here too.
_NEEDS_FALLBACK_FONT = set("ᒲᒷᓭᔑ↸∷⊣⋮⍊⍑⎓╎⚍リꖎ𝙹")

# every line of the main text gets a soft shadow behind it (see
# TerminalWindow._render_text) so it stays readable over a room's
# background image instead of just floating on top of it bare
_TEXT_SHADOW_COLOR = (40, 40, 40)
_TEXT_SHADOW_OFFSET = 1  # pixels, down and to the right
_TEXT_SHADOW_ALPHA = 190  # 0 = invisible, 255 = fully solid

# a near-solid tint behind the whole map panel, on top of each line's own
# shadow. This used to be lighter (110) so a room's background image showed
# through - but the map's thin box-drawing lines are much easier to lose in
# a busy photo than the dialogue box's prose is, so the map panel now needs
# to be MORE opaque than the dialogue box (_BOX_PANEL_ALPHA), not less. At
# this alpha the photo behind it is only a faint hint, and the map reads as
# a solid HUD element regardless of what room it's drawn over.
_MAP_PANEL_ALPHA = 235

# the ASCII conventions floor_map.py's PLAN is drawn with (see that file's
# WALLS and HERE) - mirrored here rather than imported, the same way
# _is_map_top_border/_is_map_last_line above pattern-match on plain printed
# text instead of reaching into floor_map.py: this file only ever acts on
# what the game actually printed, never on the game's own modules. Used by
# TerminalWindow._crop_map_to_local_area to figure out, from the text
# alone, which part of the map is "the room you're in and its doors".
_MAP_WALL_CHARS = frozenset("+-|=X")
_MAP_HERE_CHAR = ":"

# extra rows/columns of margin kept around the cropped area, so the crop
# lands just outside the outermost wall it keeps rather than slicing
# straight through it
_MAP_CROP_PADDING = 1

# the little Undertale-style dialogue box, lower-center - height just grows
# to fit whatever it's currently showing (capped at _BOX_MAX_ROWS so one
# huge menu can't fill the screen). Width is NOT a fixed size any more: text
# is wrapped as if the box were _BOX_WIDTH_FRACTION of the screen wide (so a
# long paragraph still wraps at the same point it always has), but the box
# is then drawn only as wide as its longest actual line needs, down to
# _BOX_MIN_WIDTH_FRACTION - so a short menu like "1) Look at the evacuation
# plan" gets a box that hugs the text instead of one that's the same width
# as a full paragraph, with empty space padding out both sides.
_BOX_WIDTH_FRACTION = 0.7
_BOX_MIN_WIDTH_FRACTION = 0.28
_BOX_MAX_ROWS = 10
_BOX_PANEL_ALPHA = 150

# set AMAZE_PYGAME_DEBUG=1 to print every fake-stdout write to the real terminal
_DEBUG = os.environ.get("AMAZE_PYGAME_DEBUG") == "1"
_debug_start = time.monotonic()


def _debug_log(message: str) -> None:
    if _DEBUG:
        print(f"[{time.monotonic() - _debug_start:7.3f}s] {message}", file=sys.stderr, flush=True)


class _StreamToQueue:
    """Fake sys.stdout - catches what the game prints and queues it for the window.

    This is also the ONE place that knows, in real time, whether
    what it's catching is being typed out character by character
    (narrate()'s _type_line()) or handed over as a whole line at once
    (say()) - and that's exactly the difference between a line the player
    needs to press through and an instant one (a menu, a prompt). See
    write() below: the moment a typed line's newline arrives, it blocks
    the GAME THREAD itself right there until the player presses something.
    That's deliberate, not just a display trick - if only the window's
    drawing paused, the game thread would keep typing further lines in the
    background at its own pace while the player was still reading the
    first one, so by the time they pressed, everything after it would
    already be sitting there fully typed instead of animating in.

    This treats every typed line - i.e. every line ui.py's own _wrap()
    hands to _type_line() - as one pause point. It doesn't try to guess
    where a sentence "really" ends; that's a room-content problem, not a
    display one. A room whose narrate() text is written as short,
    deliberately-paced parts (see rooms/corridor_blue.py for the pattern)
    already stops in the right places, because each part IS a short line.
    A room written as one long block of prose gets column-wrapped by
    ui.py and stops wherever that wrap happens to land - which is why
    long blocks belong in short parts instead, not something this file
    should be parsing English to work around.
    """

    def __init__(self, out_queue: queue.Queue[str], window: TerminalWindow) -> None:
        self._queue = out_queue
        self._window = window
        self._typing_current_line = False

    def write(self, text: str) -> None:
        # this is the whole trick: print()/say()/narrate() call write(), and it
        # lands here instead of a real screen
        if not text:
            return
        _debug_log(f"stdout.write() len={len(text)} text={text!r}")
        if text == "\n":
            was_typed = self._typing_current_line
            self._typing_current_line = False
            self._queue.put(text)
            if was_typed:
                # a real typed line just finished - stop the game thread
                # dead here and don't let it write anything more until the
                # player presses to move on
                self._window.wait_for_line_advance()
            return
        # _type_line() writes one character at a time; say()'s _write()
        # (== print()) hands over a whole already-built line in a single
        # write() call - a lone character is the signature of the typed
        # path, a longer string is the signature of the instant one
        self._typing_current_line = len(text) == 1
        self._queue.put(text)

    def flush(self) -> None:
        pass  # nothing to flush, queue.put() already delivers instantly

    def isatty(self) -> bool:
        # fixes bug where narrate() types instantly instead of one character at a time
        return True


class _QueueToStream:
    """Fake sys.stdin - the game blocks here until the player types something."""

    def __init__(self, in_queue: queue.Queue[object], on_wait_start, on_wait_end) -> None:
        self._queue = in_queue
        self._on_wait_start = on_wait_start
        self._on_wait_end = on_wait_end

    def read_answer(self, prompt: str) -> str:
        """What the game reads every answer with - see read_line_with_clock.

        Never the built-in input(), on purpose: ui.py's own timed-question
        code watches the real keyboard, and the real keyboard is not where
        the player is typing - the window is. On macOS/Linux that crashed, on
        Windows every timed question ran out.
        """
        sys.stdout.write(prompt)
        self._on_wait_start()
        try:
            line = self._queue.get()
        finally:
            self._on_wait_end()
        if line is _EOF:
            raise EOFError
        if line is _TIMED_OUT:
            raise ui.TimedOut  # the same thing ui.py does in a real terminal
        return line

    def readline(self) -> str:
        # nothing in the game calls this (ui.py reads with read_answer), but a
        # stray input() should still work rather than crash
        try:
            return f"{self.read_answer('')}\n"
        except (EOFError, ui.TimedOut):
            return ""  # empty string = EOF, same as a real terminal

    def isatty(self) -> bool:
        # fixes the same narrate() bug as above - ui.py checks BOTH stdout and stdin
        return True

    def fileno(self) -> int:
        # no real file behind this, so raise like a closed/fake stream would - not a crash
        raise OSError("this is not a real terminal - no file descriptor")


def _make_dialogue_sleep(window: TerminalWindow):
    """Swaps in for time.sleep() - a keypress fast-forwards through typing.

    A keypress fast-forwards through the typing delay between characters,
    finishing the current line instantly instead of waiting out the rest
    of its real-time typing.

    The "stop and wait for a press before the next line can start" behaviour
    does NOT live here - narrate()'s per-character writes give no sleep()
    call between two on-screen LINES to hook (only between two authored
    PARTS), so that's handled where the text actually is: _StreamToQueue.
    write(), which watches the character stream itself and blocks the game
    thread the instant a typed line finishes (see TerminalWindow.
    wait_for_line_advance). This function's other job is fast-forwarding a
    line that's still mid-typing (skip_event, below).

    It also has a THIRD job: the press that unblocks wait_for_line_advance
    also sets window.skip_pause_event, and the very next sleep() call after
    that - whatever narrate() was about to wait on next, an explicit float
    or the default PART_DELAY between two parts - is let through instantly
    instead of actually waiting. Without this, the player presses to move
    on, the box goes blank for the length of that pause, and only then does
    the next part start appearing - a dead gap with nothing on screen and
    nothing to do but wait, right after the player just asked to keep
    going. It's consumed the first time it's checked (whatever sleep() call
    that turns out to be - see the comment where it's set) so it can only
    ever cancel the one pause a press was actually waiting on, not linger
    and eat a later, unrelated one.

    Passed into ui.use_io() as the sleep argument - the one official hook
    the game already has for this, so nothing in ui.py gets touched.
    """

    def _sleep(seconds: float) -> None:
        if window.quitting:
            return  # Escape was pressed - rush the game to its save, no waiting
        if window.skip_pause_event.is_set():
            window.skip_pause_event.clear()
            return
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if window.skip_event.is_set():
                return
            time.sleep(0.005)  # check often so a keypress feels instant

    return _sleep


class TerminalWindow:
    """A fullscreen window: shows the game's fake-stdout output, types into its fake-stdin."""

    # printed after every answered prompt, to separate it from what comes next
    DIVIDER = "-" * 64

    def __init__(self) -> None:
        """Set up the window itself, and all the state tracked between frames."""
        pygame.init()
        info = pygame.display.Info()
        self.width, self.height = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        pygame.display.set_caption("a-maze-ing-delft")

        font_size = max(12, min(18, self.height // 60))
        self.font = self._load_main_font(font_size)
        # some puzzle text uses unusual Unicode (Canadian syllabics, math
        # symbols, ...) the main font has no glyphs for - these bundled
        # fonts cover that, and _render_text() below picks whichever one
        # actually has each character instead of drawing a blank box for it
        self.fallback_fonts = self._load_fallback_fonts(font_size)
        # smaller than the main text, so it reads as a HUD panel rather
        # than taking over the screen, but not so small it turns blurry
        self.map_font = self._load_main_font(max(12, int(font_size * 0.78)))
        # bigger than the main text - used just for the current question
        # (the prompt and its numbered choices) inside the dialogue box, so
        # what the player can actually act on stands out from narration -
        # see _box_lines/_render_text's `big` argument
        self.menu_font = self._load_main_font(int(font_size * 1.35))
        self.line_height = font_size + 4
        self.margin = 10

        self.lines: list[tuple[str, str]] = []  # (text, color) for every finished line
        self.current_line = ""  # the line being built right now, character by character
        self.typed = ""  # what the player has typed for their current answer

        # the pinned "== Room Name ==" line, kept separate so it never scrolls away
        self.room_header: str | None = None

        # this room's background image (see _ROOM_IMAGES), swapped in
        # _pump_output() the instant a new room header arrives - None if
        # this room has no image, which just means nothing gets drawn.
        # Starts out holding the intro screen's own background (_INTRO_IMAGE)
        # instead of None, since _draw() blits whatever's here regardless of
        # room_header - the first real room header overwrites this the same
        # way every later one does.
        self.room_image: pygame.Surface | None = self._load_static_image(_INTRO_IMAGE)

        # the last "Look at the evacuation plan" output, drawn in its own
        # corner panel instead of the normal scrollback - see _pump_output
        self.map_overlay: list[str] | None = None
        self._capturing_map = False
        self._map_capture_buffer: list[str] = []

        self.game_over = False
        # True from the moment Escape is pressed - the game thread then stops
        # waiting for presses and sleeps, so it reaches its save straight away
        self.quitting = False
        self._quit_requested_at = 0.0

        # True only while the game is blocked waiting on an answer, not while narrating
        self.waiting_for_input = False

        # when a timed question runs out (time.monotonic()), or None if untimed
        self.deadline: float | None = None

        # set the instant a new prompt starts, cleared once used - see _pump_output
        self._prompt_pending = False

        # where the current unanswered question starts in self.lines
        self._prompt_start: int | None = None

        # index of the last blank line seen - every question starts with one
        self._last_blank_index: int | None = None

        # game thread -> window: "here's what I printed"
        self.out_queue: queue.Queue[str] = queue.Queue()
        # window -> game thread: "here's what you typed"
        self.in_queue: queue.Queue[object] = queue.Queue()
        # set by a keypress while a line is still typing - finishes it instantly
        self.skip_event = threading.Event()
        # set by a keypress once a typed line has finished and is waiting to
        # be pressed past - what actually unblocks the game thread (see
        # _StreamToQueue.write / wait_for_line_advance)
        self.advance_event = threading.Event()
        # set alongside advance_event, by that same press - see
        # _make_dialogue_sleep for what it's for
        self.skip_pause_event = threading.Event()
        # True only in that state - the game thread is genuinely blocked,
        # not just "the window happens to not be showing more yet"
        self.waiting_to_advance = False
        # where the dialogue box's current "page" starts in self.lines -
        # advances only when the player presses past a completed line, or
        # answers a question (see _draw_dialogue_box / _handle_events)
        self.box_start = 0

    def _wait_start(self) -> None:
        self.waiting_for_input = True
        self._prompt_pending = True

    def _wait_end(self) -> None:
        self.waiting_for_input = False

    def wait_for_line_advance(self) -> None:
        """Block the game thread right where a typed line just finished.

        Called from the GAME THREAD (see _StreamToQueue.write) the instant
        a typed line finishes - blocks it right there until the player
        presses something. This is what stops the game thread from racing
        ahead typing the next line (or several) in the background while the
        player is still reading the one before - only pausing the DISPLAY
        wouldn't be enough, since the text would already be fully typed and
        waiting by the time they caught up.
        """
        if self.quitting:
            return  # Escape was pressed - don't make the player press through to the save
        self.advance_event.clear()
        self.waiting_to_advance = True
        self.advance_event.wait()
        self.waiting_to_advance = False

    def start_game_thread(self) -> None:
        """Wire the fake stdout/stdin in, then start the real game in the background."""
        sys.stdout = _StreamToQueue(self.out_queue, self)
        keyboard = _QueueToStream(self.in_queue, self._wait_start, self._wait_end)
        sys.stdin = keyboard

        # the only place this file changes game behaviour - see _make_dialogue_sleep,
        # and read_line_with_clock below for how answers are read
        ui.use_io(write=print, read=keyboard.read_answer, sleep=_make_dialogue_sleep(self))

        # ui.py's _type_line() has its OWN independent skip check that
        # peeks at the real console's keyboard buffer (msvcrt on Windows) -
        # a different keyboard than the pygame window entirely. run_game.bat
        # leaves that console window open behind this one, so stray input
        # there can trip it, which sets narrate()'s "skipped" flag and
        # writes the REST of that line in one go instead of character by
        # character. That's not just a skipped animation - _StreamToQueue.
        # write() tells a typed line apart from an instant one by whether
        # it arrived as single characters or one whole string (see its
        # docstring), so a line mangled this way would stop needing a press
        # at all. Disabling it keeps every line's typing genuinely one
        # write per character, which the pacing logic depends on.
        ui._pressed_a_key = lambda: False

        _debug_log(
            "after use_io(): "
            f"ui._write is print = {getattr(ui, '_write', None) is print}, "
            f"sys.stdout.isatty() = {sys.stdout.isatty()}, "
            f"ui.CHAR_DELAY = {getattr(ui, 'CHAR_DELAY', 'MISSING')}"
        )

        # wraps every read of an answer: resets the skip flag, so skipping one
        # line doesn't skip the next, and starts the clock if the question is
        # timed. Hooked on ui._read_line rather than ui.ask because it is the
        # one place EVERY answer passes through - ui.choose() reads its menus
        # without going through ask() at all, so a hook on ask() never saw a
        # timed multiple-choice question.
        def read_line_with_clock(prompt: str, timeout: float | None) -> str:
            self.skip_event.clear()
            self.deadline = None if timeout is None else time.monotonic() + timeout
            try:
                return keyboard.read_answer(prompt)
            finally:
                self.deadline = None

        ui._read_line = read_line_with_clock

        thread = threading.Thread(target=self._run_game, daemon=True)
        thread.start()

    def _run_game(self) -> None:
        try:
            run_console_game()
        except (EOFError, ui.PauseRequested, ui.QuitRequested):
            # "pause" (or Escape) or a confirmed "quit" during the very first
            # room's arrival, before game.py's own loop is there to catch it -
            # the game has already saved (or been told not to), so it's a clean end
            pass
        except Exception:
            traceback.print_exc()  # real terminal, not the window - bugs stay visible
        finally:
            self.out_queue.put("\n[Game ended - press any key to close the window]\n")
            self.game_over = True

    @staticmethod
    def _is_room_header(line: str) -> bool:
        # matches "== Room Name ==" - what game.py prints when you walk into a room
        return line.startswith("== ") and line.endswith(" ==") and len(line) > 6

    @staticmethod
    def _is_map_top_border(line: str) -> bool:
        # floor_map.py's plan always starts with a wall row like this
        # ("+" and "-" only) - nothing else in the game prints one, so
        # seeing this line means "Look at the evacuation plan" was chosen
        stripped = line.strip()
        is_wall_row = len(stripped) > 2 and stripped[0] == "+" and stripped[-1] == "+"
        return is_wall_row and set(stripped) <= set("+-")

    @staticmethod
    def _is_map_last_line(line: str) -> bool:
        # floor_map.py's render() always ends with exactly this sentence
        return line.startswith(" You are in ")

    @staticmethod
    def _option_label(typed: str, block: list[tuple[str, str]]) -> str | None:
        # finds "1) Look around" for typed="1" and returns "Look around"
        prefix = f"{typed}) "
        for text, _color in block:
            stripped = text.strip()
            if stripped.startswith(prefix):
                return stripped[len(prefix) :]
        return None

    # if a map capture somehow never reaches its last line, give up after
    # this many lines rather than swallowing the rest of the game's output
    _MAX_MAP_CAPTURE_LINES = 200

    def _pump_output(self) -> None:
        """Read what the game has printed since last frame, turn it into screen lines.

        Note this never has to decide which lines need a
        press - _StreamToQueue.write() already settled that on the game
        thread itself, before this ever sees the character (see its
        docstring); by the time text reaches here the pacing has already
        happened, this is purely "turn characters into (text, color) rows".
        """
        try:
            while True:
                chunk = self.out_queue.get_nowait()
                for character in chunk:
                    if character == "\n":
                        if self._capturing_map:
                            self._map_capture_buffer.append(self.current_line)
                            if self._is_map_last_line(self.current_line):
                                # the whole map arrived - crop it down to
                                # the current room and its doors (see
                                # _crop_map_to_local_area) and show that in
                                # its own corner instead of the normal
                                # scrollback
                                self.map_overlay = self._crop_map_to_local_area(
                                    self._map_capture_buffer
                                )
                                self._map_capture_buffer = []
                                self._capturing_map = False
                            elif len(self._map_capture_buffer) > self._MAX_MAP_CAPTURE_LINES:
                                # never found the end - something's off, so
                                # don't lose this text, just show it plainly
                                self.lines.extend(
                                    (line, "white") for line in self._map_capture_buffer
                                )
                                self._map_capture_buffer = []
                                self._capturing_map = False
                        elif self._is_map_top_border(self.current_line):
                            # the map's first line - capture it and everything
                            # after it instead of adding it to self.lines
                            self._capturing_map = True
                            self._map_capture_buffer = [self.current_line]
                        elif self._is_room_header(self.current_line):
                            # new room = clean screen, but keep the header pinned up top
                            self.room_header = self.current_line
                            self.room_image = self._load_room_image(self.current_line)
                            self.lines = []
                            self.map_overlay = None
                            self._prompt_start = None
                            self._last_blank_index = None
                            self.box_start = 0
                        else:
                            self.lines.append((self.current_line, "white"))
                            if self.current_line == "":
                                self._last_blank_index = len(self.lines) - 1
                        self.current_line = ""
                        # each new line starts fresh - needs its own press to skip
                        self.skip_event.clear()
                    else:
                        self.current_line += character
        except queue.Empty:
            pass

        if self._prompt_pending:
            # a new question just started - remember where it began, to collapse it later
            self._prompt_start = self._last_blank_index if self._last_blank_index is not None else 0
            self._prompt_pending = False

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN:
                if self.game_over:
                    self._quit()
                    continue
                if event.key == pygame.K_ESCAPE:
                    self._quit()
                    continue
                if self.waiting_to_advance:
                    # a typed line just finished and the game thread is
                    # genuinely blocked on it (see wait_for_line_advance) -
                    # this press is what unblocks it. Takes priority over
                    # everything else below in case waiting_for_input is
                    # somehow also true (shouldn't happen while blocked, but
                    # this is the state that matters if it ever does)
                    self.box_start = len(self.lines)
                    self.advance_event.set()
                    # this press is what the player experiences as "moving
                    # things along" - whatever narrate() does next (the
                    # pause between this part and the next, either an
                    # explicit float or the default PART_DELAY) is dead time
                    # they didn't ask for, only the typing animation is
                    # worth keeping. See _make_dialogue_sleep.
                    self.skip_pause_event.set()
                    continue
                if not self.waiting_for_input:
                    # game is busy narrating, not asking anything - this
                    # press just finishes the current line's typing instantly
                    self.skip_event.set()
                    continue
                if event.key == pygame.K_RETURN:
                    self._submit(self.typed)
                elif event.key == pygame.K_BACKSPACE:
                    self.typed = self.typed[:-1]
                elif event.unicode and event.unicode.isprintable():
                    self.typed += event.unicode

    def _check_clock(self) -> None:
        """Press Enter for the player when a timed question runs out."""
        deadline = self.deadline
        if self.waiting_for_input and deadline is not None and time.monotonic() >= deadline:
            self._submit(_TIMED_OUT)

    def _seconds_left(self) -> int | None:
        # what the countdown shows under a timed question, or None if untimed
        if not self.waiting_for_input or self.deadline is None:
            return None
        return max(0, math.ceil(self.deadline - time.monotonic()))

    def _submit(self, answer: object) -> None:
        """Send an answer to the game, and tidy the question away on screen.

        ``answer`` is what the player typed, or _TIMED_OUT when the clock did
        the pressing - either way the screen looks the same as pressing Enter.
        """
        answer_line = self.current_line + self.typed
        if self._prompt_start is not None:
            # collapse the whole question down to just what you picked
            block = self.lines[self._prompt_start :]
            label = self._option_label(self.typed, block)
            if label is not None:
                # show "Look around", not "1"
                answer_line = f"{self.current_line}{label}"
            del self.lines[self._prompt_start :]
            self._prompt_start = None
            self._last_blank_index = None
        self.lines.append((answer_line, "gray"))
        self.lines.append((self.DIVIDER, "gray"))
        self.current_line = ""
        self.typed = ""
        # stop listening now, not when the game thread gets round to it - so a
        # second Enter (or the clock) in the next frame can't answer twice
        self.waiting_for_input = False
        self.deadline = None
        self.in_queue.put(answer)
        # start the box fresh for whatever comes next, instead
        # of leaving the answered question sitting in it
        self.box_start = len(self.lines)

    def _quit(self) -> None:
        """Save and quit, the same as typing "pause" - or just quit if there is nothing to save."""
        if self.quitting:
            return  # don't save twice if Escape gets pressed more than once
        self.quitting = True
        self._quit_requested_at = time.monotonic()
        if self.game_over:
            return
        # ui.py only has a pause handler once a game is being played - before
        # that (typing your name) there is nothing to save yet
        if ui._pause_handler is not None:
            self.typed = ""
            self.in_queue.put("pause")
        else:
            self.in_queue.put(_EOF)
        # the game thread might be genuinely blocked in wait_for_line_advance
        # or mid-skip right now - let it go so it can reach the answer above and
        # shut down cleanly instead of hanging until the window is killed
        self.advance_event.set()
        self.skip_event.set()

    def _centered_x(self, surface: pygame.Surface) -> int:
        # centers text horizontally, never further left than the margin
        return max(self.margin, (self.width - surface.get_width()) // 2)

    def _load_room_image(self, header: str) -> pygame.Surface | None:
        # header is the exact "== Room Name ==" text just printed - look it
        # up in _ROOM_IMAGES rather than touching the room files themselves,
        # same reason _is_room_header() only ever pattern-matches on text
        filename = _ROOM_IMAGES.get(header)
        if filename is None:
            return None
        return self._load_static_image(filename)

    def _load_static_image(self, filename: str) -> pygame.Surface | None:
        # shared by _load_room_image (looked up per room) and the intro
        # screen's fixed background (_INTRO_IMAGE) - same file, same scaling
        path = os.path.join(_ASSETS_DIR, filename)
        if not os.path.exists(path):
            # a typo'd filename, or the image just hasn't been added yet -
            # show nothing rather than crash the whole game over a picture
            return None
        image = pygame.image.load(path).convert_alpha()
        # stretches to fill this computer's screen exactly, whatever its
        # resolution happens to be
        return pygame.transform.scale(image, (self.width, self.height))

    @staticmethod
    def _load_main_font(size: int) -> pygame.font.Font:
        # bundled as an actual file (_MAIN_FONT_FILE) instead of asked for
        # by name the way this used to (pygame.font.SysFont("consolas",
        # size)). SysFont only draws with an installed font if a machine
        # genuinely has one by that name - "consolas" is a Windows font, so
        # on the team's Mac and Linux machines it was silently substituting
        # some other monospace font instead, with no error or warning. That
        # meant the exact same line of code could render crisp on one
        # laptop and soft/generic on another - not a bug in any one
        # person's setup, just this never having been guaranteed to be the
        # same font twice. Loading the bundled file guarantees everyone
        # sees the same one, chosen specifically for small on-screen text.
        path = os.path.join(_ASSETS_DIR, _MAIN_FONT_FILE)
        if os.path.exists(path):
            return pygame.font.Font(path, size)
        return pygame.font.SysFont("consolas", size)  # asset missing - better than crashing

    @staticmethod
    def _load_fallback_fonts(font_size: int) -> list[pygame.font.Font]:
        # skips missing files instead of crashing - worst case, unusual
        # characters go back to drawing as boxes, same as before this existed
        fonts = []
        for filename in _FALLBACK_FONT_FILES:
            path = os.path.join(_ASSETS_DIR, filename)
            if os.path.exists(path):
                fonts.append(pygame.font.Font(path, font_size))
        return fonts

    def _font_for(self, character: str, big: bool = False) -> pygame.font.Font:
        # everything except the specific characters _NEEDS_FALLBACK_FONT
        # lists uses the main font (or menu_font, for the current
        # question's prompt/choices - see _render_text's `big` argument),
        # same as before any of this existed - covers ascii, the heart
        # symbol, accented letters, all of it
        if character not in _NEEDS_FALLBACK_FONT or not self.fallback_fonts:
            return self.menu_font if big else self.font
        # codepoints under 0x10000 are covered by the first fallback font
        # (assets/unifont-subset.otf) - anything higher needs the second
        # one (assets/unifont-upper-subset.otf), for astral-plane
        # characters like the math-alphabet "J" one puzzle uses. Puzzle
        # text like this never shows up as a menu choice, so there's no
        # bigger version of these two - `big` doesn't apply here
        is_astral = ord(character) >= 0x10000
        if is_astral and len(self.fallback_fonts) > 1:
            return self.fallback_fonts[1]
        return self.fallback_fonts[0]

    def _render_text(self, text: str, color: str, big: bool = False) -> pygame.Surface:
        # renders one line, switching fonts mid-line wherever the current
        # font can't draw the next character - most lines only ever use
        # self.font, so this only costs anything on the unusual ones.
        # `big` renders with menu_font instead - used for the current
        # question's prompt and numbered choices (see _box_lines)
        if not text:
            text = " "

        runs: list[tuple[pygame.font.Font, str]] = []
        current_font = self._font_for(text[0], big)
        current_text = text[0]
        for character in text[1:]:
            font = self._font_for(character, big)
            if font is current_font:
                current_text += character
            else:
                runs.append((current_font, current_text))
                current_font = font
                current_text = character
        runs.append((current_font, current_text))

        foreground = self._render_runs(runs, color)

        # a soft gray shadow sits just behind the real text, offset a
        # couple pixels - keeps every line readable over a busy background
        # image instead of just whatever color the text already was
        shadow = self._render_runs(runs, _TEXT_SHADOW_COLOR)
        shadow.set_alpha(_TEXT_SHADOW_ALPHA)

        combined_width = foreground.get_width() + _TEXT_SHADOW_OFFSET
        combined_height = foreground.get_height() + _TEXT_SHADOW_OFFSET
        combined = pygame.Surface((combined_width, combined_height), pygame.SRCALPHA)
        combined.blit(shadow, (_TEXT_SHADOW_OFFSET, _TEXT_SHADOW_OFFSET))
        combined.blit(foreground, (0, 0))
        return combined

    @staticmethod
    def _render_runs(runs: list[tuple[pygame.font.Font, str]], color) -> pygame.Surface:
        # renders a list of (font, text) runs side by side as one surface -
        # split out of _render_text() so the same run list can be rendered
        # twice: once for the shadow, once for the real text on top of it
        pieces = [font.render(run_text, True, color) for font, run_text in runs]
        if len(pieces) == 1:
            return pieces[0]  # common case - skip building a combined surface
        total_width = sum(piece.get_width() for piece in pieces)
        height = max(piece.get_height() for piece in pieces)
        combined = pygame.Surface((total_width, height), pygame.SRCALPHA)
        x = 0
        for piece in pieces:
            combined.blit(piece, (x, 0))
            x += piece.get_width()
        return combined

    @staticmethod
    def _split_map_grid_and_footer(lines: list[str]) -> tuple[list[str], list[str]]:
        """Split a captured map into its ascii grid and the text under it.

        floor_map.py's render() always puts a genuinely blank line between
        the grid and the legend/status lines under it - and no row of the
        grid itself is ever blank, every one has at least the plan's own
        left/right border on it. So the first blank line marks exactly
        where the grid ends and the small print (the legend, "You are in
        ...", any "not on the plan yet" notice) begins. That footer is
        left untouched by cropping below - it's a couple of short
        sentences, not part of the picture being cropped.
        """
        for index, line in enumerate(lines):
            if not line.strip():
                return lines[:index], lines[index:]
        return lines, []

    @staticmethod
    def _flood_fill_map(sheet: list[list[str]], start: tuple[int, int]) -> set[tuple[int, int]]:
        """Return every square reachable from start without crossing a wall.

        The same flood fill floor_map.py's own _inside() does to find the
        shape of a room to shade it - reimplemented here, on the captured
        text rather than imported (see _MAP_WALL_CHARS), so it can also
        walk the room on the other side of a doorway, which _inside()
        never needs to do.
        """
        seen = {start}
        pending = [start]
        while pending:
            row, col = pending.pop()
            for d_row, d_col in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                spot = (row + d_row, col + d_col)
                if spot in seen or not 0 <= spot[0] < len(sheet):
                    continue
                line = sheet[spot[0]]
                if not 0 <= spot[1] < len(line) or line[spot[1]] in _MAP_WALL_CHARS:
                    continue
                seen.add(spot)
                pending.append(spot)
        return seen

    @staticmethod
    def _doorways_around(
        sheet: list[list[str]], cells: set[tuple[int, int]]
    ) -> set[tuple[int, int]]:
        """Return every doorway ("X") directly touching any square in cells."""
        doorways = set()
        for row, col in cells:
            for d_row, d_col in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                spot_row, spot_col = row + d_row, col + d_col
                if not 0 <= spot_row < len(sheet):
                    continue
                line = sheet[spot_row]
                if 0 <= spot_col < len(line) and line[spot_col] == "X":
                    doorways.add((spot_row, spot_col))
        return doorways

    @staticmethod
    def _room_through_doorway(
        sheet: list[list[str]], doorway: tuple[int, int], home: set[tuple[int, int]]
    ) -> set[tuple[int, int]]:
        """Return the room on the far side of doorway from home.

        Checks every square touching the doorway; whichever is not a wall
        and is not already part of home is the far side, so flood-filling
        from there finds that neighbour room's own shape.
        """
        row, col = doorway
        far_side: set[tuple[int, int]] = set()
        for d_row, d_col in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            spot = (row + d_row, col + d_col)
            if not 0 <= spot[0] < len(sheet):
                continue
            line = sheet[spot[0]]
            if not 0 <= spot[1] < len(line) or line[spot[1]] in _MAP_WALL_CHARS or spot in home:
                continue
            far_side |= TerminalWindow._flood_fill_map(sheet, spot)
        return far_side

    @staticmethod
    def _crop_map_to_local_area(captured: list[str]) -> list[str]:
        """Crop a freshly-captured map down to the current room and its doors.

        floor_map.py already shades the room the player is standing in
        (with _MAP_HERE_CHAR) before this file ever sees the text - this
        finds those shaded squares, flood-fills out through every doorway
        touching them to find whatever room is directly on the other side
        (one hop through a door, not the whole building), and keeps only
        that area. A room with a lot of doors - a corridor, mainly - ends
        up with a bigger crop because it genuinely connects to more of the
        building; that's a real reflection of the map, not a bug in the
        cropping.

        This does NOT just slice out the rectangle of rows/columns that
        bounds the connected area - that was tried first and was wrong.
        The floor plan isn't a grid of independent boxes; corridors are
        long strips, and the bounding rectangle around "your room plus a
        corridor" can span much more of the building than the two of them
        actually occupy, sweeping in whatever unrelated room happens to
        sit in the gap (a real bug a teammate caught: standing near a
        corridor pulled in "Storage" purely because its room happened to
        fall inside that rectangle, with no door or flood-fill path
        connecting it to anything actually included). Instead, every
        character is masked: kept only if it's part of the connected area
        itself, or a wall character immediately touching it (so a room or
        corridor still looks like an intact box, corners included) -
        everything else in the crop's rectangle is blanked out rather than
        shown. A stray doorway on the very edge, leading further away, can
        still peek in - that's honest ("there's a door here") rather than
        a leak of the room behind it, since that room's own letters are
        always more than one cell further out and never get pulled in.

        Falls back to the whole thing, uncropped, if nothing is shaded (the
        current room isn't drawn on the plan at all yet) - better an
        oversized map than a guess at what to show instead.
        """
        grid, footer = TerminalWindow._split_map_grid_and_footer(captured)
        sheet = [list(line) for line in grid]
        here = {
            (row, col)
            for row, line in enumerate(sheet)
            for col, char in enumerate(line)
            if char == _MAP_HERE_CHAR
        }
        if not here:
            return captured

        included = set(here)
        for doorway in TerminalWindow._doorways_around(sheet, here):
            included.add(doorway)
            included |= TerminalWindow._room_through_doorway(sheet, doorway, here)

        # dilate by one cell in every direction (including diagonals, to
        # catch "+" corners) so each included room/corridor's own border
        # survives, without reaching far enough to touch anything that
        # isn't actually connected
        keep = set(included)
        for row, col in included:
            for d_row in (-1, 0, 1):
                for d_col in (-1, 0, 1):
                    spot = (row + d_row, col + d_col)
                    if 0 <= spot[0] < len(sheet) and 0 <= spot[1] < len(sheet[spot[0]]):
                        keep.add(spot)

        rows = [row for row, _ in keep]
        cols = [col for _, col in keep]
        top = max(0, min(rows) - _MAP_CROP_PADDING)
        bottom = min(len(grid) - 1, max(rows) + _MAP_CROP_PADDING)
        left = max(0, min(cols) - _MAP_CROP_PADDING)
        right = max(cols) + _MAP_CROP_PADDING

        cropped_grid = []
        for row in range(top, bottom + 1):
            line = grid[row]
            chars = [
                line[col] if col < len(line) and (row, col) in keep else " "
                for col in range(left, right + 1)
            ]
            cropped_grid.append("".join(chars).rstrip())

        # the padding row above/below usually lands on a wall - but when
        # the nearest connected cell is right at the very edge of the
        # crop, that padding row can land past it, on a row where nothing
        # in this column range was kept at all (masked to nothing but
        # spaces). A fully blank row like that isn't useful margin, it's
        # just noise, so trim it rather than show an empty line before
        # the map even starts.
        while cropped_grid and not cropped_grid[0]:
            cropped_grid.pop(0)
        while cropped_grid and not cropped_grid[-1]:
            cropped_grid.pop()

        return cropped_grid + footer

    def _render_map_line(self, text: str, color: str) -> pygame.Surface:
        # same soft-shadow treatment as _render_text(), just using
        # map_font instead of the main font - the map's lines are plain
        # ascii/box-drawing, so there's no need for _font_for()'s
        # per-character fallback-font switching here
        foreground = self.map_font.render(text, True, color)
        shadow = self.map_font.render(text, True, _TEXT_SHADOW_COLOR)
        shadow.set_alpha(_TEXT_SHADOW_ALPHA)

        combined_width = foreground.get_width() + _TEXT_SHADOW_OFFSET
        combined_height = foreground.get_height() + _TEXT_SHADOW_OFFSET
        combined = pygame.Surface((combined_width, combined_height), pygame.SRCALPHA)
        combined.blit(shadow, (_TEXT_SHADOW_OFFSET, _TEXT_SHADOW_OFFSET))
        combined.blit(foreground, (0, 0))
        return combined

    def _draw_map_overlay(self) -> None:
        # draws the map as its own panel in the corner, like a HUD, instead
        # of mixed into the normal scrolling text
        if self.map_overlay is None:
            return
        # Every row uses the SAME font at the SAME size, on purpose: this
        # is monospaced ascii art, where a wall's "|" has to land in
        # exactly the same column on every row for the boxes to look like
        # boxes at all. A smaller font for some rows was tried here and
        # reverted - a smaller point size is also narrower per character,
        # so those rows' walls drifted out of column with the rows above
        # and below them and the whole map looked broken instead of
        # smaller. Shrinking this panel has to either shrink every row
        # equally (map_font itself) or show fewer rows - never some rows
        # more than others.
        row_height = self.map_font.get_height() + 1
        surfaces = [self._render_map_line(line, "white") for line in self.map_overlay]
        panel_width = max((s.get_width() for s in surfaces), default=0) + self.margin * 2
        panel_height = len(surfaces) * row_height + self.margin * 2

        # a near-opaque tint behind the whole panel - see _MAP_PANEL_ALPHA
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((20, 20, 20, _MAP_PANEL_ALPHA))

        # the border gets the same shadow treatment as the text - a dim
        # offset copy behind a solid line, so it stays visible without
        # needing the panel to be tinted. Khaki (matching the room header
        # text) and a 2px width instead of white/1px, so the panel reads
        # unmistakably as its own HUD element sitting on top of the scene,
        # not just an edge blending into whatever's behind it
        shadow_rect = (_TEXT_SHADOW_OFFSET, _TEXT_SHADOW_OFFSET, panel_width, panel_height)
        pygame.draw.rect(panel, (*_TEXT_SHADOW_COLOR, _TEXT_SHADOW_ALPHA), shadow_rect, 2)
        pygame.draw.rect(panel, "khaki", panel.get_rect(), 2)
        for row, surface in enumerate(surfaces):
            panel.blit(surface, (self.margin, self.margin + row * row_height))

        x = self.width - panel_width - self.margin
        self.screen.blit(panel, (x, self.margin))

    def _box_lines(self) -> list[tuple[str, str, bool]]:
        """What the dialogue box should show right now.

        Only the current "page" (see box_start), never the whole
        scrollback. Every row in the box renders at the same bigger size
        (see _render_text's `big` argument) - narration and the current
        question's prompt/choices alike - only the pinned room header and
        the pre-room intro screen stay at the normal size (see _draw).

        Blank lines are dropped entirely rather than shown as an empty row.
        The game calls ``ui.say()`` with no argument all over commands.py
        and game.py purely to put a blank line between sections in a
        scrolling terminal - that's a real, printed line, so it lands in
        self.lines like any other. In a scrolling terminal a blank line
        just adds a bit of vertical space, harmless. In this box, which
        only ever shows one "page" at a time, that same blank line becomes
        its own full-height row with nothing in it - most visibly when it's
        the very first line of a fresh page (e.g. "Look around" calls
        ui.say() right before narrating the room), where it shows up as a
        big empty gap between the box's top border and the text, for no
        reason a player could ever guess. The box already has its own
        margin and a fresh border every page, so it doesn't need the
        terminal's own spacing convention reproduced inside it.
        """
        shown = [(text, color, True) for text, color in self.lines[self.box_start :] if text != ""]
        if self.waiting_to_advance:
            # the game thread is genuinely blocked right now (see
            # wait_for_line_advance) - nothing more can arrive until the
            # player presses, so just show what's there. current_line may
            # still hold this line's own text for a moment until
            # _pump_output catches up and files it into self.lines - show
            # it too so the line doesn't flicker away for a frame.
            if self.current_line:
                shown.append((self.current_line, "white", True))
            return shown
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        if self.game_over:
            live_text, live_color = self.current_line, "gray"
        else:
            live_text, live_color = self.current_line + self.typed + cursor, "lightgreen"
        shown.append((live_text, live_color, True))
        seconds_left = self._seconds_left()
        if seconds_left is not None:
            shown.append((f"[{seconds_left}s left]", "orange", True))
        return shown

    def _wrap_to_width(self, text: str, big: bool, max_width: int) -> list[str]:
        """Break text into lines that fit max_width at the box's font.

        ui.py's own _wrap() (what actually splits narration into lines in
        the first place) only knows about a fixed column count tuned for a
        full terminal - it has no idea this box exists, let alone how wide
        it is in pixels, or that "big" lines use a bigger font than
        "normal" ones. Without this, a line that DOES fit ui.py's column
        count can still be wider than the box and simply run past its edge.
        """
        font = self.menu_font if big else self.font
        # _render_text() pads its combined surface by _TEXT_SHADOW_OFFSET
        # for the shadow copy, so the actual rendered width is always a
        # little more than font.size() alone reports - budget for that here
        # too, or a line right at the edge could still clip by that much
        budget = max_width - _TEXT_SHADOW_OFFSET
        words = text.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}" if current else word
            if not current or font.size(candidate)[0] <= budget:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _draw_dialogue_box(self) -> None:
        """Draw the little Undertale-style box, lower-center.

        Shows only _box_lines(), same shadowed-panel look as the map overlay.
        """
        max_box_width = int(self.width * _BOX_WIDTH_FRACTION)
        min_box_width = int(self.width * _BOX_MIN_WIDTH_FRACTION)
        # wrap against the MAX width regardless of how wide the box ends up
        # drawn - a long paragraph should still wrap at the same column it
        # always has, not reflow just because a short line elsewhere would
        # let the box shrink
        inner_width = max_box_width - self.margin * 2

        wrapped: list[tuple[str, str, bool]] = []
        for text, color, big in self._box_lines():
            for sub_line in self._wrap_to_width(text, big, inner_width):
                wrapped.append((sub_line, color, big))
        wrapped = wrapped[-_BOX_MAX_ROWS:]

        surfaces = [self._render_text(text, color, big) for text, color, big in wrapped]
        row_heights = [surface.get_height() + 2 for surface in surfaces]
        box_height = sum(row_heights, self.margin * 2)

        # now that we know how wide the actual (already-wrapped) lines are,
        # hug the box to the widest one instead of always drawing it at the
        # max width - clamped so it never gets so narrow a line clips, and
        # never wider than what wrapping was budgeted for above
        content_width = max((surface.get_width() for surface in surfaces), default=0)
        box_width = min(max_box_width, max(min_box_width, content_width + self.margin * 2))

        box = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        box.fill((10, 10, 10, _BOX_PANEL_ALPHA))
        shadow_rect = (_TEXT_SHADOW_OFFSET, _TEXT_SHADOW_OFFSET, box_width, box_height)
        pygame.draw.rect(box, (*_TEXT_SHADOW_COLOR, _TEXT_SHADOW_ALPHA), shadow_rect, 1)
        pygame.draw.rect(box, "white", box.get_rect(), 1)
        y = self.margin
        for surface, row_height in zip(surfaces, row_heights, strict=True):
            box.blit(surface, (self.margin, y))
            y += row_height

        x = (self.width - box_width) // 2
        y = self.height - box_height - self.margin * 3
        self.screen.blit(box, (x, y))

    def _draw_intro(self) -> None:
        """Draw the very first screen, before the player has entered any room.

        self.room_header is still None here - this is the same full-screen,
        centered, top-to-bottom layout every line used before the dialogue box
        existed. The name prompt and the intro blurb aren't dialogue inside
        a room, so they don't belong crammed in the little box - this is
        "where it originally was". Pacing (typed lines still needing a
        press) is unchanged; only where it's drawn is different.
        """
        top = self.margin
        visible_rows = max(1, (self.height - top - self.margin) // self.line_height - 1)
        for row, (line, color) in enumerate(self.lines[-visible_rows:]):
            surface = self._render_text(line, color)
            self.screen.blit(surface, (self._centered_x(surface), top + row * self.line_height))

        y = top + min(len(self.lines), visible_rows) * self.line_height
        if self.waiting_to_advance:
            # game thread is blocked - current_line may still hold this
            # line's own text for a moment until _pump_output catches up
            # and files it into self.lines; show it so it doesn't flicker
            # away for a frame, just without a live cursor
            if self.current_line:
                surface = self._render_text(self.current_line, "white")
                self.screen.blit(surface, (self._centered_x(surface), y))
            return
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        live_text = self.current_line if self.game_over else self.current_line + self.typed + cursor
        live_color = "gray" if self.game_over else "lightgreen"
        surface = self._render_text(live_text, live_color)
        self.screen.blit(surface, (self._centered_x(surface), y))

    def _draw(self) -> None:
        """Redraw the whole window from scratch - Pygame has no "update just this line"."""
        self.screen.fill("black")
        if self.room_image is not None:
            self.screen.blit(self.room_image, (0, 0))

        if self.room_header is None:
            # before the first room - see _draw_intro
            self._draw_intro()
        else:
            surface = self._render_text(self.room_header, "khaki")
            self.screen.blit(surface, (self._centered_x(surface), self.margin))
            self._draw_dialogue_box()

        self._draw_map_overlay()

        pygame.display.flip()  # nothing is visible until this swaps the frame onto the screen

    # after quitting, wait this long for the game to save and say goodbye
    QUIT_GRACE_PERIOD = 5.0

    def run(self) -> None:
        """The main loop: read input, pull in new text, draw - 60 times a second."""
        self.start_game_thread()
        clock = pygame.time.Clock()
        while True:
            self._handle_events()
            self._check_clock()
            self._pump_output()
            self._draw()
            if self.quitting and (
                self.game_over
                or time.monotonic() - self._quit_requested_at > self.QUIT_GRACE_PERIOD
            ):
                break
            clock.tick(FPS)  # caps the loop at 60fps instead of spinning as fast as possible
        # one more pass so the game's very last message doesn't get cut off
        self._pump_output()
        self._draw()
        pygame.quit()


if __name__ == "__main__":
    TerminalWindow().run()  # only runs the window if this file is executed directly
