import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "travel_planner.db"


def _connect():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            source_city TEXT,
            destination TEXT,
            num_days INTEGER,
            budget REAL,
            travellers INTEGER,
            hotel_preference TEXT,
            interests TEXT,
            trip_json TEXT NOT NULL,
            pdf_path TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_trip(user_name: str, request: dict, itinerary: dict, pdf_path: str = "") -> int:
    conn = _connect()
    cur = conn.execute(
        """INSERT INTO trips
           (user_name, source_city, destination, num_days, budget, travellers,
            hotel_preference, interests, trip_json, pdf_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_name,
            request.get("source_city", ""),
            request.get("destination", ""),
            request.get("num_days", 0),
            request.get("budget", 0),
            request.get("num_travellers", 0),
            request.get("hotel_preference", "standard"),
            json.dumps(request.get("interests", [])),
            json.dumps({"request": request, "itinerary": itinerary}, default=str),
            pdf_path,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    trip_id = cur.lastrowid
    conn.close()
    return trip_id


def load_trips(user_name: str) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM trips WHERE user_name = ? ORDER BY created_at DESC",
        (user_name,),
    ).fetchall()
    conn.close()
    results = []
    for row in rows:
        data = json.loads(row["trip_json"])
        data["id"] = row["id"]
        data["pdf_path"] = row["pdf_path"] or ""
        data["created_at"] = row["created_at"]
        results.append(data)
    return results


def load_trip_by_id(trip_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
    conn.close()
    if not row:
        return None
    data = json.loads(row["trip_json"])
    data["id"] = row["id"]
    data["pdf_path"] = row["pdf_path"] or ""
    data["created_at"] = row["created_at"]
    return data


def delete_trip(trip_id: int) -> bool:
    conn = _connect()
    cur = conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


init_db()
