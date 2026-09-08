"""The one and only description of what the player can type (enabler #122).

Both the ``?`` command and the note item in the backpack render this, so the
help can never drift out of date with itself.  When you add a command, add it
here too.
"""

from __future__ import annotations

#: Commands that always work, as (command, explanation) pairs.
ALWAYS_AVAILABLE: tuple[tuple[str, str], ...] = (
    ("?", "Show this note again."),
    ("look around", "Take in the room you are standing in."),
    ("go <room>", "Walk to another room, e.g. 'go 2.031'."),
    ("inspect <thing>", "Look closely at something in the room or in your backpack."),
    ("backpack", "See what you are carrying."),
    ("map", "Show the plan of the 2nd floor."),
    ("options", "Scoreboard, save and quit."),
    ("quit", "Stop playing."),
)

#: Commands that only work in some rooms, as (command, explanation, why) triples.
CONDITIONAL: tuple[tuple[str, str, str], ...] = (
    ("take <item>", "Pick something up.", "when there is something here to take"),
    ("answer <answer>", "Answer the question you were asked.", "during a challenge"),
)


def render(available_conditionals: frozenset[str] = frozenset()) -> str:
    """Return the help text.

    Args:
        available_conditionals: The conditional commands that work right now.
            Ones that do not are still listed, but marked as conditional, so
            the player learns they exist without thinking they are stuck.
    """
    lines = ["You can type:"]
    lines += [f"  {command:<18} {explanation}" for command, explanation in ALWAYS_AVAILABLE]

    conditional_lines = []
    for command, explanation, when in CONDITIONAL:
        verb = command.split()[0]
        suffix = "" if verb in available_conditionals else f"  (only {when})"
        conditional_lines.append(f"  {command:<18} {explanation}{suffix}")
    if conditional_lines:
        lines.append("")
        lines.append("Sometimes:")
        lines += conditional_lines
    return "\n".join(lines)
