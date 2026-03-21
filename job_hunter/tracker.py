"""
tracker.py — SQLite Job Tracker
─────────────────────────────────
Tracks all jobs that have been shown to the candidate.
Prevents the same job appearing in multiple digests.
Stores application status for future tracking.
"""

from __future__ import annotations
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


DB_PATH = "./job_hunter/jobs_tracker.db"


def init_db() -> None:
    """Creates the database and tables if they don't exist."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT UNIQUE NOT NULL,
                title       TEXT,
                company     TEXT,
                source      TEXT,
                match_score REAL,
                first_seen  TEXT,
                status      TEXT DEFAULT 'seen'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_digests (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date   TEXT,
                jobs_found INTEGER,
                jobs_sent  INTEGER,
                created_at TEXT
            )
        """)
        conn.commit()


def filter_unseen_jobs(jobs: list[dict]) -> list[dict]:
    """
    Removes jobs that have been seen in the last 7 days.
    Returns only fresh, unseen jobs.
    """
    init_db()

    if not jobs:
        return []

    cutoff = (datetime.now() - timedelta(days=7)).strftime(
        "%Y-%m-%d"
    )

    with sqlite3.connect(DB_PATH) as conn:
        # Get all URLs seen in last 7 days
        cursor = conn.execute(
            "SELECT url FROM seen_jobs WHERE first_seen >= ?",
            (cutoff,)
        )
        seen_urls = {row[0] for row in cursor.fetchall()}

    # Return only jobs not in seen_urls
    fresh = [j for j in jobs if j.get("url", "") not in seen_urls]
    print(f"   ✓ {len(fresh)} fresh jobs "
          f"(filtered {len(jobs) - len(fresh)} already seen)")
    return fresh


def mark_jobs_as_seen(jobs: list[dict]) -> None:
    """Saves top 20 jobs to the tracker database."""
    init_db()

    if not jobs:
        return

    today = datetime.now().strftime("%Y-%m-%d")

    with sqlite3.connect(DB_PATH) as conn:
        for job in jobs:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO seen_jobs
                    (url, title, company, source, match_score, first_seen)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    job.get("url", ""),
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("source", ""),
                    job.get("match_score", 0.0),
                    today,
                ))
            except Exception:
                continue
        conn.commit()


def log_digest_run(jobs_found: int, jobs_sent: int) -> None:
    """Logs each digest run for analytics."""
    init_db()
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO daily_digests
            (run_date, jobs_found, jobs_sent, created_at)
            VALUES (?, ?, ?, ?)
        """, (today, jobs_found, jobs_sent, today))
        conn.commit()


def get_stats() -> dict:
    """Returns tracker statistics."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM seen_jobs"
        ).fetchone()[0]
        runs = conn.execute(
            "SELECT COUNT(*) FROM daily_digests"
        ).fetchone()[0]
        return {"total_jobs_tracked": total, "total_runs": runs}