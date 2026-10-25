"""Local copies of covers and teardown frames. Instagram CDN links expire, so they are fetched once and served locally."""

import re
import subprocess
from pathlib import Path

import requests
from PIL import Image

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


def save_cover(url, shortcode):
    """Download a cover and keep it only if it opens as an image, saved as JPEG (TikTok can serve HEIC, which browsers
    and Pillow can't show)."""
    dest = media_dir(shortcode) / "cover.jpg"
    if not download(url, dest):
        return False
    try:
        im = Image.open(dest)
        if im.format != "JPEG":
            im.convert("RGB").save(dest, "JPEG", quality=85)
        return True
    except OSError:
        dest.unlink(missing_ok=True)
        return False


def download_covers(shortcodes):
    """Covers for reels that aren't outliers (e.g. a doubled-down account's template examples)."""
    if not shortcodes:
        return
    with db.connect() as conn:
        rows = conn.execute(f"SELECT shortcode, thumb_url FROM reels WHERE thumb_url IS NOT NULL AND shortcode IN "
                            f"({','.join('?' * len(shortcodes))})", list(shortcodes)).fetchall()
    for row in rows:
        if not cover_path(row["shortcode"]).exists():
            save_cover(row["thumb_url"], row["shortcode"])


def download_missing_covers(project_id):
    with db.connect() as conn:
        rows = conn.execute("""SELECT r.shortcode, r.thumb_url FROM outliers o JOIN reels r ON r.shortcode = o.shortcode
                               WHERE o.project_id=? AND r.thumb_url IS NOT NULL""", (project_id,)).fetchall()
    for row in rows:
        if not cover_path(row["shortcode"]).exists():
            save_cover(row["thumb_url"], row["shortcode"])


def analyze_video(video_url, shortcode, duration=None):
    """Download the reel, keep small hook/overview/scene frames for review, find the hard cuts, then delete the video.

    Frames stay on this machine for human review only; the video file itself is never kept (playbook rule 13).
    """
    out = media_dir(shortcode)
    video = out / "_video.mp4"
    result = {"hook_frames": [], "frames": [], "cuts": None, "avg_shot_s": None, "scenes": []}
    if not download(video_url, video):
        result["error"] = "Could not download the video"
        return result
    try:
        for old in list(out.glob("hook_*.jpg")) + list(out.glob("f_*.jpg")) + list(out.glob("s_*.jpg")):
            old.unlink()
        run = lambda *args: subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], capture_output=True, text=True, timeout=300)
        run("-i", str(video), "-t", "3", "-vf", "fps=2,scale=360:-2", str(out / "hook_%02d.jpg"))
        # About 15 overview frames whatever the length: dense for short reels, sparse (max 1 per 2 s) for long ones.
        fps = min(2.0, max(0.5, 15 / duration)) if duration else 0.5
        run("-i", str(video), "-vf", f"fps={fps:.3f},scale=220:-2", "-frames:v", "60", str(out / "f_%03d.jpg"))
        cuts, scenes = detect_scenes(video, duration)
        result["cuts"] = len(cuts)
        # Frames from each scene so motion shows: one in a flash, otherwise a quarter and three quarters in.
        for k, sc in enumerate(scenes, 1):
            length = sc["end"] - sc["start"]
            names = []
            for n, f in enumerate((0.5,) if length < 1.0 else (0.25, 0.75)):
                name = f"s_{k:02d}{'ab'[n]}.jpg"
                run("-ss", f"{sc['start'] + length * f:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2", str(out / name))
                if (out / name).exists():
                    names.append(name)
            result["scenes"].append({**sc, "frames": names})
        result["hook_frames"] = sorted(p.name for p in out.glob("hook_*.jpg"))
        result["frames"] = sorted(p.name for p in out.glob("f_*.jpg"))
    finally:
        video.unlink(missing_ok=True)
    return result


def detect_scenes(video, duration=None, max_scenes=30, min_len=0.3, max_len=6.0):
    """Hard cuts (seconds) and scenes as {start, end, flash_cuts, cut}.

    Flashes shorter than min_len merge into their shorter neighbour, so a strobe reads as one scene with N flash cuts.
    Holds longer than max_len split into ~5 s segments with cut=False (the same shot continues), because a green-screen
    background swap or a speaker changing sides rarely registers as a hard cut. At most max_scenes in all.
    """
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                           capture_output=True, text=True, timeout=60)
    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        pass
    scene = subprocess.run(["ffmpeg", "-i", str(video), "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=300)
    cuts = sorted(float(t) for t in re.findall(r"pts_time:([\d.]+)", scene.stderr))
    if not duration:
        return cuts, []
    bounds = [0.0] + [c for c in cuts if 0 < c < duration] + [duration]
    shots = [[a, b, 0] for a, b in zip(bounds, bounds[1:]) if b > a]
    length = lambda k: shots[k][1] - shots[k][0]
    while len(shots) > 1 and min(map(length, range(len(shots)))) < min_len:
        i = min(range(len(shots)), key=length)
        j = i - 1 if i == len(shots) - 1 or (i > 0 and length(i - 1) < length(i + 1)) else i + 1
        lo, hi = min(i, j), max(i, j)
        shots[lo:hi + 1] = [[shots[lo][0], shots[hi][1], shots[lo][2] + shots[hi][2] + 1]]
    seg = max(5.0, duration / max_scenes)
    scenes = []
    for a, b, flashes in shots:
        parts = max(1, round((b - a) / seg)) if b - a > max_len else 1
        step = (b - a) / parts
        scenes += [{"start": round(a + step * n, 2), "end": round(a + step * (n + 1), 2), "flash_cuts": flashes if n == 0 else 0,
                    "cut": n == 0} for n in range(parts)]
    return cuts, scenes[:max_scenes]
