# How to work on After Hours

Read this once before your first pull request. It is short on purpose.

## Setting up (once)

```bash
git clone https://github.com/andrii-kovalskyi02/after-hours.git
cd after-hours
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

Check it works:ruff 

```bash
python main.py
pytest
```

In PyCharm: **Settings > Project > Python Interpreter > Add > Existing** and pick
`.venv/bin/python`.

## Building your room

This is the whole job. You write **one file** and change **one line**.

1. **Copy the template.**
   `rooms/_template.py` -> `rooms/<your_room>.py`
   (lowercase with underscores, e.g. `classroom_2031.py`).
   Read `rooms/classroom_2035.py` too - that is a finished room.

2. **Fill in the fields.** Your room is *data*: a name, an area, the text the
   player reads, its exits, what it contains. Every field is explained in the
   template.

3. **Add your items.** If your room contains or needs an item, add it to
   `ITEM_CATALOGUE` in `inventory.py`.

4. **Register it.** Add your module to the import line in
   `rooms/__init__.py`, keeping the list alphabetical.

5. **Run `pytest`.** You do not write these tests - the room contract suite
   runs against your room automatically and tells you, by name, what is wrong.

6. **Open a pull request** from a branch named `room/<story>-<room>`, e.g.
   `room/us1c-classroom-2031`. Link your issue in the description.

### What you must not write

No `while` loop. No `input()`. No `print()`. No menu. No checking whether the
player has a key. **The engine does all of that**, once, for every room - that
is the only reason six people can build rooms at the same time without the game
falling apart in week 3.

The player never types a command. Every turn the engine shows a short numbered
list, and picking "Look around" leads to a second list built from what your
room contains: one line per inspectable, one per item lying there, and one for
your boss. You write the contents; the engine writes the menu.

This is why your room is only data. Listing an `Inspectable` is enough to make
it appear. Setting `requires=` is enough to make the door refuse the player.
There is nothing to wire up.

A digit of the exit code is an ordinary item with a `colour` and a `value`
(see `ITEM_CATALOGUE`). Hand one out as a boss `reward` or leave it in `items`:
it shows in the backpack, cannot be picked up twice, and the exit door (a room
with `is_exit=True`) counts it. See `digits.py` (#116).

If your room needs something the engine cannot do, say so in the issue before
you build a workaround. Nine times out of ten it belongs in the engine so that
everyone's room gets it.

### Your boss, and its quirk

Every boss in the design document behaves differently, and all of it is
declared in your `Boss(...)` - there is no engine change to make, whichever
quirk you were given:

| What your boss does | What you write |
|---|---|
| multiple choice | `Question(prompt=..., answers=..., choices=(...))` |
| an open question | the same, with no `choices` |
| a question with no right answer | `answers=()` |
| a time limit | `Question(seconds=10)` |
| no time limit | leave `seconds` out |
| "type this word, quickly" | `models.typing_attack("word", seconds=10)` |
| a fight the player cannot win | `single_attempt=True` |
| a side quest rather than a boss | `side_quest=True` |

Hearts are the engine's job too: a wrong answer or a missed timer costs a
whole heart against a boss and half of one on a side quest, and beating it
gives the same back. A `single_attempt` loss costs nothing, because losing it
is the story. Three hearts gone ends the run.

The Evil Backpack comments on what the player does from US1c onwards. It hooks
into the engine, so **do not call it from your room** - and do not write lines
for it anywhere but `narrator.py`.

Two escape hatches exist for the rare case:

- `on_first_enter=<async function>` - runs once when the player first walks in.
  `classroom_2035.py` uses it for the wake-up scene.
- `Boss(...)` - a challenge with questions. Declared as data; the engine runs it.

To print from either of those, use `await ui.say(...)` or `await ui.narrate(...)`, never
`print(...)`. That is what lets the tests play your room without a human at the keyboard, and the
game keep drawing (in the window or a browser) while it waits for the player.

## What the engine gives you

| File | What it does | Issue |
|---|---|---|
| `models.py` | `Room`, `Item`, `Inspectable`, `Boss`, `Question`, `Area` | #96 |
| `world.py` | the world graph, room lookup, lock enforcement | #96 |
| `game.py` | the one main loop and all player state | #92 |
| `commands.py` | the menu, and what each choice does | #92 |
| `inventory.py` | the item catalogue and what the player carries | #100 |
| `encounters.py` | running a boss's questions, and what a fight costs | #104 |
| `health.py` | hearts, in halves | #108 |
| `narrator.py` | what the Evil Backpack says, and when | #103 |
| `digits.py` | the four digits of the code, and the exit door | #116 |
| `ui.py` | all screen output, keyboard input, and the numbered menu | #151 |
| `floor_map.py` | the map | #120 |

## Before you push

```bash
ruff format .      # fixes the layout for you
ruff check .       # finds the real problems
pytest
```

CI runs exactly these three on every pull request. A red tick is not a
disaster - open the failed job, scroll to the red line, and it names the file
and the rule. Fix it and push again.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org). Every commit
message starts with a type, then a colon, then a short summary in the
imperative - "add", not "added" or "adds":

```
feat: add classroom 2.031 and the Evil Backpack boss
```

The types you will need:

| Type | Use it for |
|---|---|
| `feat` | a new room, command, or anything the player can notice |
| `fix` | correcting behaviour that was wrong |
| `test` | adding or changing tests only |
| `docs` | README, CONTRIBUTING, comments and docstrings only |
| `refactor` | changing how code is written without changing what it does |
| `chore` | tooling, CI, dependencies, project config |

Rules:

- Lowercase after the colon, and no full stop at the end.
- Keep the summary under about 72 characters.
- If it needs more explanation, leave a blank line and write a paragraph
  underneath saying **why**, not what.
- Reference the issue in the body: `Refs #17`.

Why bother: the history becomes readable, and "what changed in sprint 2" is a
question anyone can answer by reading `git log` instead of asking you.

## Pull requests

- One story or task per pull request. Small is good.
- Link the issue: `Closes #17`.
- Somebody else reviews and merges. Never merge your own.
- Never push to `main`.

## Style

`ruff` decides layout, so do not argue with it - run `ruff format .` and move
on. The rules it cannot check:

- Names in English, `snake_case` for functions and variables, `CapWords` for
  classes.
- Every public function gets a docstring saying what it does, in the Google
  style you can see everywhere in this repo.
- Type hints on every function signature.
- A comment should say *why*, not *what*. The code already says what.
