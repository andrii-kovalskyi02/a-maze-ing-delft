"""The pause menu (Escape): it stops the game behind a blurred freeze-frame of it.

It has a few screens of its own (``view``): the menu itself, the leaderboard, the controls, "Are
you sure you want to quit?", and the floor map, which is shown the same way.
"""

from __future__ import annotations

import time
import traceback
from typing import TYPE_CHECKING

import pygame

import progress
import ui
from leaderboard import scoreboard
from pygame_ui import assets
from pygame_ui.text import HEART, ICON_COLOR, SKULL, load_heart_font

if TYPE_CHECKING:
    from pygame_ui.window import TerminalWindow

BLUR_RADIUS = 14  # at the reference screen height - scaled to the real one
DIM_ALPHA = 130  # how much the frozen scene is darkened: 0 = not at all, 255 = black
ACCENT = (240, 200, 80)  # the word PAUSED

# what the Controls screen lists: (the keys, what they do). The keys are drawn in khaki
CONTROLS = [
    ("Up / Down  or  W / S", "choose from a menu or a question"),
    ("1, 2, 3 ...", "pick that choice by its number"),
    ("Enter", "confirm your choice, or send what you typed"),
    ("Space", "skip the story text, or go on once it has been told"),
    ("M", "open the floor map, once you have taken the plan from the wall"),
    ("Esc", "open the pause menu, and close it again"),
    ("Type + Enter", "answer a question in your own words"),
    ("Backspace", "take back a letter"),
]
CONTROLS_KEY_COLOR = "khaki"

QUIT_ITEMS = ["Quit the game", "Keep playing"]  # the answers to "Are you sure you want to quit?"
QUIT_ITEM = 8  # where "Quit the game" is on the menu itself

# the cog in the top left corner that says "press Esc", a bit smaller than the map's icon
ICON_FILE = "settings_icon.png"
ICON_HEIGHT = 0.065

_ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
_UP = (pygame.K_UP, pygame.K_w)
_DOWN = (pygame.K_DOWN, pygame.K_s)


def blurred(surface: pygame.Surface, scale: float) -> pygame.Surface:
    """A blurred, dimmed copy of ``surface``: the frozen game behind the menu."""
    radius = max(3, round(BLUR_RADIUS * scale))
    size = surface.get_size()
    # blur a quarter-size copy: four times quicker, and a blur hides the lost detail anyway
    small = pygame.transform.smoothscale(surface, (max(1, size[0] // 4), max(1, size[1] // 4)))
    gaussian_blur = getattr(pygame.transform, "gaussian_blur", None)
    if gaussian_blur is not None:  # pygame-ce, which run_game.bat installs
        small = gaussian_blur(small, max(1, radius // 4))
    else:
        # plain pygame has no blur - shrinking further and growing back smears alike
        tiny = pygame.transform.smoothscale(
            small, (max(1, small.get_width() // 4), max(1, small.get_height() // 4))
        )
        small = pygame.transform.smoothscale(tiny, small.get_size())
    backdrop = pygame.transform.smoothscale(small, size)
    dim = pygame.Surface(size, pygame.SRCALPHA)
    dim.fill((0, 0, 0, DIM_ALPHA))
    backdrop.blit(dim, (0, 0))
    return backdrop


class PauseMenu:
    """What the pause menu shows, and what its keys do."""

    def __init__(self, window: TerminalWindow) -> None:
        """Load the menu's own fonts and its cog icon."""
        self.window = window
        size = window.text.size
        self.title_font = window.text.font_at(max(12, round(size * 2.6)))
        # the hearts on the menu are drawn much bigger than the text around them
        self.hearts_size = max(12, round(size * 3.0))
        self.hearts_font = load_heart_font(self.hearts_size)
        self.hearts_text_font = window.text.font_at(self.hearts_size)
        self.icon_art = assets.load_picture(ICON_FILE)
        self._icon: pygame.Surface | None = None

        self.view = "menu"  # "menu", "scoreboard", "controls", "quit" or "map"
        self.selected = 0
        self.status: dict = {}  # how the player is doing, taken once as the menu opens
        self.backdrop: pygame.Surface | None = None
        self.scores: list[str] = []
        self._scores_read_at = 0.0
        self.notice = ""  # a short message such as "Game saved.", until _notice_until
        self._notice_until = 0.0

    def open(self, backdrop: pygame.Surface, view: str = "menu") -> None:
        """Show the menu (or ``view``) over ``backdrop``, with how the player is doing right now."""
        self.status = ui.status() or {}
        self.backdrop = backdrop
        self.selected = 0
        self.view = view

    def items(self) -> list[str]:
        """The labels on the menu, in order."""
        return [
            "Resume",
            "Leaderboard",
            "Controls",
            f"Story text: {ui.text_speed().lower()}",
            f"Music: {self.window.music.level_name.lower()}",
            f"Menu sound: {self.window.tick.level_name.lower()}",
            "Save and continue",
            "Save and quit",
            "Quit the game",
        ]

    def key(self, event: pygame.event.Event) -> None:
        """Handle a key press while the menu is open."""
        if self.view == "map":
            if event.key in (pygame.K_ESCAPE, pygame.K_m, pygame.K_BACKSPACE, *_ENTER):
                self.window.close_pause_menu()
        elif self.view in ("scoreboard", "controls"):
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_BACKSPACE):
                self.view = "menu"
        elif self.view == "quit":
            self._quit_key(event)
        else:
            self._menu_key(event)

    def _menu_key(self, event: pygame.event.Event) -> None:
        count = len(self.items())
        if event.key == pygame.K_ESCAPE:
            self.window.close_pause_menu()
        elif event.key in _UP:
            self.selected = (self.selected - 1) % count
            self.window.tick.play()
        elif event.key in _DOWN:
            self.selected = (self.selected + 1) % count
            self.window.tick.play()
        elif event.key in _ENTER:
            self._choose(self.selected)
        elif event.unicode.isdigit() and 1 <= int(event.unicode) <= count:
            self._choose(int(event.unicode) - 1)

    def _choose(self, index: int) -> None:
        """Do what the menu's item number ``index`` says."""
        window = self.window
        if index == 0:
            window.close_pause_menu()
        elif index == 1:
            self.scores = scoreboard.lines()
            self.view = "scoreboard"
        elif index == 2:
            self.view = "controls"
        elif index == 3:
            ui.cycle_text_speed()  # slow, normal, fast, instant, and round again
        elif index == 4:
            window.music.cycle_level()  # off, low, normal, and round again
        elif index == 5:
            window.tick.cycle_level()
        elif index == 6:
            window.settle_pause_clock()  # so the saved time played leaves out this pause
            try:
                saved = ui.save_game()
            except Exception:  # a locked or missing database must not take the game down
                traceback.print_exc()
                self.notice = "Could not save the game."
            else:
                self.notice = "Game saved." if saved else "There is nothing to save yet."
            self._notice_until = time.monotonic() + 3.0
        elif index == 7:
            window.quit()  # saves and ends the game, the same as closing the window
        elif index == QUIT_ITEM:
            self.view = "quit"
            self.selected = 1  # "Keep playing" to start with

    def _quit_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self._quit_choose(1)  # backing out is the same as keeping on playing
        elif event.key in (*_UP, *_DOWN):
            self.selected = 1 - self.selected
            self.window.tick.play()
        elif event.key in _ENTER:
            self._quit_choose(self.selected)
        elif event.unicode in ("1", "2"):
            self._quit_choose(int(event.unicode) - 1)

    def _quit_choose(self, index: int) -> None:
        if index == 0:
            self.window.quit(save=False)  # stop at once, saving nothing, and close the window
        else:
            self.view = "menu"
            self.selected = QUIT_ITEM

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the menu over the frozen game, with how the player is doing round the edges."""
        window = self.window
        text = window.text
        width, height = screen.get_size()
        if self.backdrop is not None:
            screen.blit(self.backdrop, (0, 0))
        else:
            screen.fill("black")
        if self.view == "map":
            window.floor_map.draw(screen, text, self.status, window.margin)
            return

        status = self.status
        corner = window.margin * 4
        screen.blit(self._render_hearts(str(status.get("hearts", ""))), (corner, corner))
        seconds = progress.format_duration(float(status.get("seconds", 0)))
        played = text.render(f"Time played  {seconds}", "white", True)
        screen.blit(played, (width - corner - played.get_width(), corner))
        explored = text.render(f"{status.get('percent', 0)}% of the floor explored", "white", True)
        screen.blit(
            explored,
            ((width - explored.get_width()) // 2, height - corner - explored.get_height()),
        )

        title = self.title_font.render("PAUSED", True, ACCENT)
        y = height // 8
        screen.blit(title, ((width - title.get_width()) // 2, y))
        y += title.get_height() + window.margin
        name = text.render(str(status.get("name", "")), "gray", True)
        screen.blit(name, ((width - name.get_width()) // 2, y))

        rows, hint = self._rows()
        y = int(height * 0.36)
        for row in rows:
            screen.blit(row, ((width - row.get_width()) // 2, y))
            y += int(row.get_height() * 1.6)
        hint_row = text.render(hint, "gray")
        screen.blit(hint_row, ((width - hint_row.get_width()) // 2, y + window.margin * 2))
        if self.notice and time.monotonic() < self._notice_until:
            note = text.render(self.notice, "khaki", True)
            screen.blit(note, ((width - note.get_width()) // 2, y + window.margin * 5))

    def _rows(self) -> tuple[list[pygame.Surface], str]:
        """The rows in the middle of the screen for the current view, and the hint under them."""
        text = self.window.text
        if self.view == "scoreboard":
            if time.monotonic() - self._scores_read_at > 1.0:  # the shared list comes later
                self.scores = scoreboard.lines()
                self._scores_read_at = time.monotonic()
            return [text.render(line, "white", True) for line in self.scores], "Esc or Enter: back"
        if self.view == "controls":
            return [self._controls_row(keys, what) for keys, what in CONTROLS], "Esc or Enter: back"
        if self.view == "quit":
            rows = [
                text.render("Are you sure you want to quit?", "white", True),
                text.render("Any progress from this run will be lost.", "gray", True),
                text.render("", "white", True),
                *self._choices(QUIT_ITEMS),
            ]
            return rows, "Up / Down and Enter, or Esc to keep playing"
        return self._choices(self.items()), "Up / Down and Enter, or Esc to resume"

    def _choices(self, labels: list[str]) -> list[pygame.Surface]:
        """A column of choices, the selected one in khaki with "> <" round it."""
        return [
            self.window.text.render(f"> {label} <", "khaki", True)
            if number == self.selected
            else self.window.text.render(f"  {label}  ", "white", True)
            for number, label in enumerate(labels)
        ]

    def _controls_row(self, keys: str, what: str) -> pygame.Surface:
        """One line of the Controls screen: the keys in khaki, then what they do in white."""
        left = self.window.text.render(keys, CONTROLS_KEY_COLOR, True)
        right = self.window.text.render(f"  -  {what}", "white", True)
        row = pygame.Surface(
            (left.get_width() + right.get_width(), left.get_height()), pygame.SRCALPHA
        )
        row.blit(left, (0, 0))
        row.blit(right, (left.get_width(), 0))
        return row

    def _render_hearts(self, hearts: str) -> pygame.Surface:
        """The "Hearts: ..." row of the menu, with the hearts big and red."""
        text = self.window.text
        icon_font, bracket_font = self.hearts_font, self.hearts_text_font
        if icon_font is None:  # no heart font: the normal row
            return text.render(f"Hearts: {hearts}", "white", True)
        label = text.render("Hearts:", "white", True)
        pieces = []
        for character in hearts.replace("·", SKULL):  # an empty heart is a skull
            icon = character in (HEART, SKULL)
            font = icon_font if icon else bracket_font
            pieces.append(font.render(character, True, ICON_COLOR if icon else (245, 245, 245)))
        gap = text.menu_font.size(" ")[0]
        surface = pygame.Surface(
            (label.get_width() + gap + sum(p.get_width() for p in pieces), icon_font.get_height()),
            pygame.SRCALPHA,
        )
        # the small label is centred on the hearts: the middle of its capital letters level
        # with the middle of a heart (a heart is drawn from 90 to 610 units above the line,
        # so its middle is 350 up, and a capital of this font is about 956 tall)
        heart_middle = icon_font.get_ascent() - 0.35 * self.hearts_size
        label_baseline = heart_middle + 0.5 * 0.956 * text.menu_font.get_height() / 1.32
        surface.blit(label, (0, round(label_baseline - text.menu_font.get_ascent())))
        x = label.get_width() + gap
        for piece in pieces:
            surface.blit(piece, (x, 0))
            x += piece.get_width()
        return surface

    def draw_hint(self, screen: pygame.Surface) -> None:
        """Draw the cog over "ESC" in the top left corner, to say the menu is there."""
        if self.icon_art is None:
            return
        if self._icon is None:
            height = max(8, round(screen.get_height() * ICON_HEIGHT))
            width = max(8, round(self.icon_art.get_width() * height / self.icon_art.get_height()))
            self._icon = pygame.transform.smoothscale(self.icon_art, (width, height))
        key = self.window.text.render("ESC", "white", True)
        icon = self._icon
        margin = self.window.margin
        column = max(icon.get_width(), key.get_width())
        left = top = margin * 2
        screen.blit(icon, (left + (column - icon.get_width()) // 2, top))
        screen.blit(
            key, (left + (column - key.get_width()) // 2, top + icon.get_height() + margin // 2)
        )
