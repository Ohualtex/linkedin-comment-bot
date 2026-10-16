"""SQLite storage module to track commented posts and prevent duplicates."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator

from config import DB_PATH


@contextmanager
def get_db(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections that guarantees clean closing."""
    target_path = Path(db_path or DB_PATH)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """Initializes the database schema if it doesn't already exist."""
    with get_db(db_path) as conn:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS commented_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_urn TEXT UNIQUE NOT NULL,
                    post_url TEXT,
                    author TEXT,
                    comment_text TEXT,
                    commented_at TIMESTAMP NOT NULL
                );
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_post_urn ON commented_posts(post_urn);
                """
            )


def is_post_commented(post_urn: str, db_path: Optional[Path] = None) -> bool:
    """Checks whether a post has already been commented on."""
    init_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM commented_posts WHERE post_urn = ? LIMIT 1;",
            (post_urn.strip(),),
        )
        return cursor.fetchone() is not None


def record_comment(
    post_urn: str,
    post_url: str,
    comment_text: str,
    author: str = "",
    db_path: Optional[Path] = None,
) -> None:
    """Records a new comment into the database."""
    init_db(db_path)
    now = datetime.utcnow().isoformat()
    with get_db(db_path) as conn:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO commented_posts
                (post_urn, post_url, author, comment_text, commented_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (post_urn.strip(), post_url.strip(), author.strip(), comment_text.strip(), now),
            )


def get_commented_count(db_path: Optional[Path] = None) -> int:
    """Returns the total number of commented posts stored in the database."""
    init_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM commented_posts;")
        row = cursor.fetchone()
        return row[0] if row else 0


def get_recent_comments(limit: int = 10, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves the most recent commented posts."""
    init_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT post_urn, post_url, author, comment_text, commented_at
            FROM commented_posts
            ORDER BY id DESC
            LIMIT ?;
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
