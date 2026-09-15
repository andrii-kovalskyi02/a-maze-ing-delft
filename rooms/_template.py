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

from models import Area, Boss, Inspectable, Question, Room

ROOM = Room(
    # The unique id of your room. Other rooms use this in their exits.
    key="template_room",
    # How the room is shown on screen.
    name="Template Room",
    # Area.BLUE, Area.RED or Area.YELLOW - check the evacuation plan.
    area=Area.BLUE,
    # One or two lines, typed out every time the player walks in. Instead of
    # one string you can give a tuple of parts, typed one after another, and
    # put a number between them to pause that many seconds:
    #     description=("The lights flicker.", 1.5, "Then they go out."),
    # The same works for look_around, inspectable text and a boss's lines.
    description="A room that does not exist. You should not be able to get here.",
    # The longer text for 'look around'. Take your time with this one: it is
    # the part of the game the player reads most. Leave it out only for a place
    # with nothing to describe, like a staircase you just pass through.
    look_around=(
        "Describe what the player sees, hears and smells. Mention anything "
        "they can interact with, so they are never left guessing."
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
    inspectables=(
        Inspectable(name="poster", text="A fire evacuation poster, curling at the corners."),
    ),
    # Items lying here, by key. Add them to ITEM_CATALOGUE first.
    items=(),
    # The challenge guarding your room, or None. Delete this whole block if
    # your room has no boss.
    boss=Boss(
        name="the Example",
        intro="Someone blocks your way and clears their throat.",
        questions=(
            Question(
                prompt="What is 7 * 6?",
                answers=("42", "forty two", "forty-two"),
            ),
            Question(
                prompt="Which floor are you on?",
                answers=("the 2nd",),
                choices=("the ground floor", "the 1st", "the 2nd", "the roof"),
            ),
        ),
        win_text="They step aside, impressed despite themselves.",
        lose_text="They shake their head and block the door again.",
        reward=None,
    ),
)

# The last line of a real room module registers it. It is commented out here
# so that the template itself never ends up in the game:
#
# register(ROOM)
