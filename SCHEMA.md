# The database (enabler #121)

The game keeps everything it has to remember in one SQLite file, `game.db`,
next to `main.py`. All the code that reads or writes it is in `persistence.py`.

## Why SQLite

It comes with Python, so nobody installs anything. The whole database is one
file. It survives the program closing, which is what US3 (pause and resume)
and US5 (the scoreboard) both need. And it is a real SQL database, so ordering
the scoreboard is one query instead of code we write and test ourselves.

## Two tables, for two different things

An unfinished game and a finished one are different things. An unfinished
game has to be resumed exactly, so it holds everything. A finished run only has
to be ranked, so it holds three numbers. Keeping them apart means finishing a
game can never be resumed by mistake, and the scoreboard never shows a game
somebody is still playing.

### `game_states` - one unfinished game per player (US3)

| Column | Type | What it holds |
|---|---|---|
| `player_name` | TEXT, **primary key** | The name typed at the start. One save per name |
| `current_room` | TEXT | The key of the room the player is in |
| `inventory` | TEXT (JSON list) | The keys of the items carried |
| `hearts` | INTEGER | Hearts left, counted in halves (3 hearts = 6) |
| `digits` | TEXT (JSON list) | The exit code digits carried |
| `visited_rooms` | TEXT (JSON list) | Rooms walked into |
| `unlocked_rooms` | TEXT (JSON list) | Doors already opened, so a used-up key is not needed again |
| `defeated_challenges` | TEXT (JSON list) | Bosses resolved - a beaten boss stays beaten |
| `taken_items` | TEXT (JSON list of pairs) | `[room, item]` for every item picked up |
| `approached` | TEXT (JSON list) | Encounters the player has walked up to |
| `elapsed_time` | REAL | Seconds played in earlier sessions |

Written by `save_game()` (Options -> Save, or typing `pause`), read by
`load_game()` when the player gives their name, and deleted by `delete_save()`
when they finish.

The sets (visited, defeated, ...) are Python `set`s in the game, because the
game only ever asks "is this room in it?". SQLite has no set type, so they are
stored as JSON lists and turned back into sets on loading.

### `scores` - each player's best finished run (US5)

| Column | Type | What it holds |
|---|---|---|
| `player_name` | TEXT, **primary key** | One row per player: their best run |
| `percent` | INTEGER | How much of the floor was done, 0-100 |
| `seconds` | REAL | Total play time, every session included |
| `finished_at` | TEXT | When that run finished (filled in by SQLite) |

Written by `record_score()` when the player walks out of the building. A new
run replaces the old one only if it is better - more of the floor, or the same
amount faster.

The scoreboard is one query, in `top_scores()`:

```sql
SELECT player_name, percent, seconds
FROM scores
ORDER BY percent DESC, seconds ASC
LIMIT 5
```

### The shared scoreboard (`leaderboard/online.py`)

Optional. When `SUPABASE_URL` and `SUPABASE_KEY` are filled in at the top of `leaderboard/online.py`, finished
runs are also uploaded to a `scores` table on Supabase (create it with `leaderboard/scores_online.sql`), and
the scoreboard shows everyone's best five. Two more local tables back this up:

| Table | What it holds |
|---|---|
| `pending_scores` | Finished runs not uploaded yet (no connection); sent the next time the server answers |
| `online_top` | The last top list seen, shown when the server cannot be reached |

## Two copies of the game at once

Each function opens the file, does one thing, commits and closes. SQLite lets
only one writer in at a time; anyone else waits up to `BUSY_TIMEOUT` (5
seconds) for their turn rather than writing over them. So two players on the
same machine cannot corrupt the file.
