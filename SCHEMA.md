# The database (enabler #121)

The game keeps everything it has to remember in one SQLite file, `game.db`,
next to `main.py`. All the code that reads or writes it is in `persistence.py`.

## Why SQLite

It comes with Python, so nobody installs anything. The whole database is one
file. It survives the program closing, which is what US3 (pause and resume)
and US5 (the scoreboard) both need. And it is a real SQL database, so ordering
the scoreboard is one query instead of code we write and test ourselves.

## Who is playing: `players`

| Column | Type | What it holds |
|---|---|---|
| `id` | INTEGER, **primary key** | The player's number. Saves and scores point at this, not at the name |
| `name` | TEXT, **unique**, ignoring capitals | The name typed at the start. Two players can never share one |
| `salt` | BLOB | Only without Supabase: random bytes, different for every player, mixed into the hash |
| `password_hash` | BLOB | Only without Supabase: the password, hashed (PBKDF2-SHA256) |
| `tag` | TEXT | 8 random letters and digits, made by SQLite. Tells two players with one name apart online |
| `created_at` | TEXT | When the name was first used (filled in by SQLite) |

A new name chooses a password (`set_password()`). A taken name - one with a save or a score - needs
its password (`password_matches()`) before anyone can play as it. Because names are unique, the
scoreboard never shows two players with the same name. A password on its own does not take a name
(`player_exists()`): a player who chose one and quit without saving is in no list, so the next
person to pick that name starts afresh and their new password replaces the old one.

Keeping the player apart from their save and score means the name lives in one place only.

Only a hash is stored. Each player gets their own salt, so two players with the same password get
different hashes, and checking a password is slow on purpose (`HASH_ROUNDS`), so guessing passwords
from a copied `game.db` is slow too. This protects one player's save from another player. It is not
strong security: anyone can open `game.db` and edit it. A forgotten password cannot be recovered;
the player picks a new name.

A database from before passwords existed is updated by `create_tables()`: every name in it becomes a
player with no password (`salt` and `password_hash` empty), and the first person to come back as
that name chooses its password.

## Saves and scores: two tables, for two different things

An unfinished game and a finished one are different things. An unfinished
game has to be resumed exactly, so it holds everything. A finished run only has
to be ranked, so it holds three numbers. Keeping them apart means finishing a
game can never be resumed by mistake, and the scoreboard never shows a game
somebody is still playing.

### `game_states` - one unfinished game per player (US3)

| Column | Type | What it holds |
|---|---|---|
| `player_id` | INTEGER, **primary key** | The player (`players.id`). One save per player |
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
| `in_question` | INTEGER | The boss question (from 0) being asked when the game was saved, or empty outside a fight. The game resumes straight on that question |

Written by `save_game()` (Options -> Save, or typing `pause`), read by
`load_game()` once the player has logged in, and deleted by `delete_save()`
when they finish.

The sets (visited, defeated, ...) are Python `set`s in the game, because the
game only ever asks "is this room in it?". SQLite has no set type, so they are
stored as JSON lists and turned back into sets on loading.

### `scores` - each player's best finished run (US5)

| Column | Type | What it holds |
|---|---|---|
| `player_id` | INTEGER, **primary key** | The player (`players.id`). One row per player: their best run |
| `percent` | INTEGER | How much of the floor was done, 0-100 |
| `seconds` | REAL | Total play time, every session included |
| `finished_at` | TEXT | When that run finished (filled in by SQLite) |

Written by `record_score()` when the player walks out of the building. A new
run replaces the old one only if it is better - more of the floor, or the same
amount faster.

The scoreboard is one query, in `top_scores()`:

```sql
SELECT players.name, percent, seconds
FROM scores
JOIN players ON players.id = scores.player_id
ORDER BY percent DESC, seconds ASC
LIMIT 5
```

### The shared scoreboard (`leaderboard/online.py`)

Optional. When `SUPABASE_URL` and `SUPABASE_KEY` are filled in at the top of `cloud.py`, finished
runs are also uploaded to a `scores` table on Supabase (create it with `supabase/scores.sql`), and
the scoreboard shows everyone's best five. Two more local tables back this up:

| Table | What it holds |
|---|---|
| `pending_scores` | Finished runs not uploaded yet (no connection); sent the next time the server answers |
| `online_top` | The last top list seen, shown when the server cannot be reached |

Names are registered online now (see below), but runs from before that can share a name. So every uploaded run
carries its player's `tag` (`player_tag` on Supabase). When two different players with one name are
both in the top five, the first four letters of their tags are shown after the name: `Kru #a3f9`
and `Kru #07bc`. The tag is random rather than made from the name, because a hash of the name would
be the same for both "Kru"s. A Supabase table made before tags existed needs the column added once
(the `alter table` line at the bottom of `supabase/scores.sql`) before this version of the game uploads.

### Accounts online (`accounts.py`)

When Supabase is set up, passwords are not kept in `game.db` at all. A name is registered in a
`players` table on Supabase (create it with `supabase/accounts.sql`), so it is the same player on
every computer and nobody else can take it.

| Column | Type | What it holds |
|---|---|---|
| `name` | text, **primary key**, unique ignoring capitals | The player's name |
| `password_hash` | text | The password, hashed with bcrypt on the server |
| `failed_attempts` | int | Wrong passwords in a row |
| `locked_until` | timestamptz | Set for a minute after five wrong passwords in a row |
| `created_at` | timestamptz | When the name was registered |

Row level security is on with no policies, so the table cannot be read or written with the public
key. The game only calls three database functions, which run with the table owner's rights:

| Function | What it does |
|---|---|
| `player_exists(player_name)` | Whether the name is registered |
| `register_player(player_name, password)` | Registers the name; false if it is taken |
| `check_password(player_name, password)` | `'ok'`, `'wrong'`, or `'locked'` |

The password itself travels to the server over HTTPS and is never stored anywhere in plain text.
If the server cannot be reached, the game says so and asks for a name again: a password that cannot
be checked is not accepted. Without Supabase the local `salt` and `password_hash` columns described
above are used instead.

## Two copies of the game at once

Each function opens the file, does one thing, commits and closes. SQLite lets
only one writer in at a time; anyone else waits up to `BUSY_TIMEOUT` (5
seconds) for their turn rather than writing over them. So two players on the
same machine cannot corrupt the file.
