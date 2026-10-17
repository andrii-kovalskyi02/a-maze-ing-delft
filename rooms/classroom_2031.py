"""US1c - Room: Classroom 2.031 - the Evil Backpack Issue #13."""

from __future__ import annotations

from models import Area, Boss, Question, Room, Unless
from world import register

ROOM = Room(
    key="classroom_2031",
    name="Classroom 2.031",
    area=Area.BLUE,
    description=(
        "You enter Classroom 2.031... A shiver runs down your spine.",
        0.6,
        "You decide to enter regardless.",
    ),
    return_description="The empty classroom, just as you left it.",
    look_around=(
        "You see an unusually empty classroom as you look around. ",
        0.6,
        "Unlike Classroom 2.035 there's nothing on the desks... Something feels off",
        Unless(
            "backpack", (0.6, "Theres a backpack on one of desk, your curiosity is eating at you")
        ),
    ),
    exits=("corridor_blue",),
    requires=None,
    locked_text="The door is locked. Something with a blue stripe would help.",
    items=(),
    boss=Boss(
        name="backpack",
        intro=(
            "Hello dear student, it is ME the Backpack",
            0.6,
            "...",
            0.8,
            "You don't seem too excited. Nonetheless i am here to propose an idea!",
            0.5,
            "If you win. I will disapear into thin air and never bother you again.",
            0.7,
            "But if you lose...",
            0.4,
            "YOU will have to carry me throughout your dr- ",
            0.6,
            "I mean adventure!!",
            0.5,
            "Oh, and a word of warning, dear student.",
            0.5,
            "Out there, every question comes with a clock.",
            0.6,
            "Answer too slowly and it counts as WRONG. Hehe.",
            0.6,
            "Mine don't have one though. I'm generous like that.",
            0.5,
            "Understood?...",
            0.8,
            "GREAT LETS GET GOING THEN SHALL WE!",
        ),
        questions=(
            Question(
                prompt="Lets start of easy. What is 1+1 equal to?",
                answers=("2", "two", "2."),
            ),
            Question(
                prompt="Hmm.. too easy? What are the first 3 digits of Pi",
                answers=(
                    "3.14",
                    "314",
                ),
                choices=(
                    "3.14",
                    "4.13",
                    "I have no clue",
                ),
            ),
            Question(
                prompt="How about this?"
                "I have but one last easy question for you."
                "What is the deep state of ↸∷ᒷᔑᒲ╎リ⊣ ||𝙹⚍re ꖎi⍊g ⎓d⍑ᓭ⋮a",
                answers=(),
            ),
        ),
        win_text="shouldnt see ts",
        lose_text="*The backpack quickly attaches itself to you*...",
        reward=None,
        lose_reward="backpack",
        lose_reward_text="Oh, and here, catch, you might find this useful",
        lose_reward_2="blue_card",
        single_attempt=True,
    ),
)

register(ROOM)
