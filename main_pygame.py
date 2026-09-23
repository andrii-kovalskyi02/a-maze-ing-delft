"""Runs the real console game inside a Pygame window that acts like a terminal.

We used to reimplement say()/narrate()/ask()/choose() for Pygame, but that
broke every time ui.py changed. This version runs your actual main.py
unchanged in a background thread, and only fakes stdout/stdin so the game
never knows it's not a real terminal.

Run it with:

    python main_pygame.py

Type + Enter like a normal console. Any key skips typing/pauses. Escape
quits.

Quick map of the file:
    _StreamToQueue / _QueueToStream  -> the fake stdout/stdin
    _make_skippable_sleep            -> lets a keypress skip a wait
    TerminalWindow.__init__          -> all the state the window tracks
    TerminalWindow.start_game_thread -> wires the fakes in, starts the game
    TerminalWindow._pump_output      -> turns printed text into screen lines
    TerminalWindow._handle_events    -> turns keypresses into typed answers
    TerminalWindow._draw             -> draws everything each frame
    TerminalWindow._draw_map_overlay -> draws the map in its own corner panel
    TerminalWindow.run               -> the main loop tying it all together
"""

from __future__ import annotations

import ctypes
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

# tells the game "stop waiting" - input() turns this into EOFError on its own
_EOF = object()

FPS = 60

# fonts with glyphs for the unusual Unicode some puzzle text uses - consolas
# alone can't draw these, so they live next to this file as small files
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_FALLBACK_FONT_FILES = ["unifont-subset.otf", "unifont-upper-subset.otf"]

# the exact characters rooms/classroom_2031.py's last puzzle question uses
# (Canadian syllabics, box-drawing, math symbols, ...) that consolas has no
# glyph for - everything else (ascii, the heart symbol, accented letters
# elsewhere in the game) keeps using consolas as normal. This has to be an
# exact list rather than asking pygame "can you draw this character" at
# runtime: that check (Font.metrics()) turned out to report a character as
# drawable even when the installed font can't actually draw it, so it
# can't be trusted to decide this. Add a room with similarly unusual
# Unicode later? Add its non-ascii characters here too.
_NEEDS_FALLBACK_FONT = set("ᒲᒷᓭᔑ↸∷⊣⋮⍊⍑⎓╎⚍リꖎ𝙹")

# set AMAZE_PYGAME_DEBUG=1 to print every fake-stdout write to the real terminal
_DEBUG = os.environ.get("AMAZE_PYGAME_DEBUG") == "1"
_debug_start = time.monotonic()


def _debug_log(message: str) -> None:
    if _DEBUG:
        print(f"[{time.monotonic() - _debug_start:7.3f}s] {message}", file=sys.stderr, flush=True)


class _StreamToQueue:
    """Fake sys.stdout - catches what the game prints and queues it for the window."""

    def __init__(self, out_queue: queue.Queue[str]) -> None:
        self._queue = out_queue

    def write(self, text: str) -> None:
        # this is the whole trick: print()/say()/narrate() call write(), and it
        # lands here instead of a real screen
        if text:
            _debug_log(f"stdout.write() len={len(text)} text={text!r}")
            self._queue.put(text)

    def flush(self) -> None:
        pass  # nothing to flush, queue.put() already delivers instantly

    def isatty(self) -> bool:
        # fixes bug where narrate() types instantly instead of one character at a time
        return True


class _QueueToStream:
    """Fake sys.stdin - input() blocks here until the player types something."""

    def __init__(self, in_queue: queue.Queue[object], on_wait_start, on_wait_end) -> None:
        self._queue = in_queue
        self._on_wait_start = on_wait_start
        self._on_wait_end = on_wait_end

    def readline(self) -> str:
        self._on_wait_start()
        try:
            line = self._queue.get()
        finally:
            self._on_wait_end()
        if line is _EOF:
            return ""  # empty string = EOF, same as a real terminal
        return f"{line}\n"

    def isatty(self) -> bool:
        # fixes the same narrate() bug as above - ui.py checks BOTH stdout and stdin
        return True

    def fileno(self) -> int:
        # no real file behind this, so raise like a closed/fake stream would - not a crash
        raise OSError("this is not a real terminal - no file descriptor")


def _make_skippable_sleep(skip_event: threading.Event):
    """Swaps in for time.sleep() - returns early if the player pressed a key to skip.

    Passed into ui.use_io() as the sleep argument - the one official hook
    the game already has for this, so nothing in ui.py gets touched.
    """

    def _sleep(seconds: float) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if skip_event.is_set():
                return
            time.sleep(0.01)  # check often so a keypress feels instant

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
        self.font = pygame.font.SysFont("consolas", font_size)
        # some puzzle text uses unusual Unicode (Canadian syllabics, math
        # symbols, ...) consolas has no glyphs for - these bundled fonts
        # cover that, and _render_text() below picks whichever one actually
        # has each character instead of drawing a blank box for it
        self.fallback_fonts = self._load_fallback_fonts(font_size)
        # smaller than the main text, so it reads as a HUD panel rather
        # than taking over the screen, but not so small it turns blurry
        self.map_font = pygame.font.SysFont("consolas", max(11, int(font_size * 0.75)))
        self.line_height = font_size + 4
        self.margin = 10

        self.lines: list[tuple[str, str]] = []  # (text, color) for every finished line
        self.current_line = ""  # the line being built right now, character by character
        self.typed = ""  # what the player has typed for their current answer

        # the pinned "== Room Name ==" line, kept separate so it never scrolls away
        self.room_header: str | None = None

        # the last "Look at the evacuation plan" output, drawn in its own
        # corner panel instead of the normal scrollback - see _pump_output
        self.map_overlay: list[str] | None = None
        self._capturing_map = False
        self._map_capture_buffer: list[str] = []

        self.game_over = False
        self._quit_requested = False
        self._quit_requested_at = 0.0

        # True only while the game is blocked waiting on an answer, not while narrating
        self.waiting_for_input = False

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
        self.skip_event = threading.Event()

    def _wait_start(self) -> None:
        self.waiting_for_input = True
        self._prompt_pending = True

    def _wait_end(self) -> None:
        self.waiting_for_input = False

    def start_game_thread(self) -> None:
        """Wire the fake stdout/stdin in, then start the real game in the background."""
        sys.stdout = _StreamToQueue(self.out_queue)
        sys.stdin = _QueueToStream(self.in_queue, self._wait_start, self._wait_end)

        # the only place this file changes game behaviour - lets a keypress skip a wait
        ui.use_io(write=print, read=input, sleep=_make_skippable_sleep(self.skip_event))

        _debug_log(
            "after use_io(): "
            f"ui._write is print = {getattr(ui, '_write', None) is print}, "
            f"sys.stdout.isatty() = {sys.stdout.isatty()}, "
            f"ui.CHAR_DELAY = {getattr(ui, 'CHAR_DELAY', 'MISSING')}"
        )

        # reset the skip flag each new question, so skipping one line doesn't skip the next
        real_ask = ui.ask

        def ask_and_reset_skip(prompt: str = "> ") -> str:
            self.skip_event.clear()
            return real_ask(prompt)

        ui.ask = ask_and_reset_skip

        thread = threading.Thread(target=self._run_game, daemon=True)
        thread.start()

    def _run_game(self) -> None:
        try:
            run_console_game()
        except EOFError:
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
        """Read whatever the game has printed since last frame, turn it into screen lines."""
        try:
            while True:
                chunk = self.out_queue.get_nowait()
                for character in chunk:
                    if character == "\n":
                        if self._capturing_map:
                            self._map_capture_buffer.append(self.current_line)
                            if self._is_map_last_line(self.current_line):
                                # the whole map arrived - show it in its own
                                # corner instead of the normal scrollback
                                self.map_overlay = list(self._map_capture_buffer)
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
                            self.lines = []
                            self.map_overlay = None
                            self._prompt_start = None
                            self._last_blank_index = None
                        else:
                            self.lines.append((self.current_line, "white"))
                            if self.current_line == "":
                                self._last_blank_index = len(self.lines) - 1
                        self.current_line = ""
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
                if not self.waiting_for_input:
                    # game is busy narrating, not asking anything - just skip, don't type
                    self.skip_event.set()
                    continue
                if event.key == pygame.K_RETURN:
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
                    self.in_queue.put(self.typed)
                    self.typed = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.typed = self.typed[:-1]
                elif event.unicode and event.unicode.isprintable():
                    self.typed += event.unicode

    def _quit(self) -> None:
        if self._quit_requested:
            return  # don't push _EOF twice if Escape gets pressed more than once
        self._quit_requested = True
        self._quit_requested_at = time.monotonic()
        self.in_queue.put(_EOF)

    def _centered_x(self, surface: pygame.Surface) -> int:
        # centers text horizontally, never further left than the margin
        return max(self.margin, (self.width - surface.get_width()) // 2)

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

    def _font_for(self, character: str) -> pygame.font.Font:
        # everything except the specific characters _NEEDS_FALLBACK_FONT
        # lists uses the main font, same as before any of this existed -
        # covers ascii, the heart symbol, accented letters, all of it
        if character not in _NEEDS_FALLBACK_FONT or not self.fallback_fonts:
            return self.font
        # codepoints under 0x10000 are covered by the first fallback font
        # (assets/unifont-subset.otf) - anything higher needs the second
        # one (assets/unifont-upper-subset.otf), for astral-plane
        # characters like the math-alphabet "J" one puzzle uses
        is_astral = ord(character) >= 0x10000
        if is_astral and len(self.fallback_fonts) > 1:
            return self.fallback_fonts[1]
        return self.fallback_fonts[0]

    def _render_text(self, text: str, color: str) -> pygame.Surface:
        # renders one line, switching fonts mid-line wherever the current
        # font can't draw the next character - most lines only ever use
        # self.font, so this only costs anything on the unusual ones
        if not text:
            return self.font.render(" ", True, color)

        runs: list[tuple[pygame.font.Font, str]] = []
        current_font = self._font_for(text[0])
        current_text = text[0]
        for character in text[1:]:
            font = self._font_for(character)
            if font is current_font:
                current_text += character
            else:
                runs.append((current_font, current_text))
                current_font = font
                current_text = character
        runs.append((current_font, current_text))

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

    def _draw_map_overlay(self) -> None:
        # draws the map as its own panel in the corner, like a HUD, instead
        # of mixed into the normal scrolling text
        if self.map_overlay is None:
            return
        row_height = self.map_font.get_height() + 2
        surfaces = [self.map_font.render(line, True, "khaki") for line in self.map_overlay]
        panel_width = max((s.get_width() for s in surfaces), default=0) + self.margin * 2
        panel_height = len(surfaces) * row_height + self.margin * 2

        panel = pygame.Surface((panel_width, panel_height))
        panel.fill((20, 20, 20))
        pygame.draw.rect(panel, "khaki", panel.get_rect(), 1)
        for row, surface in enumerate(surfaces):
            panel.blit(surface, (self.margin, self.margin + row * row_height))

        x = self.width - panel_width - self.margin
        self.screen.blit(panel, (x, self.margin))

    def _draw(self) -> None:
        """Redraw the whole window from scratch - Pygame has no "update just this line"."""
        self.screen.fill("black")

        top = self.margin
        if self.room_header is not None:
            surface = self._render_text(self.room_header, "khaki")
            self.screen.blit(surface, (self._centered_x(surface), top))
            top += self.line_height * 2

        # only draw as many lines as actually fit - the rest scrolls off, like a real terminal
        visible_rows = max(1, (self.height - top - self.margin) // self.line_height - 1)
        for row, (line, color) in enumerate(self.lines[-visible_rows:]):
            surface = self._render_text(line, color)
            self.screen.blit(surface, (self._centered_x(surface), top + row * self.line_height))

        # blinking cursor - on for half a second, off for half a second
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        live_text = self.current_line if self.game_over else self.current_line + self.typed + cursor
        live_color = "gray" if self.game_over else "lightgreen"
        y = top + min(len(self.lines), visible_rows) * self.line_height
        surface = self._render_text(live_text, live_color)
        self.screen.blit(surface, (self._centered_x(surface), y))

        self._draw_map_overlay()

        pygame.display.flip()  # nothing is visible until this swaps the frame onto the screen

    # after quitting, wait this long for the game's own "goodbye" message
    QUIT_GRACE_PERIOD = 1.0

    def run(self) -> None:
        """The main loop: read input, pull in new text, draw - 60 times a second."""
        self.start_game_thread()
        clock = pygame.time.Clock()
        while True:
            self._handle_events()
            self._pump_output()
            self._draw()
            if self._quit_requested and (
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