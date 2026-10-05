import sqlite3
from typing import Optional

DB_PATH = "bot_data.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL UNIQUE,
                channel_id TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                title TEXT NOT NULL,
                event_type TEXT NOT NULL,
                date_time TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                event_id INTEGER,
                user_id TEXT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (event_id, user_id),
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def create_event(
    message_id: int,
    channel_id: int,
    creator_id: str,
    title: str,
    event_type: str,
    date_time: str,
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO events (message_id, channel_id, creator_id, title, event_type, date_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                str(message_id),
                str(channel_id),
                creator_id,
                title,
                event_type,
                date_time,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_event_by_message_id(message_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM events WHERE message_id = ?", (str(message_id),)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def add_participant(event_id: int, user_id: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO participants (event_id, user_id)
            VALUES (?, ?)
        """,
            (event_id, str(user_id)),
        )
        conn.commit()


def remove_participant(event_id: int, user_id: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM participants
            WHERE event_id = ? AND user_id = ?
        """,
            (event_id, str(user_id)),
        )
        conn.commit()


def get_participants(event_id: int) -> list[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id FROM participants
            WHERE event_id = ?
            ORDER BY joined_at ASC
        """,
            (event_id,),
        )
        rows = cursor.fetchall()
        return [row["user_id"] for row in rows]


def delete_event(event_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM participants WHERE event_id = ?", (event_id,)
        )
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
