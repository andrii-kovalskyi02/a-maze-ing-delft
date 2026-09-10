"""The details the Memory Keeper asks about, and the one that sets up the twist.

The final boss (US1l) quizzes the player on what they saw in classroom 2.035
in the opening scene. If the wording drifted between the two rooms the quiz
would be unanswerable, so both rooms read it from here.

**Do not change these strings without changing the Memory Keeper's questions
in the same commit.**

Each of the three objects in 2.035 is here for its own reason, and they are
not interchangeable:

* the **desk note** answers Question 2, "what did you find on the desk"
* the **laptop** answers Question 5, "what were you doing before you woke up"
* the **clock** answers nothing - Question 1 asks about the clock in Project
  room 3, not this one. It is here so the player sees 23:17 twice. Hours of
  exploring happen between the two, and the time has not moved, because none
  of it happened. That is the twist, and it only lands if the two clocks
  agree - which is why the time is a constant read by both rooms rather than
  typed into each.
"""

from __future__ import annotations

#: Shown by the clock in 2.035 (US1a) and the clock in Project room 3 (US1l).
#: The two MUST agree. Project room 3's clock is the one Question 1 asks about;
#: 2.035's is the setup that makes the answer feel earned.
CLOCK_TIME = "23:17"

#: What the laptop in 2.035 is showing (US1a). This is the only place the
#: answer to Question 5 - "working on your project" - can be discovered.
LAPTOP_NOTIFICATION = "Project deadline: Tomorrow."

#: What the player finds on their desk in 2.035, and the answer to Question 2.
#:
#: It used to be a backpack, which made the game contain two backpacks - the
#: player's own and the Evil Backpack that becomes their inventory in 2.031
#: (US1c). One backpack is enough, and it is the one with teeth.
DESK_CONTENTS = "a note"
