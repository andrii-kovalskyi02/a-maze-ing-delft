"""COPY ME.  This is the starting point for a new room.

How to use this file:

1. Copy it to ``rooms/<your_room>.py`` - lowercase, underscores,
   e.g. ``classroom_2031.py``.
2. Fill in every field below.  Delete the ones you do not need; they all have
   sensible defaults.
3. Add any items your room contains to ``ITEM_CATALOGUE`` in ``inventory.py``.
4. Import your module in ``rooms/__init__.py``.
5. Run ``pytest``.  The room contract tests run against your room without you
   writing a single one.
6. Open a pull request from a branch named ``room/<story>-<room>``, e.g.
   ``room/us1c-classroom-2031``.

Notice what is NOT here: no ``while`` loop, no ``input()``, no ``print()``, no
menu, no checking whether the player has a key.  The engine does all of that.
Your room only says what it contains, and the engine works out what to offer
the player.  If you find yourself wanting to write a loop, ask first - it
probably belongs in the engine so that every room gets it.

This file is a template, not a room: it does not register itself.
"""

from __future__ import annotations

from world import register

from models import Area, Boss, Inspectable, Question, Room

ROOM = Room(
    # The unique id of your room. Other rooms use this in their exits.
    key="classroom_2031",
    # How the room is shown on screen.
    name="Classroom 2031",
    # Area.BLUE, Area.RED or Area.YELLOW - check the evacuation plan.
    area=Area.BLUE,
    # One or two lines, printed every time the player walks in.
    description="You enter Classroom 2.031... A shiver runs down your spine"
                "You decide to enter regardless",
    # The longer text for 'look around'. Take your time with this one: it is
    # the part of the game the player reads most.
    look_around=(
        "You see an unusually empty classroom as you look around. "
        "Unlike Classroom 2.035 theres nothing on the desks... Something feels off"
    ),
    # The keys of the rooms you can walk to from here. Both directions have to
    # be listed: if you can walk back, the other room needs your key too.
    exits=("corridor_blue",),
    # The key of an item needed to get in, or None for an unlocked room. The
    # engine checks the backpack itself - the player never types "use key".
    requires=None,
    # What the player reads when they do not have that item.
    locked_text="The door is locked. Something with a blue stripe would help.",
    # Details the player can 'inspect'. Cheap to add and they make a room feel
    # real, so add more than you think you need.
    # Items lying here, by key. Add them to ITEM_CATALOGUE first.
    items=(),
    # The challenge guarding your room, or None. Delete this whole block if
    # your room has no boss.
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