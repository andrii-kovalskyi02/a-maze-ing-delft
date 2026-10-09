"""room/us1k-student-society Issue #147."""

from __future__ import annotations

from models import Area, Boss, Inspectable, Question, Room
from world import register

ROOM = Room(
    key="student_society",
    name="Student society",
    area=Area.RED,
    description="A student society room that looks like someplace you've seen "
    "before... but you dont remember when or where",
    look_around=(
        "A kicker table stands in the middle of the room, ball frozen on "
        "the halfway line, an iPad sits on one of the chairs barely visible "
        "Mismatched seats are pushed in around the walls, and posters "
        "cover most of the space between them. One flyer is dated for "
        "next year."
    ),
    exits=("corridor_red",),
    requires=None,
    locked_text="the door is unlocked? ",
    inspectables=(
        Inspectable(
            name="the kicker table",
            text=(
                "A battered foosball table, ball frozen mid-shot. A single "
                "red light blinks above one goal, though you can't see "
                "where it's plugged in."
            ),
        ),
        Inspectable(
            name="the ipad",
            text=(
                "Left on one of the chairs, screen still on. It's open to a "
                "note-taking app, one line typed and unfinished."
            ),
        ),
        Inspectable(
            name="the posters",
            text=(
                "Flyers for a Sinterklaas party, a LAN night, and a bake "
                "sale - except one of them is dated for next year, and "
                "you're fairly sure that one hasn't happened."
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
        intro=(
            "The red light above the goal blinks once, twice, and the "
            "  table shudders to life with no cord, no coin, nothing "
            "               A tiny speaker crackles:               "
            "       PENALTY. SHOOTOUT. BEST. OF. THREE. The "
            "mechanical arm lines up a ball that was not there a moment "
            "ago."
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
            "The red light flashes green. MATCH. LOST. the speaker "
            "grumbles, and the table stills again, the ball freezing "
            "mid-air exactly where it started."
        ),
        lose_text=(
            "The red light stays red. MATCH. WON. the machine "
            "announces, smug for something that isn't really there."
        ),
        reward=None,
    ),
)
register(ROOM)
