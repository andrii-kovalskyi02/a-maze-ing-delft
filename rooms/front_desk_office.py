"""The Front Desk Office and Check-In Terminal encounter."""

from __future__ import annotations

from models import Area, Boss, Inspectable, Question, Room, says
from world import register

ROOM = Room(
    key="front_desk_office",
    name="Front Desk Office",
    area=Area.RED,
    description=(
        "A cramped front desk office under harsh fluorescent lights.",
        0.4,
        "It smells of printer paper and bureaucratic authority.",
    ),
    look_around=(
        "Buzzing fluorescent tubes illuminate a narrow service counter.",
        0.5,
        "Beyond it is a wall of notice boards and strict administrative regulations.",
        0.6,
        "On the desk, a silent desktop monitor glows next to an office phone.",
        0.5,
        "Nearby sit stacks of color-coded request forms and ink stamps.",
        0.6,
        "A small keycard scanner on the counter blinks an expectant green light.",
    ),
    exits=("corridor_red",),
    inspectables=(
        Inspectable(
            name="the counter",
            text="A scratched wooden service desk with a narrow transaction window.",
        ),
        Inspectable(
            name="the computer",
            text="An office desktop displaying a login screen for the student management portal.",
        ),
        Inspectable(
            name="the phone",
            text="A multi-line landline phone with a blinking voicemail indicator.",
        ),
        Inspectable(
            name="the forms and stamps",
            text="Neatly arranged stacks of building access permits and a red 'DENIED' ink stamp.",
        ),
        Inspectable(
            name="the notice boards",
            text="Pinned with departmental memos, opening hours, and strict building rules.",
        ),
    ),
    items=(),
    boss=Boss(
        name="the Check-In Terminal",
        speaker="terminal",
        intro=(
            says("State your business."),
            0.8,
            "A mechanical whir rises from the desk.",
            0.4,
            "A hybrid scanner-monitor-printer comes alive.",
            0.6,
            "Its screen displays two glowing digital eyes.",
            0.4,
            "Its printer tray clacks open like a mouth.",
            0.4,
            "Red indicator lights pulse as its visitor-slip arms rustle.",
        ),
        questions=(
            # Question 1 (Open-ended)
            Question(
                prompt=(
                    "I let staff call another office without walking there, "
                    "but I am not a computer. What am I?"
                ),
                answers=(
                    "extension",
                    "an extension",
                    "extension number",
                    "an extension number",
                    "phone",
                    "a phone",
                    "telephone",
                    "a telephone",
                    "intercom",
                    "an intercom",
                    "desk phone",
                ),
                seconds=15,
            ),
            # Question 2 (Multiple choice)
            Question(
                prompt="Which object is used to hold paper steady while someone writes on it?",
                choices=("Clipboard", "Mouse", "Stapler", "Desk lamp"),
                answers=("Clipboard",),
                seconds=15,
            ),
            # Question 3 (Multiple choice)
            Question(
                prompt="What object is used to fasten papers together temporarily?",
                choices=("Paperclip", "Highlighter", "Phone", "Monitor"),
                answers=("Paperclip",),
                seconds=15,
            ),
            # Question 4 (Open-ended)
            Question(
                prompt="I show a person's name or role before they even speak. What am I?",
                answers=(
                    "name tag",
                    "a name tag",
                    "nametag",
                    "a nametag",
                    "id badge",
                    "an id badge",
                    "badge",
                    "a badge",
                    "name badge",
                    "a name badge",
                ),
                seconds=15,
            ),
        ),
        win_text=(
            says('"Access granted. You may pass."'),
            0.8,
            "The red lights switch to a steady green.",
            0.4,
            "The printer tray closes with a snap.",
            0.4,
            "A small metallic key ejects onto the counter.",
        ),
        lose_text=(
            says('"Access denied. Please consult the regulations and try again."'),
            0.6,
            "The terminal flashes red and powers down its tray.",
        ),
        reward="storage_key",
    ),
)

register(ROOM)
