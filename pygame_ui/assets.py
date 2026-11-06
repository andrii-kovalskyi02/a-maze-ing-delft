"""Finding and loading the pictures in ``assets/``.

A missing file never crashes the game: the loaders return None, and whatever would have been
drawn is simply left out.
"""

from __future__ import annotations

import json
import os

import pygame

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# background picture per room, keyed by the exact "== Room Name ==" header the game prints when
# you walk in. A room with no entry here gets a plain black background
ROOM_IMAGES = {
    "== classroom.2015 ==": "classroom_2015.png",
    "== Classroom 2021 ==": "classroom_2021.png",
    "== Classroom 2.015 ==": "classroom_2015.png",
    "== Classroom 2.021 ==": "classroom_2021.png",
    "== Classroom 2.035 ==": "classroom_2035.png",
    "== Classroom 2.031 ==": "classroom_2031.jpg",
    "== The Blue corridor ==": "corridor_blue.png",
    "== The Red corridor ==": "corridor_red.png",
    "== LAB2.003 ==": "lab_2003.png",
    "== LAB 2.003 ==": "lab_2003.png",  # the name the room has now
    "== Forest room ==": "lab_2001.png",  # lab_2001
    "== LAB 2.001 ==": "lab_2001.png",  # the name the forest room has now
    "== Teachers room ==": "teacher_room.png",
    "== Teachers room 4 ==": "teacher_room.png",
    "== Front Desk Office ==": "front_desk_office.png",
    "== Storage Room ==": "storage.png",
    "== Lobby ==": "lobby.png",
    "== Main Teachers Room ==": "teacher_room.png",
    "== Teachers Room 4 ==": "teacher_room_4.png",
    "== Project Room 1 ==": "projectroom_1.png",
    "== Project room 1 ==": "projectroom_1.png",
    "== Project Room 2 ==": "projectroom_2.png",
    "== Student society ==": "student_society.png",
    "== Equinox Student Society ==": "student_society.png",  # the name the room has now
    "== Project Room 3 ==": "projectroom_3.png",
}

# the background of the very first screen (the name prompt). It is plain black for now; this is
# the photo to pass to load_cover() when it comes back
INTRO_IMAGE = "intro.jpg"


def path(*parts: str) -> str:
    """The full path of a file in ``assets/``."""
    return os.path.join(ASSETS_DIR, *parts)


def load_picture(*parts: str) -> pygame.Surface | None:
    """Load a picture with see-through parts, or None if the file is missing."""
    file = path(*parts)
    return pygame.image.load(file).convert_alpha() if os.path.exists(file) else None


def load_positions(folder: str) -> dict[str, tuple[int, int]]:
    """Read ``assets/<folder>/index.json``: where each room's picture goes on the map."""
    file = path(folder, "index.json")
    if not os.path.exists(file):
        return {}
    with open(file, encoding="utf-8") as handle:
        return {key: (xy[0], xy[1]) for key, xy in json.load(handle).items()}


def load_cover(filename: str, width: int, height: int) -> pygame.Surface | None:
    """Load a background picture that fills width x height without stretching.

    It is scaled just enough to cover the whole screen, keeping its shape, and the overflow is
    trimmed evenly off both sides. None if the file is missing.
    """
    file = path(filename)
    if not os.path.exists(file):
        return None
    image = pygame.image.load(file).convert()
    scale = max(width / image.get_width(), height / image.get_height())
    size = (round(image.get_width() * scale), round(image.get_height() * scale))
    image = pygame.transform.smoothscale(image, size)
    left = (size[0] - width) // 2
    top = (size[1] - height) // 2
    return image.subsurface((left, top, width, height)).copy()


def load_room_image(header: str, width: int, height: int) -> pygame.Surface | None:
    """The background for the room whose "== Room Name ==" header is ``header``, if it has one."""
    filename = ROOM_IMAGES.get(header)
    return None if filename is None else load_cover(filename, width, height)
