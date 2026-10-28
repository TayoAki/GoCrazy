"""Shared helpers for reel.py and match.py: probing a video, and calling vision.py (transcription, face finding,
person cut-out) in the skill's own Python environment, which is made on first use.

The environment lives at ~/.cache/slideshow-content/venv (Python 3.11 with faster-whisper and MediaPipe, about
1.3 GB). It's made with uv when uv is installed, otherwise with python3.11's venv and pip. Whisper's model downloads
on its first use (about 500 MB). Results are cached in the post's out/work/ folder, keyed by the source file.
"""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
VENV = Path(os.environ.get("SLIDESHOW_VENV") or Path.home() / ".cache/slideshow-content/venv")
VISION = Path(__file__).resolve().parent / "vision.py"
PACKAGES = ["faster-whisper", "mediapipe==0.10.14"]
QUIET = {"GLOG_minloglevel": "3", "TF_CPP_MIN_LOG_LEVEL": "3", "PYTHONWARNINGS": "ignore", "HF_HUB_DISABLE_PROGRESS_BARS": "1"}


def vpython():
    """The environment's python, made if missing."""
    py = VENV / "bin/python"
    if py.exists():
        return py
    print(f"Setting up the video tools' Python environment at {VENV} (one time, a few minutes)...", flush=True)
    VENV.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("uv"):
        subprocess.run(["uv", "venv", "-q", "--python", "3.11", str(VENV)], check=True)
        subprocess.run(["uv", "pip", "install", "-q", "--python", str(py), *PACKAGES], check=True)
    else:
        base = shutil.which("python3.11") or shutil.which("python3.12")
        if not base:
            raise SystemExit("The video tools need Python 3.11 or 3.12 (MediaPipe has no wheels for newer Pythons), "
                             "or uv (https://docs.astral.sh/uv/) to fetch one.")
        subprocess.run([base, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(py), "-m", "pip", "install", "-q", *PACKAGES], check=True)
    return py


def vision(*args):
    """Run vision.py in the environment; returns the last line of its output as JSON."""
    run = subprocess.run([str(vpython()), str(VISION), *map(str, args)], capture_output=True, text=True,
                         env={**os.environ, **QUIET})
    if run.returncode:
        raise SystemExit(f"vision.py {args[0]} failed:\n{run.stderr[-1500:]}")
    return json.loads(run.stdout.strip().splitlines()[-1])


def probe(path):
    """Width and height as displayed (phone rotation applied), duration, frame rate, and whether there's audio."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,width,height,r_frame_rate:stream_side_data=rotation:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True)
    info = json.loads(out.stdout)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    w, h = video["width"], video["height"]
    if next((abs(int(d.get("rotation", 0))) for d in video.get("side_data_list", []) if "rotation" in d), 0) in (90, 270):
        w, h = h, w
    num, _, den = video.get("r_frame_rate", "30/1").partition("/")
    return {"width": w, "height": h, "duration": float(info["format"]["duration"]),
            "fps": round(float(num) / float(den or 1), 2), "audio": any(s["codec_type"] == "audio" for s in info["streams"])}


def key(path, *extra):
    st = Path(path).stat()
    return hashlib.sha1(f"{Path(path).resolve()}|{st.st_size}|{st.st_mtime}|{extra}".encode()).hexdigest()[:12]


def words(src, work, start=0.0, end=None, model="small", language=None):
    """Every spoken word with its start and end in the source's own time (seconds), cached in work/words-<key>.json.
    Fix misheard names in that file by hand (keep the timings); the edit is kept until the source changes."""
    work.mkdir(parents=True, exist_ok=True)
    cache = work / f"words-{key(src, start, end, model, language)}.json"
    if not cache.exists():
        clip = work / "speech.wav"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", str(src)]
        if end:
            cmd += ["-t", f"{end - start:.3f}"]
        subprocess.run(cmd + ["-vn", "-ac", "1", "-ar", "16000", str(clip)], check=True)
        print("transcribing (the first run downloads the speech model)...", flush=True)
        tmp = work / "words.tmp.json"
        args = ["words", clip, tmp, "--model", model] + (["--language", language] if language else [])
        vision(*args)
        found = json.loads(tmp.read_text())
        for w in found:
            w["s"], w["e"] = round(w["s"] + start, 3), round(w["e"] + start, 3)
        cache.write_text(json.dumps(found, indent=0, ensure_ascii=False))
        tmp.unlink()
        clip.unlink()
        print(f"{len(found)} words -> {cache} (fix any misheard names there, keeping the times)")
    return json.loads(cache.read_text())


def face(src, work):
    work.mkdir(parents=True, exist_ok=True)
    cache = work / f"face-{key(src)}.json"
    if not cache.exists():
        cache.write_text(json.dumps(vision("face", src)))
    return json.loads(cache.read_text())


def cuts(src, threshold=0.3):
    """Times where the picture changes shot (ffmpeg's scene score)."""
    run = subprocess.run(["ffmpeg", "-v", "info", "-i", str(src), "-vf", f"select='gt(scene,{threshold})',showinfo",
                          "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [float(x.split("pts_time:")[1].split()[0]) for x in run.stderr.splitlines() if "pts_time:" in x]
