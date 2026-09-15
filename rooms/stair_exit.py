from __future__ import annotations

from world import register

from models import Area, Boss, Inspectable, Question, Room

ROOM = Room(
    # The unique id of your room. Other rooms use this in their exits.
    key="stair_exit",
    # How the room is shown on screen.
    name="Stair Exit",
    # Area.BLUE, Area.RED or Area.YELLOW - check the evacuation plan.
    area=Area.BLUE,
    # One or two lines, printed every time the player walks in.
    description="The stairs leading to the main exit.",
    # The longer text for 'look around'. Take your time with this one: it is
    # the part of the game the player reads most.
    look_around=(
        "test"
    ),
    # The keys of the rooms you can walk to from here. Both directions have to
    # be listed: if you can walk back, the other room needs your key too.
    exits=("corridor_blue",),
    # The key of an item needed to get in, or None for an unlocked room. The
    # engine checks the backpack itself - the player never types "use key".
    requires="digit_4",
    # What the player reads when they do not have that item.
    locked_text="The exit is locked. A 4 digit pin is needed to unlock.",
    # Details the player can 'inspect'. Cheap to add and they make a room feel
    # real, so add more than you think you need.
    inspectables=(
        Inspectable(name="poster", text="A fire evacuation poster, curling at the corners."),
    ),
    # Items lying here, by key. Add them to ITEM_CATALOGUE first.
    items=(),
    # The challenge guarding your room, or None. Delete this whole block if
    # your room has no boss.
    boss=None,
    approach_reward_text="Something is scratched into the doorframe: a single digit, \"1\".... You decide to pick it up",
    approach_reward="digit_1",
)
register(ROOM)
