"""Local copies of covers and teardown frames. Instagram CDN links expire, so they are fetched once and served locally."""

import subprocess
from pathlib import Path

import requests

from . import db
from .config import MEDIA

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def media_dir(shortcode):
    d = MEDIA / shortcode
    d.mkdir(parents=True, exist_ok=True)
    return d


def cover_path(shortcode):
    return MEDIA / shortcode / "cover.jpg"


def download(url, dest):
    try:
        with requests.get(url, headers=UA, timeout=60, stream=True) as r:
            if r.status_code != 200:
                return False
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
        return True
    except requests.RequestException:
        return False


def download_missing_covers(project_id):
    with db.connect() as conn:
        rows = conn.execute("""SELECT r.shortcode, r.thumb_url FROM outliers o JOIN reels r ON r.shortcode = o.shortcode
                               WHERE o.project_id=? AND r.thumb_url IS NOT NULL""", (project_id,)).fetchall()
    for row in rows:
        if not cover_path(row["shortcode"]).exists():
            download(row["thumb_url"], media_dir(row["shortcode"]) / "cover.jpg")


def analyze_video(video_url, shortcode, duration=None):
    """Download the reel, keep small hook/overview frames for review, count hard cuts, then delete the video.

    Frames stay on this machine for human review only; the video file itself is never kept (playbook rule 13).
    """
    out = media_dir(shortcode)
    video = out / "_video.mp4"
    result = {"hook_frames": [], "frames": [], "cuts": None, "avg_shot_s": None}
    if not download(video_url, video):
        result["error"] = "Could not download the video"
        return result
    try:
        for old in list(out.glob("hook_*.jpg")) + list(out.glob("f_*.jpg")):
            old.unlink()
        run = lambda *args: subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], capture_output=True, text=True, timeout=300)
        run("-i", str(video), "-t", "3", "-vf", "fps=2,scale=360:-2", str(out / "hook_%02d.jpg"))
        # About 15 overview frames whatever the length: dense for short reels, sparse (max 1 per 2 s) for long ones.
        fps = min(2.0, max(0.5, 15 / duration)) if duration else 0.5
        run("-i", str(video), "-vf", f"fps={fps:.3f},scale=220:-2", "-frames:v", "60", str(out / "f_%03d.jpg"))
        scene = subprocess.run(["ffmpeg", "-i", str(video), "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"],
                               capture_output=True, text=True, timeout=300)
        result["cuts"] = scene.stderr.count("pts_time:")
        result["hook_frames"] = sorted(p.name for p in out.glob("hook_*.jpg"))
        result["frames"] = sorted(p.name for p in out.glob("f_*.jpg"))
    finally:
        video.unlink(missing_ok=True)
    return result
