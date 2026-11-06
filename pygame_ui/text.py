"""Fonts, and drawing one line of text the way every line in the window looks."""

from __future__ import annotations

import os

import pygame

from pygame_ui import assets

# the main font is bundled as a file rather than asked for by name: pygame.font.SysFont("consolas")
# quietly used a different font on every Mac and Linux machine. Our handwriting is a copy of
# JetBrains Mono with the 52 letters redrawn, so if it is ever missing the plain one is used
MAIN_FONT_FILE = "AmazeHand-Regular.ttf"
BACKUP_FONT_FILE = "JetBrainsMono-Regular.ttf"

# fonts for the unusual Unicode the classroom_2031 puzzle uses, which the main font cannot draw:
# the first covers code points under 0x10000, the second the ones above
FALLBACK_FONT_FILES = ["unifont-subset.otf", "unifont-upper-subset.otf"]

# the exact characters that need a fallback font. It has to be a list: asking pygame "can you
# draw this?" (Font.metrics) says yes even when the font cannot. Add a room with similarly
# unusual Unicode? Add its characters here too
NEEDS_FALLBACK_FONT = set("ᒲᒷᓭᔑ↸∷⊣⋮⍊⍑⎓╎⚍リꖎ𝙹")

# the heart in "Hearts: ♥♥♥" (health.py), and a skull for an empty heart in its place (the game
# prints a dot): the main font has neither, so they have a tiny font of their own, built to its
# size and spacing. The skull sits on a private-use code point nothing else uses
HEART = "♥"
SKULL = ""
HEART_FONT_FILE = "heart.otf"
ICON_COLOR = (235, 45, 45)  # both icons are red, whatever colour the text around them is

# every line gets a soft shadow behind it, so it stays readable over a room's picture
SHADOW_COLOR = (40, 40, 40)
SHADOW_OFFSET = 1  # pixels, down and to the right
SHADOW_ALPHA = 190  # 0 = invisible, 255 = fully solid

# "big" text (everything in the dialogue box) is this many times the normal size
BIG_FACTOR = 1.35


def load_main_font(size: int) -> pygame.font.Font:
    """The game's own font at ``size``, or a system font if the files are missing."""
    for filename in (MAIN_FONT_FILE, BACKUP_FONT_FILE):
        path = assets.path(filename)
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("consolas", size)  # assets missing - better than crashing


def load_heart_font(size: int) -> pygame.font.Font | None:
    """The heart and skull font at ``size``, or None (they then draw as boxes)."""
    path = assets.path(HEART_FONT_FILE)
    return pygame.font.Font(path, size) if os.path.exists(path) else None


def _load_fallback_fonts(size: int) -> list[pygame.font.Font]:
    return [
        pygame.font.Font(assets.path(filename), size)
        for filename in FALLBACK_FONT_FILES
        if os.path.exists(assets.path(filename))
    ]


class TextRenderer:
    """Every font the window uses, at sizes that suit the screen, and how to draw with them."""

    def __init__(self, size: int) -> None:
        """Load the fonts for text that is ``size`` pixels high."""
        self.size = size
        self.font = load_main_font(size)
        # bigger: everything in the dialogue box, so it stands out from the room's name
        self.menu_font = load_main_font(int(size * BIG_FACTOR))
        self.fallback_fonts = _load_fallback_fonts(size)
        self.heart_font = load_heart_font(size)
        self.heart_menu_font = load_heart_font(int(size * BIG_FACTOR))
        self._sized: dict[int, pygame.font.Font] = {}

    def font_at(self, size: int) -> pygame.font.Font:
        """The main font at any ``size``, loaded once and kept."""
        if size not in self._sized:
            self._sized[size] = load_main_font(size)
        return self._sized[size]

    def render(self, text: str, color, big: bool = False) -> pygame.Surface:
        """Draw one line, with its shadow, switching fonts for characters the main one lacks."""
        if not text:
            text = " "
        if text.startswith("Hearts:"):
            text = text.replace("·", SKULL)  # an empty heart is drawn as a skull

        # split the line into runs of characters that share a font
        runs: list[tuple[pygame.font.Font, str]] = []
        for character in text:
            font = self._font_for(character, big)
            if runs and runs[-1][0] is font:
                runs[-1] = (font, runs[-1][1] + character)
            else:
                runs.append((font, character))

        foreground = self._render_runs(runs, color, tint_icons=True)
        shadow = self._render_runs(runs, SHADOW_COLOR)
        shadow.set_alpha(SHADOW_ALPHA)
        combined = pygame.Surface(
            (foreground.get_width() + SHADOW_OFFSET, foreground.get_height() + SHADOW_OFFSET),
            pygame.SRCALPHA,
        )
        combined.blit(shadow, (SHADOW_OFFSET, SHADOW_OFFSET))
        combined.blit(foreground, (0, 0))
        return combined

    def wrap(self, text: str, big: bool, max_width: int) -> list[str]:
        """Break ``text`` into lines that fit ``max_width`` pixels.

        ui.py's own wrapping counts characters for a terminal and knows nothing of pixels, so
        without this a line could still run past the edge of the box.
        """
        font = self.menu_font if big else self.font
        budget = max_width - SHADOW_OFFSET  # render() makes every line this much wider
        lines: list[str] = []
        current = ""
        for word in text.split(" "):
            candidate = f"{current} {word}" if current else word
            if not current or font.size(candidate)[0] <= budget:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _font_for(self, character: str, big: bool) -> pygame.font.Font:
        if character in (HEART, SKULL) and self.heart_font is not None:
            return self.heart_menu_font if big else self.heart_font
        if character not in NEEDS_FALLBACK_FONT or not self.fallback_fonts:
            return self.menu_font if big else self.font
        # puzzle text never shows up as a menu choice, so the fallbacks have no big version
        if ord(character) >= 0x10000 and len(self.fallback_fonts) > 1:
            return self.fallback_fonts[1]
        return self.fallback_fonts[0]

    def _render_runs(
        self, runs: list[tuple[pygame.font.Font, str]], color, tint_icons: bool = False
    ) -> pygame.Surface:
        icon_fonts = (self.heart_font, self.heart_menu_font)
        pieces = [
            font.render(run_text, True, ICON_COLOR if tint_icons and font in icon_fonts else color)
            for font, run_text in runs
        ]
        if len(pieces) == 1:
            return pieces[0]
        combined = pygame.Surface(
            (sum(piece.get_width() for piece in pieces), max(p.get_height() for p in pieces)),
            pygame.SRCALPHA,
        )
        x = 0
        for piece in pieces:
            combined.blit(piece, (x, 0))
            x += piece.get_width()
        return combined
