# After Hours

> 🏆 **1st place, Best Project** out of 16 project groups that built the same game.
> Every group's students, our professors and other university staff voted.

A story-driven adventure game set on the 2nd floor of THUAS Delft, built in Python by a team of
six students for the Applied Computer Science Q1 project.

## The game

You wake up with your cheek stuck to a desk in classroom 2.035. It is late, the building is far too
quiet, and everyone else is gone. The only way out is the stairs exit, and its door wants a
four-digit code.

To escape you explore the floor's classrooms, labs, corridors and offices, and collect four
colour-coded digits. Each one is guarded by a boss with a quirk of its own: multiple-choice
quizzes, open questions you answer in your own words, timed questions and typing attacks. A wrong
answer costs a heart, and losing your last heart sends you back to your last save. Along the way an
Evil Backpack attaches itself to you, becomes your inventory, and comments on everything you do.

- **No commands to remember.** Every turn shows a short numbered list of what you can do right now.
- **Two ways to play.** A plain terminal version, and a Pygame window with hand-drawn room art, a
  floor map, music, typing sounds and a pause menu.
- **Accounts and saves.** Pick a name and a password, save mid-game (even mid-fight) and resume
  later.
- **An online leaderboard.** Finished runs are ranked by how much of the floor you completed, then
  by time. If you are offline, your run is uploaded later.

## Running it locally

You need **Python 3.12 or newer**. The terminal version uses only the standard library.

```bash
git clone https://github.com/andrii-kovalskyi02/a-maze-ing-delft.git
cd a-maze-ing-delft
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

Play in the terminal:

```bash
python main.py
```

Play in a window (recommended), which also needs Pygame:

```bash
pip install pygame-ce
python main_pygame.py
```

On Windows you can also double-click `run_game.bat`, which installs Pygame the first time and
starts the window version.

Other useful commands:

```bash
python play_room.py lab_2003            # start in one room to try it out; nothing is saved
pytest                                  # run the test suite
ruff check . && ruff format --check .   # lint and formatting, the same checks CI runs
```

### In a web browser

The same game also runs in the browser, built with [pygbag](https://pygame-web.github.io/):

```bash
python web/build.py --serve      # build it and play at http://localhost:8000
python web/build.py              # build only: upload build/web-src/build/web to any static host
```

In the browser, saves live in the browser's `localStorage`, and accounts and the leaderboard use
the browser's own `fetch` (see `browser.py`). Add `--offline` to build a version that never talks
to Supabase.

### Accounts, the leaderboard and Supabase

Accounts and the shared leaderboard run on [Supabase](https://supabase.com) (hosted Postgres).
Passwords never stay on a player's computer. They are sent over HTTPS to database functions that
hash them with bcrypt and lock a name after five wrong guesses in a row. Players can't read the
tables directly: row level security blocks it, and the game only calls those functions. See
[SCHEMA.md](SCHEMA.md) for the details.

To run the game against your own Supabase project:

1. Create a free project, then run `supabase/accounts.sql` and `supabase/scores.sql` in its SQL
   editor.
2. Put the project URL and its **public** (anon / publishable) key at the top of `cloud.py`.

Leave `SUPABASE_URL` in `cloud.py` empty to keep everything local: passwords are then hashed into
the local SQLite database instead, and the leaderboard only shows this computer's runs.

## How we worked

We built After Hours as a team of six over eight weeks using **Scrum**, the same way a product team
works in industry.

- **Sprints and reviews.** The work was split into three sprints. At the end of each one we
  demonstrated the game to our **product owner** at a sprint review and took their feedback into
  the next sprint's planning.
- **Weekly supervision.** We met our **supervisor** every week to review progress, blockers and
  technical decisions.
- **A real backlog.** Every room, feature and piece of technical work was a GitHub issue: user
  stories (`US1a`, `US1b`, ...), tasks under them, and enablers for shared engine work. We planned
  them on a [project board](https://github.com/users/andrii-kovalskyi02/projects/1) with one
  milestone per sprint. That came to more than 170 backlog items over the project.
- **Pull requests and CI.** All work reached `main` through pull requests from feature branches.
  GitHub Actions ran linting (ruff), formatting checks and the full pytest suite on Python 3.12
  and 3.14 for every pull request.
- **An architecture built for parallel work.** Rooms are pure data and one engine owns the game
  loop, so six people could build rooms at the same time without merge conflicts. A shared room
  contract test checks every room automatically, so nobody had to write tests for each room.

| Label | Meaning |
|---|---|
| `user-story` | A product backlog item: one per room (US1a, US1b, ...), plus US2-US5 |
| `task` | A sub-issue: concrete work under a user story |
| `enabler` | Technical work with no direct player-facing story (menu, world graph, quiz engine, persistence) |
| `process` | Scrum and course deliverables |
| `question` | An open design question for the team or the product owner |
| `area:blue` / `area:red` / `area:yellow` / `area:core` | Which part of the building, or the shared engine |

New contributors should start with [CONTRIBUTING.md](CONTRIBUTING.md).

## Tech stack

Python 3.12+, pygame-ce, SQLite, Supabase (Postgres, row level security, bcrypt via pgcrypto),
pytest, ruff, GitHub Actions.

## How the code is laid out

```
main.py          start the game in the terminal: pick a player, log in, play
main_pygame.py   run the same game inside a Pygame window
pygame_ui/       the Pygame window itself, one module per part (see its __init__.py)
play_room.py     start in one chosen room, to try it out; nothing is saved
run_game.bat     Windows: install Pygame if needed and start the window version
models.py        the data types a room is built from (Room, Item, Boss, ...)
world.py         the world graph: every room, and the locks between them
game.py          the one main loop, and everything true about a play-through
commands.py      the menu, and what each choice does
inventory.py     the item catalogue and what the player carries
encounters.py    running a boss's questions
digits.py        the four digits of the exit code, and the door that asks for them
health.py        the player's hearts, counted in halves
narrator.py      the Evil Backpack, talking over the game
memories.py      the details the Memory Keeper asks about at the end
accounts.py      registering a name and checking its password (on Supabase, or locally)
cloud.py         the connection to Supabase
browser.py       what is different in a web browser: fetch, and saves kept in localStorage
web/             the browser build: its start-up file and the build script
persistence.py   the local SQLite database: saved games and the scoreboard (see SCHEMA.md)
leaderboard/     the top 5 shown in the game, and the shared online one
supabase/        the SQL that sets up the Supabase project
profiles.py      which player names are allowed, and how a saved game is described
progress.py      completion % and play time, shared by status and the scoreboard
ui.py            all screen output, keyboard input, and the numbered menu
floor_map.py     the map: an ASCII plan of the 2nd floor showing where you are
music.py         background music for the Pygame window
assets/          pictures, fonts, music and sounds used by the Pygame window
rooms/           one file per room
tests/
  test_room_contract.py   runs against every registered room, automatically
  test_*.py               one file per engine module
```
