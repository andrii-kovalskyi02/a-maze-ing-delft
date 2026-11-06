"""A template for a new room; see CONTRIBUTING.md. It is not a room, so it never registers."""

from __future__ import annotations

from models import Area, Boss, Inspectable, Question, Room

ROOM = Room(
    # the unique id; other rooms use it in their exits
    key="template_room",
    name="Template Room",
    # Area.BLUE, Area.RED or Area.YELLOW
    area=Area.BLUE,
    # typed out on entry. Any text can also be a tuple of parts, a number being a pause:
    #     description=("The lights flicker.", 1.5, "Then they go out."),
    description="A room that does not exist. You should not be able to get here.",
    # the longer text for "Look around"; None for a place with nothing to describe
    look_around=(
        "Describe what the player sees, hears and smells. Mention anything "
        "they can interact with, so they are never left guessing."
    ),
    # both directions must be listed: the other room needs this room's key too
    exits=("corridor_blue",),
    # the key of the item needed to get in, or None
    requires=None,
    locked_text="The door is locked. Something with a blue stripe would help.",
    inspectables=(Inspectable(name="poster", text="A notice poster, curling at the corners."),),
    # item keys, each defined in inventory.ITEM_CATALOGUE
    items=(),
    # None for a room with no boss
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

# a real room ends with: register(ROOM)
