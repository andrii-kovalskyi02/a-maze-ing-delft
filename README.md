# A-maze-ing Delft

A text-based adventure/maze game set on the 2nd floor of THUAS Delft (ICT/ACS section),
built for the Applied Computer Science Q1 project by **Team ACS**.

The player wakes up in classroom 2.035 to a fire alarm, has to explore the building,
defeat the bosses guarding each area, collect four colour-coded digits and enter them
at the exit door to escape.

The player never has to remember a command. Every turn they are shown a numbered
list of what they can do right then, and they press a number. The one exception is
a boss asking an open question, which is answered in the player's own words.

## Running it

Requires Python 3.12 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python main.py
```

## Working on it

**Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first pull request.** It has the
six-step recipe for adding a room, and the three commands to run before you push.

Building a room means writing one file and changing one line. Start from
`rooms/_template.py`, and read `rooms/classroom_2035.py`
as a worked example.

## How the code is laid out

```
main.py          start the game
models.py        the data types a room is built from (Room, Item, Boss, ...)
world.py         the world graph: every room, and the locks between them
game.py          the one main loop, and everything true about a play-through
commands.py      the menu, and what each choice does
inventory.py     the item catalogue and what the player carries
encounters.py    running a boss's questions
memories.py      the details the Memory Keeper asks about at the end
ui.py            all screen output, keyboard input, and the numbered menu
floor_map.py     the map (issue #120, not built yet)
rooms/           one file per room - this is where the team works
tests/
  test_room_contract.py   runs against every registered room, automatically
```

The engine owns the loop so that no room has to. That is what lets several people
build rooms at the same time without six different command loops to merge.

## Backlog

The product backlog lives in this repository's issues and on the
[A-maze-ing Delft project board](https://github.com/users/andrii-kovalskyi02/projects/1).

| Label | Meaning |
|---|---|
| `user-story` | A Product Backlog Item. One per room (US1a, US1b, ...), plus US2-US5 from the Project Guide |
| `task` | A sub-issue: concrete work under a user story |
| `enabler` | Technical work with no direct player-facing story (menu, world graph, quiz engine, persistence) |
| `process` | Scrum/course deliverables (Appendix I documents, Sprint 0 setup) |
| `question` | An open design question that needs a team or Product Owner decision |
| `area:blue` / `area:red` / `area:yellow` / `area:core` | Which part of the building, or the shared engine |

Milestones map to the sprints in the Project Guide: Sprint 1 (week 2-4, engine enablers
and rooms), Sprint 2 (week 4-6, US2-US5 and persistence), Sprint 3 (week 7-8, fixes and
improvements).

## Framework

Started from [SimpleMaze](https://github.com/pb12/SimpleMaze), the framework provided with
the project assignment. The seed is preserved in this repository's git history; the engine
described above replaced it once the shared room contract was agreed (issue #96).
