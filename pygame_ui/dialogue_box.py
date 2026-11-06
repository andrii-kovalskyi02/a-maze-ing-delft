"""The Undertale-style dialogue box: a hand-drawn speech bubble, lower-centre, with the story in it.

The window decides which rows to show (see TerminalWindow.box_rows); this file only lays them out
and draws them. A row is (text, colour, big). Instead of a real colour, a row can be marked with
one of the names below: a menu choice, or the name of whoever is speaking.
"""

from __future__ import annotations

import pygame

from pygame_ui import assets
from pygame_ui.text import TextRenderer

# a menu's choices are drawn in a column of their own, the chosen one in khaki with "> <" round
# it. Just confirmed (Enter, or its number), it "clicks": orange, and pressed in a little
OPTION = "option"
OPTION_SELECTED = "option_selected"
OPTION_PRESSED = "option_pressed"
OPTION_COLORS = {OPTION: "white", OPTION_SELECTED: "khaki", OPTION_PRESSED: "orange"}
SPEAKER_LABEL = "speaker_label"
SPEAKER_LABEL_COLOR = "khaki"

# the two hand-drawn frames: the chat box (a speech bubble with a tail) is the dialogue box, and
# the text box (two square brackets) frames the little "SPACE to skip" tag on it. Each is cut into
# 3 columns by 3 rows, so it can be stretched to any size without thinning its lines: the corners
# keep their size and only the parts in between are stretched. The cuts are pixel positions
TEXT_BOX_FILE = "text_box.png"  # 682 x 327
TEXT_BOX_CUTS = ((0, 211, 463, 682), (0, 30, 297, 327))
CHAT_BOX_FILE = "chat_box.png"  # 472 x 405
CHAT_BOX_CUTS = ((0, 40, 300, 472), (0, 30, 270, 405))  # the tail is in the bottom right piece
CHAT_BOX_LINE_Y = 290  # where the bubble's bottom edge runs, above its tail
ART_PER_TEXT = 1 / 60  # pixels of drawing per pixel of text height

# text is wrapped as if the box were WIDTH_FRACTION of the screen wide, so a paragraph always
# wraps in the same place, but the box is then drawn only as wide as its longest line needs (no
# narrower than MIN_WIDTH_FRACTION). Its height grows with the text, up to MAX_ROWS rows
WIDTH_FRACTION = 0.7
MIN_WIDTH_FRACTION = 0.28
MAX_ROWS = 15
PANEL_ALPHA = 150

SKIP_HINT = "SPACE to skip"  # shown on the box while the story is being told...
CONTINUE_HINT = "SPACE to go on"  # ...and this once it has been told, until the player goes on


class DialogueBox:
    """Lays out and draws the dialogue box."""

    def __init__(self, text: TextRenderer) -> None:
        """Load the two frames; without them the box is a plain rectangle."""
        self.text = text
        self.art: dict[str, pygame.Surface] = {}
        for file in (TEXT_BOX_FILE, CHAT_BOX_FILE):
            picture = assets.load_picture(file)
            if picture is not None:
                self.art[file] = picture
        self._cache: dict[tuple, pygame.Surface] = {}

    def draw(
        self,
        screen: pygame.Surface,
        rows: list[tuple[str, str, bool]],
        *,
        waiting_for_press: bool,
        show_tag: bool,
        seconds_left: int | None,
        margin: int,
        row_gap: int,
    ) -> tuple[int, int, int, int]:
        """Draw ``rows`` in the box; return where the box went (x, y, width, height).

        ``show_tag`` puts the "SPACE to skip" tag on its bottom edge. ``seconds_left`` is a timed
        question's countdown, drawn beside the hearts.
        """
        width, height = screen.get_size()
        text = self.text
        max_box_width = int(width * WIDTH_FRACTION)
        min_box_width = int(width * MIN_WIDTH_FRACTION)

        hint_text = CONTINUE_HINT if waiting_for_press else SKIP_HINT
        hint = text.render(hint_text, "white", True)
        scale = hint.get_height() * ART_PER_TEXT  # the drawing is scaled to the size of the text
        xs, ys = CHAT_BOX_CUTS
        left_cap = round((xs[1] - xs[0]) * scale)
        right_cap = round((xs[3] - xs[2]) * scale)
        top_cap = round((ys[1] - ys[0]) * scale)
        # the tag is written smaller, in a little text box just inside the bottom edge
        tag_text = text.render(hint_text, "white", False)
        tag_height = tag_text.get_height() + margin // 2
        bottom_cap = round((ys[3] - ys[2]) * scale) + margin // 2 + tag_height
        left_pad = right_pad = round(40 * scale) + margin  # room for the lines of the drawing
        top_pad = top_cap + margin // 2
        inner_width = max_box_width - left_pad - right_pad

        wrapped = [
            (sub_line, color, big)
            for row_text, color, big in rows
            for sub_line in text.wrap(row_text, big, inner_width)
        ][-MAX_ROWS:]

        # a timed question's countdown goes in orange right after the hearts - on a row of its
        # own only if there is no hearts row to sit beside
        countdown = None if seconds_left is None else f"[{seconds_left}s left]"
        hearts_row = None
        if countdown is not None:
            for index in range(len(wrapped) - 1, -1, -1):
                if wrapped[index][0].startswith("Hearts:"):
                    hearts_row = index
                    break
            if hearts_row is None:
                wrapped.append((countdown, "orange", True))
                wrapped = wrapped[-MAX_ROWS:]
                countdown = None

        colors = {**OPTION_COLORS, SPEAKER_LABEL: SPEAKER_LABEL_COLOR}
        surfaces = [text.render(t, colors.get(color, color), big) for t, color, big in wrapped]
        # the choices share one column: the same left edge for every one of them, with the ">"
        # in a gutter beside it so the words never shift
        option_rows = [
            row for row, (_t, color, _big) in enumerate(wrapped) if color in OPTION_COLORS
        ]
        gutter = text.menu_font.size("> ")[0]
        tail = text.menu_font.size(" <")[0]  # room for the "<" after the longest choice
        column_width = max((surfaces[row].get_width() for row in option_rows), default=0)
        press_shift = max(2, round(4 * scale))  # how far a click pushes the markers in
        countdown_surface = None
        countdown_x = 0
        if countdown is not None and hearts_row is not None:
            countdown_surface = text.render(countdown, "orange", True)
            countdown_x = surfaces[hearts_row].get_width() + text.menu_font.size("  ")[0]
        row_heights = [surface.get_height() + row_gap for surface in surfaces]
        box_height = top_pad + sum(row_heights) + bottom_cap

        # hug the widest line, between the minimum width and the width wrapping allowed for,
        # and never narrower than the drawing's own corners
        content_width = max((surface.get_width() for surface in surfaces), default=0)
        if countdown_surface is not None:
            content_width = max(content_width, countdown_x + countdown_surface.get_width())
        if option_rows:
            content_width = max(content_width, gutter + column_width + tail)
        box_width = min(max_box_width, max(min_box_width, content_width + left_pad + right_pad))
        box_width = max(box_width, left_cap + right_cap + round(20 * scale))

        box = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        if CHAT_BOX_FILE in self.art:
            # a dark panel inside the drawn lines, tail and all, then the lines
            frame = self._frame(CHAT_BOX_FILE, box_width, box_height, scale)
            box.blit(self._inside(frame), (0, 0))
            box.blit(frame, (0, 0))
        else:  # the drawing is missing: a plain box
            box.fill((10, 10, 10, PANEL_ALPHA))
            pygame.draw.rect(box, "white", box.get_rect(), 1)

        y = top_pad
        for row, (surface, row_height) in enumerate(zip(surfaces, row_heights, strict=True)):
            if row in option_rows:
                # a little left of centre: the column starts 20% of the way along the free space
                free = box_width - left_pad - right_pad - gutter - column_width - tail
                x = left_pad + max(0, int(free * 0.2))
                self._draw_choice(box, surface, wrapped[row][1], (x, y), gutter, tail, press_shift)
            else:
                box.blit(surface, (left_pad, y))
            if countdown_surface is not None and row == hearts_row:
                box.blit(countdown_surface, (left_pad + countdown_x, y))
            y += row_height

        x = (width - box_width) // 2
        y = height - box_height - margin * 3
        screen.blit(box, (x, y))

        if show_tag:  # in the bottom left corner of the bubble, clear of the tail on the right
            tag_scale = scale * 0.25
            tag_xs = TEXT_BOX_CUTS[0]
            tag_width = max(
                tag_text.get_width() + margin,
                round((tag_xs[1] + tag_xs[3] - tag_xs[2]) * tag_scale) + 2,
            )
            tag_x = x + left_pad
            tag_y = y + box_height - round((ys[3] - CHAT_BOX_LINE_Y) * scale) - tag_height
            tag_y -= margin // 4
            if TEXT_BOX_FILE in self.art:
                frame = self._frame(TEXT_BOX_FILE, tag_width, tag_height, tag_scale)
                screen.blit(frame, (tag_x, tag_y))
            screen.blit(
                tag_text,
                (
                    tag_x + (tag_width - tag_text.get_width()) // 2,
                    tag_y + (tag_height - tag_text.get_height()) // 2,
                ),
            )
        return (x, y, box_width, box_height)

    def _draw_choice(
        self,
        box: pygame.Surface,
        surface: pygame.Surface,
        kind: str,
        position: tuple[int, int],
        gutter: int,
        tail: int,
        press_shift: int,
    ) -> None:
        """Draw one menu choice, with "> <" round it if it is the chosen one."""
        x, y = position
        row_width = gutter + surface.get_width() + tail
        pressed = kind == OPTION_PRESSED
        lift = press_shift // 2 if pressed else 0  # a click pushes the whole row down
        push = press_shift if pressed else 0
        if kind in (OPTION_SELECTED, OPTION_PRESSED):
            color = "orange" if pressed else "khaki"
            left_marker = self.text.render(">", color, True)
            right_marker = self.text.render("<", color, True)
            box.blit(left_marker, (x + push, y + lift))
            box.blit(right_marker, (x + row_width - right_marker.get_width() - push, y + lift))
        box.blit(surface, (x + gutter, y + lift))

    def _frame(self, file: str, width: int, height: int, scale: float) -> pygame.Surface:
        """A hand-drawn frame stretched to width x height, its corners kept at ``scale``."""
        key = (file, width, height, round(scale, 3))
        frame = self._cache.get(key)
        if frame is not None:
            return frame
        art = self.art[file]
        xs, ys = TEXT_BOX_CUTS if file == TEXT_BOX_FILE else CHAT_BOX_CUTS
        left, right = round((xs[1] - xs[0]) * scale), round((xs[3] - xs[2]) * scale)
        top, bottom = round((ys[1] - ys[0]) * scale), round((ys[3] - ys[2]) * scale)
        columns = [left, max(1, width - left - right), right]
        rows = [top, max(1, height - top - bottom), bottom]
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        x = 0
        for column, column_width in enumerate(columns):
            y = 0
            for row, row_height in enumerate(rows):
                piece = art.subsurface(
                    (xs[column], ys[row], xs[column + 1] - xs[column], ys[row + 1] - ys[row])
                )
                frame.blit(
                    pygame.transform.smoothscale(piece, (max(1, column_width), max(1, row_height))),
                    (x, y),
                )
                y += row_height
            x += column_width
        if len(self._cache) > 80:
            self._cache.clear()
        self._cache[key] = frame
        return frame

    def _inside(self, frame: pygame.Surface) -> pygame.Surface:
        """The dark panel for everything inside a frame's drawn lines, following their shape.

        Found by flooding the outside from a corner: whatever the flood cannot reach is inside.
        """
        key = ("inside", id(frame))
        inside = self._cache.get(key)
        if inside is None:
            lines = pygame.mask.from_surface(frame, 100)
            lines.invert()  # now the empty pixels are set...
            outside = lines.connected_component((0, 0))  # ...and these are the ones it reaches
            outside.draw(pygame.mask.from_surface(frame, 20), (0, 0))  # never under the lines
            outside.invert()
            inside = outside.to_surface(setcolor=(10, 10, 10, PANEL_ALPHA), unsetcolor=(0, 0, 0, 0))
            self._cache[key] = inside
        return inside
