from __future__ import annotations

from world import register

from models import Area, Boss, Inspectable, Question, Room

ROOM = Room(
    key="classroom_2031",
    name="Classroom 2031",
    area=Area.BLUE,
    description="You enter Classroom 2.031... A shiver runs down your spine"
                "You decide to enter regardless",
    look_around=(
        "You see an unusually empty classroom as you look around. "
        "Unlike Classroom 2.035 theres nothing on the desks... Something feels off"
    ),
    exits=("corridor_blue",),
    requires=None,
    locked_text="The door is locked. Something with a blue stripe would help.",
    items=(),
    boss=Boss(
        name="backpack",
        intro="Hello dear student, it is ME the Backpack"
              "..."
              "You don't seem too excited. Nonetheless i am here to propose an idea!"
              "If you win. I will disapear into thin air and never bother you again."
              "But if you lose..."
              "YOU will have to carry me throughout your dr- "
              "I mean adventure!!"
              "Agreed?..."
              "GREAT LETS GET GOING THEN SHALL WE!",
        questions=(
            Question(
                prompt="Lets start of easy. "
                       "What is 1+1 equal to?",
                answers=("2", "two", "2."),
            ),
            Question(
                prompt="Hmm.. too easy? What are the first 3 digits of Pi",
                answers=("3.14", "314",),
                choices=("3.14", "4.13", "I have no clue",),
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