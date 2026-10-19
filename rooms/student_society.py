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
        "A kicker table stands in the middle of the room.",
        0.4,
        "Its ball is frozen on the halfway line.",
        0.6,
        "An iPad sits on one of the chairs, barely visible.",
        0.6,
        "Mismatched seats are pushed in around the walls.",
        0.4,
        "Posters cover most of the space between them.",
        0.6,
        "One flyer is dated for next year.",
    ),
    exits=("corridor_red",),
    requires=None,
    locked_text="the door is unlocked? ",
    inspectables=(
        Inspectable(
            name="the kicker table",
            text=(
                "A battered foosball table, ball frozen mid-shot.",
                0.4,
                "A single red light blinks above one goal.",
                0.4,
                "You can't see where it's plugged in.",
            ),
        ),
        Inspectable(
            name="the ipad",
            text=(
                "Left on one of the chairs, screen still on.",
                0.4,
                "It's open to a note-taking app, one line typed and unfinished.",
            ),
        ),
        Inspectable(
            name="the posters",
            text=(
                "Flyers for a Sinterklaas party, a LAN night, and a bake sale.",
                0.4,
                "Except one of them is dated for next year.",
                0.4,
                "You're fairly sure that one hasn't happened.",
            ),
        ),
        Inspectable(
            name="the seats",
            text="A row of mismatched chairs, pulled in close as if a meeting just ended.",
        ),
        Inspectable(
            name="the whiteboard",
            text="An agenda: 'Item 1: snacks budget. Item 2: snacks budget (cont.)'",
        ),
    ),
    items=(),
    # Automated kicker table for now, more complex mini-game later on?
    boss=Boss(
        name="Automated Kicker Machine",
        speaker="kicker",
        intro=(
            "The red light above the goal blinks once, twice.",
            0.4,
            "The table shudders to life with no cord, no coin, nothing.",
            0.6,
            "A tiny speaker crackles:",
            0.5,
            says("PENALTY.", 0.3, "SHOOTOUT.", 0.3, "BEST.", 0.2, "OF.", 0.2, "THREE."),
            0.6,
            "The mechanical arm lines up a ball that was not there a moment ago.",
        ),
        questions=(
            Question(
                prompt="Round 1: Where do you aim?",
                choices=("Left", "Center", "Right"),
                answers=("Left",),
                seconds=15,
            ),
            Question(
                prompt="Round 2: Where do you aim?",
                choices=("Left", "Center", "Right"),
                answers=("Right",),
                seconds=15,
            ),
            Question(
                prompt="Round 3: Where do you aim?",
                choices=("Left", "Center", "Right"),
                answers=("Center",),
                seconds=15,
            ),
        ),
        win_text=(
            "The red light flashes green.",
            0.3,
            says("MATCH. LOST."),
            0.5,
            "The speaker grumbles, and the table stills again.",
            0.4,
            "The ball freezes mid-air, exactly where it started.",
        ),
        lose_text=(
            "The red light stays red.",
            0.3,
            says("MATCH. WON."),
            0.5,
            "The machine announces, smug for something that isn't really there.",
        ),
        reward=None,
    ),
)
register(ROOM)
