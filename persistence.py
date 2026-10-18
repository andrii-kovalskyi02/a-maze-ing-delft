"""Save and load game state, and keep the scoreboard, using SQLite (enabler #121).

Two tables, because they hold two different things - see SCHEMA.md:

- ``game_states``: one unfinished game per player, to resume later (US3).
- ``scores``: one finished run per player - their best - for the scoreboard (US5).
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game


DATABASE_NAME = "game.db"

#: How long, in seconds, to wait for another copy of the game that is writing
#: at the same moment. SQLite lets one writer in at a time and makes the other
#: wait, so two players on one machine cannot corrupt the file.
BUSY_TIMEOUT = 5.0


def get_connection() -> sqlite3.Connection:
    """Return a connection to the game database."""
    return sqlite3.connect(DATABASE_NAME, timeout=BUSY_TIMEOUT)


def create_tables() -> None:
    """Create the save table and the scoreboard table if they do not exist."""
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS game_states (
            player_name TEXT PRIMARY KEY,
            current_room TEXT NOT NULL,
            inventory TEXT NOT NULL,
            hearts INTEGER NOT NULL,
            digits TEXT NOT NULL,
            visited_rooms TEXT NOT NULL,
            unlocked_rooms TEXT NOT NULL,
            defeated_challenges TEXT NOT NULL,
            taken_items TEXT NOT NULL,
            approached TEXT NOT NULL,
            elapsed_time REAL NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            player_name TEXT PRIMARY KEY,
            percent INTEGER NOT NULL,
            seconds REAL NOT NULL,
            finished_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def save_game(game: Game) -> None:
    """Save the complete state of a game."""
    inventory = [item.key for item in game.carrying]

    digits = [key for key in inventory if key.startswith("digit_")]

    taken_items = [[room, item] for room, item in game.taken]

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO game_states (
            player_name,
            current_room,
            inventory,
            hearts,
            digits,
            visited_rooms,
            unlocked_rooms,
            defeated_challenges,
            taken_items,
            approached,
            elapsed_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_name) DO UPDATE SET
            current_room = excluded.current_room,
            inventory = excluded.inventory,
            hearts = excluded.hearts,
            digits = excluded.digits,
            visited_rooms = excluded.visited_rooms,
            unlocked_rooms = excluded.unlocked_rooms,
            defeated_challenges = excluded.defeated_challenges,
            taken_items = excluded.taken_items,
            approached = excluded.approached,
            elapsed_time = excluded.elapsed_time
        """,
        (
            game.player_name,
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
        ),
    )

    connection.commit()
    connection.close()


def load_game(player_name: str) -> Game | None:
    """Load a saved game for ``player_name`` if one exists."""
    connection = get_connection()

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
            elapsed_time
        FROM game_states
        WHERE player_name = ?
        """,
        (player_name,),
    ).fetchone()

    connection.close()

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
    connection = get_connection()
    connection.execute("DELETE FROM game_states WHERE player_name = ?", (player_name,))
    connection.commit()
    connection.close()


def record_score(player_name: str, percent: int, seconds: float) -> None:
    """Put a finished run on the scoreboard, if it is the player's best (US5).

    Each player has one row: their best run. A new run replaces it only if it
    explored more of the floor, or the same amount in less time - the same
    order the scoreboard is sorted in.
    """
    connection = get_connection()
    connection.execute(
        """
        INSERT INTO scores (player_name, percent, seconds)
        VALUES (?, ?, ?)
        ON CONFLICT(player_name) DO UPDATE SET
            percent = excluded.percent,
            seconds = excluded.seconds,
            finished_at = CURRENT_TIMESTAMP
        WHERE excluded.percent > scores.percent
            OR (excluded.percent = scores.percent AND excluded.seconds < scores.seconds)
        """,
        (player_name, percent, seconds),
    )
    connection.commit()
    connection.close()


def top_scores(limit: int = 5) -> list[tuple[str, int, float]]:
    """Return (name, percent, seconds) for the best players: highest % first, then fastest."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT player_name, percent, seconds
        FROM scores
        ORDER BY percent DESC, seconds ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    connection.close()
    return rows
