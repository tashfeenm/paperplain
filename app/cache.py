"""SQLite caching layer for paper explanations."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.models import PaperExplanation, PaperResponse, RecentPaper

DB_PATH = Path("data/cache.db")


def _get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the database if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            arxiv_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT NOT NULL,
            abstract TEXT NOT NULL,
            explanation TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def get(arxiv_id: str) -> PaperResponse | None:
    """Retrieve a cached paper explanation, or None if not found."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        ).fetchone()
        if row is None:
            return None
        return PaperResponse(
            arxiv_id=row["arxiv_id"],
            title=row["title"],
            authors=json.loads(row["authors"]),
            abstract=row["abstract"],
            explanation=PaperExplanation(**json.loads(row["explanation"])),
            arxiv_url=f"https://arxiv.org/abs/{row['arxiv_id']}",
            created_at=row["created_at"],
        )
    finally:
        conn.close()


def put(paper: PaperResponse) -> None:
    """Store a paper explanation in the cache."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO papers (arxiv_id, title, authors, abstract, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                paper.arxiv_id,
                paper.title,
                json.dumps(paper.authors),
                paper.abstract,
                json.dumps(paper.explanation.model_dump()),
                paper.created_at or datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_recent(limit: int = 20) -> list[RecentPaper]:
    """List recently explained papers."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT arxiv_id, title, created_at FROM papers ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            RecentPaper(
                arxiv_id=row["arxiv_id"],
                title=row["title"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    finally:
        conn.close()
