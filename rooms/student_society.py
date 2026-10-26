"""room/us1k-student-society Issue #147."""

from __future__ import annotations

from models import Area, Boss, Inspectable, Question, Room, says
from world import register

ROOM = Room(
    key="student_society",
    name="Equinox Student Society",
    area=Area.RED,
    description=(
        "This student society room looks familiar.",
        0.5,
        "You don't remember when or where.",
    ),
    return_description="The kicker table sits where it did, its ball frozen on the halfway line.",
    look_around=(
        "Two black leather sofas face each other, brown cushions thrown on top.",
        0.4,
        "A big TV hangs on the wall, next to a row of framed group photos and a rainbow flag.",
        0.6,
        "On the glass coffee table, branded EQUINOX, lies a Nintendo Switch.",
        0.6,
        "A tall cupboard is stacked with energy drinks, posters taped to its doors.",
        0.4,
        "At the back, by the windows, a few desks with monitors.",
        0.6,
        "One flyer is dated for next year.",
    ),
    exits=("corridor_red",),
    requires=None,
    locked_text="the door is unlocked? ",
    inspectables=(
        Inspectable(
            name="the posters on the cupboard",
            text=(
                "A green poster: POOL NIGHT, Monday September 28th, at De Peper.",
                0.4,
                "Below it: MTG NIGHT, every 3rd Wednesday of the month.",
                0.4,
                "Someone circled both of them in marker.",

            ),
        ),
        Inspectable(
            name="the coffee table",
            text=(
                "EQUINOX is burned into the wooden frame of the glass table.",
                0.4,
                "A Nintendo Switch sits on top, one red and one blue controller still attached.",
                0.4,
                "The screen is dark, but the controllers are warm.",
            ),
        ),
    ),
    items=(),
    # Automated kicker table for now, more complex mini-game later on?
    boss=Boss(
        name="The Game Night Host",
        speaker="host",
        intro=(
            "The TV on the wall flicks on by itself.",
            0.4,
            "The Switch on the coffee table lights up, red and blue.",
            0.6,
            "A cheerful voice comes from the speakers:",
            0.5,
            says("GAME NIGHT.", 0.4, "BEST.", 0.2, "OF.", 0.2, "THREE."),
            0.6,
            "Only real members know the answers. Did you look around?",
        ),
        questions=(
            Question(
                prompt="Round 1: Where is Pool Night held?",
                choices=("De Peper", "The lobby", "Lab 2.001", "The library"),
                answers=("De Peper",),
                seconds=15,
            ),
            Question(
                prompt="Round 2: When is MTG Night?",
                choices=(
                    "Every Monday",
                    "Every 3rd Wednesday of the month",
                    "The last Friday of the month",
                ),
                answers=("Every 3rd Wednesday of the month",),
                seconds=15,
            ),
            Question(
                prompt="Round 3: What colours are the controllers on the Switch?",
                choices=("Black and black", "Red and blue", "Green and yellow"),
                answers=("Red and blue",),
                seconds=15,
            ),
        ),
        win_text=(
            "Confetti bursts across the TV screen.",
            0.3,
            says("YOU. ARE. ONE. OF. US."),
            0.5,
            "The TV switches off, and the Switch goes dark again.",
        ),
        lose_text=(
            "The TV shows a big red cross.",
            0.3,
            says("NOT. A. MEMBER."),
            0.5,
            "Maybe look around the room first.",
        ),
        reward=None,
    ),
)
register(ROOM)
