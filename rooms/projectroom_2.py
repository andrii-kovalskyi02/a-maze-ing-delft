"""Project Room 2."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ui
from models import Area, Inspectable, Room
from world import register

if TYPE_CHECKING:
    from game import Game


def supervisor_meeting(game: Game) -> None:
    """Run the supervisor meeting once when the player first enters."""
    ui.say()
    ui.narrate("The supervisor looks up from his desk.")
    ui.narrate("You're late for the meeting.")

    first_choice = ui.choose(
        "Your response:",
        (
            "What meeting?",
            "I'm sorry!",
        ),
    )

    if first_choice == 0:
        ui.narrate("The project meeting.")
        ui.narrate("Which project?")

        project_choice = ui.choose(
            "Your response:",
            (
                "I have many projects.",
                "...",
            ),
        )

        if project_choice == 0:
            ui.narrate("The supervisor stares at you.")
            ui.narrate("Yes. I noticed.")
        else:
            ui.narrate("The supervisor waits for an answer.")
            ui.narrate("You say nothing.")
            ui.narrate("Honestly, that might be your best answer so far.")

    else:
        ui.narrate("Anyway... did you finish the project?")

        project_choice = ui.choose(
            "Your response:",
            (
                "I am working on it.",
                "Which project?",
            ),
        )

        if project_choice == 0:
            ui.narrate(
                "That's reassuring. I was beginning to think "
                "you were working on something else."
            )
        else:
            ui.narrate("...The one we're having this meeting about.")

    ui.narrate("You know what? Let's just call this a progress meeting.")
    ui.narrate("What progress?")
    ui.narrate("Exactly.")

ROOM = Room(
    key="projectroom_2",
    name="Project Room 2",
    area=Area.YELLOW,
    requires=None,
    description=(
        "You enter Project Room 2. A supervisor is sitting at a desk, "
        "looking at you as if he has been waiting for you."
    ),
    look_around=("A desk stands in the middle of the room. A whiteboard hangs on the wall."),
    exits=("lobby",),
    inspectables=(
        Inspectable(
            name="the TODO list",
            text=(
                "TODO\n\n"
                "- Finish project\n"
                "- Finish documentation\n"
                "- Test everything\n"
                "- Fix everything\n\n"
                "IMPORTANT:\n"
                "DO NOT PANIC"
            ),
        ),
    ),
    on_first_enter=supervisor_meeting,
)

register(ROOM)
