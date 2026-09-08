# How to work on A-maze-ing Delft

Read this once before your first pull request. It is short on purpose.

## Setting up (once)

```bash
git clone https://github.com/andrii-kovalskyi02/a-maze-ing-delft.git
cd a-maze-ing-delft
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Check it works:

```bash
python -m amazing_delft
pytest
```

In PyCharm: **Settings > Project > Python Interpreter > Add > Existing** and pick
`.venv/bin/python`.

## Building your room

This is the whole job. You write **one file** and change **one line**.

1. **Copy the template.**
   `amazing_delft/rooms/_template.py` -> `amazing_delft/rooms/<your_room>.py`
   (lowercase with underscores, e.g. `classroom_2031.py`).
   Read `amazing_delft/rooms/classroom_2035.py` too - that is a finished room.

2. **Fill in the fields.** Your room is *data*: a name, an area, the text the
   player reads, its exits, what it contains. Every field is explained in the
   template.

3. **Add your items.** If your room contains or needs an item, add it to
   `ITEM_CATALOGUE` in `amazing_delft/backpack.py`.

4. **Register it.** Add your module to the import line in
   `amazing_delft/rooms/__init__.py`, keeping the list alphabetical.

5. **Run `pytest`.** You do not write these tests - the room contract suite
   runs against your room automatically and tells you, by name, what is wrong.

6. **Open a pull request** from a branch named `room/<story>-<room>`, e.g.
   `room/us1c-classroom-2031`. Link your issue in the description.

### What you must not write

No `while` loop. No `input()`. No `print()`. No checking whether the player has
a key. **The engine does all of that**, once, for every room - that is the only
reason six people can build rooms at the same time without the game falling
apart in week 3.

If your room needs something the engine cannot do, say so in the issue before
you build a workaround. Nine times out of ten it belongs in the engine so that
everyone's room gets it.

Two escape hatches exist for the rare case:

- `on_first_enter=<function>` - runs once when the player first walks in.
  `classroom_2035.py` uses it for the wake-up scene.
- `Boss(...)` - a challenge with questions. Declared as data; the engine runs it.

To print from either of those, use `ui.say(...)`, never `print(...)`. That is
what lets the tests play your room without a human at the keyboard.

## What the engine gives you

| File | What it does | Issue |
|---|---|---|
| `models.py` | `Room`, `Item`, `Inspectable`, `Boss`, `Question`, `Area` | #96 |
| `world.py` | the world graph, room lookup, lock enforcement | #96 |
| `game.py` | the one main loop and all player state | #92 |
| `parser.py` | turns sloppy typing into commands | #92 |
| `commands.py` | what each command does | #92 |
| `backpack.py` | the item catalogue and the backpack | #100 |
| `encounters.py` | running a boss's questions | #104 |
| `help_text.py` | the one source of the `?` text | #122 |
| `ui.py` | all screen output and keyboard input | - |
| `floor_map.py` | the `map` command - **not built yet** | #120 |

## Before you push

```bash
ruff format .      # fixes the layout for you
ruff check .       # finds the real problems
pytest
```

CI runs exactly these three on every pull request. A red tick is not a
disaster - open the failed job, scroll to the red line, and it names the file
and the rule. Fix it and push again.

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
