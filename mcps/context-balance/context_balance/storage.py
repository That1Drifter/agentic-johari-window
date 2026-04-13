"""SQLite event store for context-balance."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schemas import EventType, StoredEvent


class EventStore:
    """Stores retrieval, pruning, and quality events in SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path.home() / ".context-balance" / "events.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                data TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_session
                ON events(session_id, sequence);
            CREATE INDEX IF NOT EXISTS idx_events_type
                ON events(session_id, event_type);
        """)
        self.conn.commit()

    def add_event(self, event_type: EventType, session_id: str, data: dict) -> StoredEvent:
        """Add an event and return it with its assigned ID and sequence number."""
        # Get next sequence number for this session
        row = self.conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 as next_seq FROM events WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        next_seq = row["next_seq"]

        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            "INSERT INTO events (event_type, timestamp, session_id, sequence, data) VALUES (?, ?, ?, ?, ?)",
            (event_type.value, now, session_id, next_seq, json.dumps(data)),
        )
        self.conn.commit()

        return StoredEvent(
            id=cursor.lastrowid,
            event_type=event_type,
            timestamp=datetime.fromisoformat(now),
            session_id=session_id,
            sequence=next_seq,
            data=data,
        )

    def get_events(
        self,
        session_id: str,
        event_type: Optional[EventType] = None,
        last_n: Optional[int] = None,
    ) -> list[StoredEvent]:
        """Retrieve events for a session, optionally filtered by type and limited."""
        query = "SELECT * FROM events WHERE session_id = ?"
        params: list = [session_id]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        query += " ORDER BY sequence ASC"

        if last_n:
            query += " LIMIT ?"
            params.append(last_n)

        rows = self.conn.execute(query, params).fetchall()
        return [
            StoredEvent(
                id=row["id"],
                event_type=EventType(row["event_type"]),
                timestamp=datetime.fromisoformat(row["timestamp"]),
                session_id=row["session_id"],
                sequence=row["sequence"],
                data=json.loads(row["data"]),
            )
            for row in rows
        ]

    def get_event_count(self, session_id: str) -> dict[str, int]:
        """Count events by type for a session."""
        rows = self.conn.execute(
            "SELECT event_type, COUNT(*) as cnt FROM events WHERE session_id = ? GROUP BY event_type",
            (session_id,),
        ).fetchall()
        counts = {et.value: 0 for et in EventType}
        for row in rows:
            counts[row["event_type"]] = row["cnt"]
        return counts

    def close(self):
        self.conn.close()
