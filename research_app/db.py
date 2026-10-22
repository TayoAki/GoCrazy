import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DATA, DB_PATH, DEFAULT_SETTINGS

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    niche TEXT,
    keywords TEXT NOT NULL,          -- JSON list
    settings TEXT NOT NULL,          -- JSON object
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    status TEXT NOT NULL,            -- running | done | stopped | failed
    phase TEXT,
    progress REAL DEFAULT 0,
    message TEXT,
    credits_used INTEGER DEFAULT 0,
    stats TEXT,                      -- JSON object
    started_at TEXT NOT NULL,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS creators (
    username TEXT PRIMARY KEY,
    full_name TEXT,
    followers INTEGER,
    is_verified INTEGER,
    profile_fetched_at TEXT,
    reels_fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS project_creators (
    project_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    keywords TEXT NOT NULL,          -- JSON list of keywords that surfaced this creator
    status TEXT NOT NULL,            -- found | scanned | too_small | too_big | private | error
    PRIMARY KEY (project_id, username)
);
CREATE TABLE IF NOT EXISTS reels (
    shortcode TEXT PRIMARY KEY,
    username TEXT,
    url TEXT,
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    taken_at TEXT,
    caption TEXT,
    thumb_url TEXT,
    duration REAL,
    fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS outliers (
    project_id INTEGER NOT NULL,
    shortcode TEXT NOT NULL,
    ratio REAL NOT NULL,
    keyword TEXT,
    status TEXT NOT NULL DEFAULT 'new',   -- new | saved | dismissed
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, shortcode)
);
CREATE TABLE IF NOT EXISTS teardowns (
    shortcode TEXT PRIMARY KEY,
    status TEXT NOT NULL,            -- running | done | failed
    data TEXT,                       -- JSON teardown card
    error TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    level TEXT NOT NULL,             -- info | success | warning | error
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with connect() as conn:
        conn.executescript(SCHEMA)
        # A run left "running" by a server restart can never finish.
        conn.execute("UPDATE runs SET status='stopped', message='Server restarted', finished_at=? WHERE status='running'", (now(),))
        conn.execute("UPDATE teardowns SET status='failed', error='Server restarted' WHERE status='running'")


def log(project_id, level, message):
    with connect() as conn:
        conn.execute("INSERT INTO events (project_id, level, message, created_at) VALUES (?,?,?,?)",
                     (project_id, level, message, now()))


def project_settings(row):
    return {**DEFAULT_SETTINGS, **json.loads(row["settings"])}
