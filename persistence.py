"""Save and load game state, and keep the scoreboard, using SQLite (enabler #121).

Three tables - see SCHEMA.md:

- ``players``: who plays. One row per name, with that player's password, hashed.
- ``game_states``: one unfinished game per player, to resume later (US3).
- ``scores``: one finished run per player - their best - for the scoreboard (US5).

The functions below take a player's name, because names are unique: the database turns it
into the player's id itself.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import secrets
import sqlite3
from collections.abc import Iterator
from typing import TYPE_CHECKING

import browser

if TYPE_CHECKING:
    from game import Game


DATABASE_NAME = "game.db"

#: How long, in seconds, to wait for another copy of the game that is writing
#: at the same moment. SQLite lets one writer in at a time and makes the other
#: wait, so two players on one machine cannot corrupt the file.
BUSY_TIMEOUT = 5.0

#: How many times a password is hashed. Slow on purpose: somebody with a copy of game.db has to
#: wait this long for every password they guess.
HASH_ROUNDS = 100_000

_GAME_STATES = """
    CREATE TABLE IF NOT EXISTS game_states (
        player_id INTEGER PRIMARY KEY REFERENCES players(id),
        current_room TEXT NOT NULL,
        inventory TEXT NOT NULL,
        hearts INTEGER NOT NULL,
        digits TEXT NOT NULL,
        visited_rooms TEXT NOT NULL,
        unlocked_rooms TEXT NOT NULL,
        defeated_challenges TEXT NOT NULL,
        taken_items TEXT NOT NULL,
        approached TEXT NOT NULL,
        elapsed_time REAL NOT NULL,
        saved_at TEXT,
        in_question INTEGER
    )
"""

_SCORES = """
    CREATE TABLE IF NOT EXISTS scores (
        player_id INTEGER PRIMARY KEY REFERENCES players(id),
        percent INTEGER NOT NULL,
        seconds REAL NOT NULL,
        finished_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
"""


@contextlib.contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the game database for one job, in a ``with`` block.

    When the block ends the changes are saved (committed), or thrown away if it ended with an
    error, and the file is closed either way. Python's own ``with sqlite3.connect(...)`` commits
    but never closes, which is why this is here. In a web browser a changed file is also copied
    somewhere it lasts (see ``browser.py``).
    """
    connection = sqlite3.connect(DATABASE_NAME, timeout=BUSY_TIMEOUT)
    try:
        with connection:  # commits, or rolls back after an error
            yield connection
        changed = connection.total_changes > 0
    finally:
        connection.close()
    if changed:
        browser.keep_file(DATABASE_NAME)


def create_tables() -> None:
    """Create the players, save and scoreboard tables if they do not exist.

    In a web browser this first brings back the database from the last visit.
    """
    browser.restore_file(DATABASE_NAME)
    with connect() as connection:
        # salt and password_hash are empty for a player from before passwords existed. tag is
        # 8 random letters and digits, made by SQLite for every new player: it tells two players
        # with one name apart on the shared scoreboard, where names are not unique
        # (leaderboard/online.py)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                salt BLOB,
                password_hash BLOB,
                tag TEXT NOT NULL DEFAULT (lower(hex(randomblob(4)))),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        for table, create in (("game_states", _GAME_STATES), ("scores", _SCORES)):
            if "player_name" in _columns(connection, table):
                _move_to_player_ids(connection, table, create)
            else:
                connection.execute(create)
        # saves from before a game could be saved mid-question are not in a fight
        if "in_question" not in _columns(connection, "game_states"):
            connection.execute("ALTER TABLE game_states ADD COLUMN in_question INTEGER")

        # the shared scoreboard (leaderboard/online.py): runs waiting to be uploaded, and the last
        # top list seen
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_scores (
                run_id TEXT PRIMARY KEY,
                player_name TEXT NOT NULL,
                percent INTEGER NOT NULL,
                seconds REAL NOT NULL,
                player_tag TEXT
            )
            """
        )
        # runs waiting from before tags existed keep an empty tag
        if "player_tag" not in _columns(connection, "pending_scores"):
            connection.execute("ALTER TABLE pending_scores ADD COLUMN player_tag TEXT")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS online_top (
                place INTEGER PRIMARY KEY,
                player_name TEXT NOT NULL,
                percent INTEGER NOT NULL,
                seconds REAL NOT NULL
            )
            """
        )


def _columns(connection: sqlite3.Connection, table: str) -> list[str]:
    """Return the column names of ``table``; empty if there is no such table."""
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def _move_to_player_ids(connection: sqlite3.Connection, table: str, create: str) -> None:
    """Rebuild a table from before players existed, keyed by player_name, keyed by player_id.

    Every name in it becomes a player with no password yet, so old saves and scores are kept.
    """
    connection.execute(f"ALTER TABLE {table} RENAME TO old_{table}")
    connection.execute(create)
    # a column the old table never had (saved_at, in the oldest saves) is just left empty
    old_columns = _columns(connection, f"old_{table}")
    kept = ", ".join(column for column in old_columns if column != "player_name")
    connection.execute(f"INSERT OR IGNORE INTO players (name) SELECT player_name FROM old_{table}")
    connection.execute(
        f"INSERT OR IGNORE INTO {table} (player_id, {kept})"
        f" SELECT players.id, {kept} FROM old_{table}"
        f" JOIN players ON players.name = old_{table}.player_name"
    )
    connection.execute(f"DROP TABLE old_{table}")


def _player_id(connection: sqlite3.Connection, name: str) -> int:
    """Return ``name``'s id, adding them as a player with no password yet if they are new."""
    connection.execute("INSERT OR IGNORE INTO players (name) VALUES (?)", (name,))
    (player_id,) = connection.execute("SELECT id FROM players WHERE name = ?", (name,)).fetchone()
    return player_id


def _hash(password: str, salt: bytes) -> bytes:
    """Hash a password. The same password and salt always give the same hash."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ROUNDS)


def player_exists(name: str) -> bool:
    """Return True if ``name`` is taken - by a save or a score.

    A password alone does not take a name: a player who chose one and left without saving has
    nothing to protect, and is not in the "who is playing?" list either. The next person to pick
    that name starts afresh and chooses a new password.
    """
    with connect() as connection:
        row = connection.execute(
            "SELECT 1 FROM players WHERE name = ? AND ("
            " id IN (SELECT player_id FROM game_states) OR id IN (SELECT player_id FROM scores))",
            (name,),
        ).fetchone()
    return row is not None


def player_tag(name: str) -> str | None:
    """Return ``name``'s tag, which tells them apart from players with the same name elsewhere."""
    with connect() as connection:
        row = connection.execute("SELECT tag FROM players WHERE name = ?", (name,)).fetchone()
    return None if row is None else row[0]


def has_password(name: str) -> bool:
    """Return True if ``name`` has a password. Players from before passwords existed do not."""
    with connect() as connection:
        row = connection.execute(
            "SELECT 1 FROM players WHERE name = ? AND password_hash IS NOT NULL", (name,)
        ).fetchone()
    return row is not None


def set_password(name: str, password: str) -> None:
    """Give ``name`` a password, adding them as a player if they are new.

    Only a hash is kept, never the password. Each player gets their own random salt, so two
    players with the same password do not get the same hash.
    """
    salt = secrets.token_bytes(16)
    with connect() as connection:
        connection.execute(
            "UPDATE players SET salt = ?, password_hash = ? WHERE id = ?",
            (salt, _hash(password, salt), _player_id(connection, name)),
        )


def password_matches(name: str, password: str) -> bool:
    """Return True if ``password`` is ``name``'s password. False if they have none."""
    with connect() as connection:
        row = connection.execute(
            "SELECT salt, password_hash FROM players WHERE name = ?", (name,)
        ).fetchone()
    if row is None or row[1] is None:
        return False
    salt, stored = row
    # compare_digest takes as long whatever the answer, so timing gives nothing away
    return hmac.compare_digest(_hash(password, salt), stored)


def save_game(game: Game) -> None:
    """Save the complete state of a game."""
    inventory = [item.key for item in game.carrying]

    digits = [key for key in inventory if key.startswith("digit_")]

    taken_items = [[room, item] for room, item in game.taken]

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO game_states (
                player_id,
                current_room,
                inventory,
                hearts,
                digits,
                visited_rooms,
                unlocked_rooms,
                defeated_challenges,
                taken_items,
                approached,
                elapsed_time,
                in_question,
                saved_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(player_id) DO UPDATE SET
                current_room = excluded.current_room,
                inventory = excluded.inventory,
                hearts = excluded.hearts,
                digits = excluded.digits,
                visited_rooms = excluded.visited_rooms,
                unlocked_rooms = excluded.unlocked_rooms,
                defeated_challenges = excluded.defeated_challenges,
                taken_items = excluded.taken_items,
                approached = excluded.approached,
                elapsed_time = excluded.elapsed_time,
                in_question = excluded.in_question,
                saved_at = CURRENT_TIMESTAMP
            """,
            (
                _player_id(connection, game.player_name),
                game.current,
                json.dumps(inventory),
                game.hearts.halves,
                json.dumps(digits),
                json.dumps(sorted(game.visited)),
                json.dumps(sorted(game.unlocked)),
                json.dumps(sorted(game.defeated)),
                json.dumps(taken_items),
                json.dumps(sorted(game.approached)),
                game.elapsed_time,
                game.in_question,
            ),
        )


def load_game(player_name: str) -> Game | None:
    """Load a saved game for ``player_name`` if one exists."""
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                current_room,
                inventory,
                hearts,
                digits,
                visited_rooms,
                unlocked_rooms,
                defeated_challenges,
                taken_items,
                approached,
                elapsed_time,
                in_question
            FROM game_states
            JOIN players ON players.id = game_states.player_id
            WHERE players.name = ?
            """,
            (player_name,),
        ).fetchone()

    if row is None:
        return None

    from game import Game
    from health import Health

    (
        current_room,
        inventory_json,
        hearts,
        digits_json,
        visited_json,
        unlocked_json,
        defeated_json,
        taken_json,
        approached_json,
        elapsed_time,
        in_question,
    ) = row

    game = Game(
        player_name=player_name,
        current=current_room,
        hearts=Health(hearts),
        visited=set(json.loads(visited_json)),
        unlocked=set(json.loads(unlocked_json)),
        defeated=set(json.loads(defeated_json)),
        taken={(room, item) for room, item in json.loads(taken_json)},
        approached=set(json.loads(approached_json)),
        elapsed_time=elapsed_time,
        in_question=in_question,
    )

    from inventory import ITEM_CATALOGUE

    for item_key in json.loads(inventory_json):
        if item_key in ITEM_CATALOGUE:  # an item that no longer exists (an old save) is dropped
            game.carrying.add(item_key)

    return game


def delete_save(player_name: str) -> None:
    """Remove ``player_name``'s saved game, if there is one.

    Called when a game is finished, so the player cannot resume - and finish
    again - a run that is already on the scoreboard.
    """
    with connect() as connection:
        connection.execute(
            "DELETE FROM game_states WHERE player_id = (SELECT id FROM players WHERE name = ?)",
            (player_name,),
        )


def record_score(player_name: str, percent: int, seconds: float) -> None:
    """Put a finished run on the scoreboard, if it is the player's best (US5).

    Each player has one row: their best run. A new run replaces it only if it
    explored more of the floor, or the same amount in less time - the same
    order the scoreboard is sorted in.
    """
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO scores (player_id, percent, seconds)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                percent = excluded.percent,
                seconds = excluded.seconds,
                finished_at = CURRENT_TIMESTAMP
            WHERE excluded.percent > scores.percent
                OR (excluded.percent = scores.percent AND excluded.seconds < scores.seconds)
            """,
            (_player_id(connection, player_name), percent, seconds),
        )


def top_scores(limit: int = 5) -> list[tuple[str, int, float]]:
    """Return (name, percent, seconds) for the best players: highest % first, then fastest."""
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT players.name, percent, seconds
            FROM scores
            JOIN players ON players.id = scores.player_id
            ORDER BY percent DESC, seconds ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows


def add_pending_score(run_id: str, player_name: str, percent: int, seconds: float) -> None:
    """Remember a finished run, with the player's tag, until it is on the shared scoreboard."""
    with connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO pending_scores"
            " (run_id, player_name, player_tag, percent, seconds)"
            " VALUES (?, ?, (SELECT tag FROM players WHERE name = ?), ?, ?)",
            (run_id, player_name, player_name, percent, seconds),
        )


def pending_scores() -> list[tuple[str, str, str | None, int, float]]:
    """Return (run_id, name, tag, percent, seconds) for every run not uploaded yet."""
    with connect() as connection:
        rows = connection.execute(
            "SELECT run_id, player_name, player_tag, percent, seconds FROM pending_scores"
        ).fetchall()
    return rows


def delete_pending_score(run_id: str) -> None:
    """Forget a run once it is safely on the shared scoreboard."""
    with connect() as connection:
        connection.execute("DELETE FROM pending_scores WHERE run_id = ?", (run_id,))


def save_online_top(players: list[tuple[str, int, float]]) -> None:
    """Keep the shared scoreboard's top list, to show when there is no connection.

    Place -1 is a marker row saying "the list was fetched", so an empty board that was really
    fetched can be told apart from one that never was.
    """
    with connect() as connection:
        connection.execute("DELETE FROM online_top")
        connection.execute("INSERT INTO online_top VALUES (-1, '', 0, 0)")
        connection.executemany(
            "INSERT INTO online_top (place, player_name, percent, seconds) VALUES (?, ?, ?, ?)",
            [(place, *player) for place, player in enumerate(players)],
        )


def online_top() -> list[tuple[str, int, float]] | None:
    """Return (name, percent, seconds) from the last shared scoreboard seen, best first.

    None if no list has ever been fetched; an empty list means it was fetched and nobody is on it.
    """
    with connect() as connection:
        rows = connection.execute(
            "SELECT place, player_name, percent, seconds FROM online_top ORDER BY place"
        ).fetchall()
    if not rows:
        return None
    return [(name, percent, seconds) for place, name, percent, seconds in rows if place >= 0]


def recent_saves(limit: int) -> list[str]:
    """Return the names of the ``limit`` most recently saved games, newest first."""
    with connect() as connection:
        rows = connection.execute(
            "SELECT players.name FROM game_states"
            " JOIN players ON players.id = game_states.player_id"
            " ORDER BY saved_at DESC, players.name LIMIT ?",
            (limit,),
        ).fetchall()
    return [name for (name,) in rows]


def canonical_name(name: str) -> str:
    """Return the spelling already on file for ``name``, ignoring capital letters, or ``name``.

    "krug" and "Krug" are one player, so a save and a leaderboard row never split in two. The
    first spelling used wins, and the players keep seeing it.
    """
    with connect() as connection:
        rows = connection.execute("SELECT name FROM players").fetchall()
    wanted = name.casefold()
    for (known,) in sorted(rows):
        if known.casefold() == wanted:
            return known
    return name
