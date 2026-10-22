"""Backup and restore of everything the app keeps: the SQLite database and the media folder, as one .tar.gz.

Used to move research between machines, e.g. from a laptop to a Railway deployment.
"""

import shutil
import sqlite3
import tarfile
import tempfile
import time
from pathlib import Path

from . import db, pipeline, planner
from .config import DATA, DB_PATH, MEDIA


def busy():
    """Why a restore can't run right now, or None."""
    if pipeline._stop_flags:
        return "A research run is in progress."
    if planner._running:
        return "A plan is being generated."
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM teardowns WHERE status='running'").fetchone():
            return "A teardown is in progress."
    return None


def make_backup():
    """Write a consistent backup to a new temp folder. Returns (folder, archive path); the caller deletes the folder."""
    folder = Path(tempfile.mkdtemp(prefix="backup_", dir=DATA))
    copy = folder / "research.db"
    src, dst = sqlite3.connect(DB_PATH), sqlite3.connect(copy)
    with dst:
        src.backup(dst)  # safe while the app is writing, unlike copying the file
    src.close()
    dst.close()
    archive = folder / f"outlier-research-{time.strftime('%Y-%m-%d')}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(copy, arcname="research.db")
        if MEDIA.exists():
            tar.add(MEDIA, arcname="media")
    copy.unlink()
    return folder, archive


def restore(archive):
    """Replace the database and media with the archive's. Returns what the restored database holds."""
    reason = busy()
    if reason:
        raise RuntimeError(reason + " Wait for it to finish, then restore.")
    work = Path(tempfile.mkdtemp(prefix="restore_", dir=DATA))
    try:
        with tarfile.open(archive, "r:gz") as tar:
            members = [m for m in tar.getmembers() if (m.isfile() or m.isdir())
                       and (m.name == "research.db" or m.name == "media" or m.name.startswith("media/"))]
            tar.extractall(work, members=members, filter="data")
        new_db = work / "research.db"
        if not new_db.exists():
            raise RuntimeError("That file isn't a backup from this app: it has no research.db.")
        with sqlite3.connect(new_db) as conn:
            counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("projects", "outliers", "teardowns", "plans")}
        # Swap: keep the old data aside until the new data is in place.
        old = work / "old"
        old.mkdir()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(DB_PATH) + suffix)
            if path.exists():
                shutil.move(path, old / path.name)
        if MEDIA.exists():
            shutil.move(MEDIA, old / "media")
        shutil.move(new_db, DB_PATH)
        if (work / "media").exists():
            shutil.move(work / "media", MEDIA)
        else:
            MEDIA.mkdir(parents=True)
        db.init()
        return counts
    finally:
        shutil.rmtree(work, ignore_errors=True)
