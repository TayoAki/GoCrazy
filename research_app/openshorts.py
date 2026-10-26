"""Render a clip plan with OpenShorts (github.com/mutonby/openshorts): vertical crop with face tracking, burned captions
and the plan's on-screen hook.

OpenShorts makes clips in jobs, then re-cuts a job's clip to any segments of its source (/api/clip/rerender, in seconds
of that source) and burns a hook on it (/api/hook). Which jobs depends on the source:
- A video file on this computer: per clip, its stretch (at least a minute around the clip, OpenShorts' shortest
  range) is cut with ffmpeg and uploaded, so OpenShorts only transcribes and reframes that much. Its timeline starts at
  the stretch's start, so the plan's segments are shifted by that much.
- A YouTube link on the hosted service: per clip, a job over its stretch (source_start / source_end), billed for that
  stretch alone. OpenShorts cuts the stretch out first, so the segments shift the same way.
- A YouTube link on a self-hosted OpenShorts: it ignores source_start / source_end (they only exist for billing), so
  one job takes the whole video and every clip is re-cut from it, in the video's own seconds.
Each clip is downloaded before the next re-cut, and saved under media/clips/<plan id>/.

OpenShorts runs self-hosted (its Docker setup serves the API on localhost:8000, with a Gemini key of its own, ours from
GEMINI_API_KEY, or a local LLM) or hosted at openshorts.app with OPENSHORTS_API_KEY. Processing needs the person's
confirmation that they own the video or have the rights to clip it; it's sent only when they tick that box.
"""

import json
import os
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import requests

from . import db
from .config import MEDIA, openshorts_key, openshorts_url

MIN_RANGE_S = 60       # OpenShorts refuses a shorter stretch
PAD_S = 3.0            # room around the clip for OpenShorts' word snapping
POLL_S = 5
JOB_TIMEOUT_S = 3600
HOOK_STYLE = "pill"
_running = set()
_reach = {"checked": 0.0, "value": None}


class OpenShortsError(Exception):
    pass


def _headers():
    if openshorts_key():
        return {"Authorization": f"Bearer {openshorts_key()}"}
    # Self-hosted OpenShorts takes the Gemini key per request (its own GEMINI_API_KEY is the fallback).
    return {"X-Gemini-Key": os.environ["GEMINI_API_KEY"]} if os.environ.get("GEMINI_API_KEY") else {}


def _call(method, path, timeout=60, **kwargs):
    try:
        resp = requests.request(method, openshorts_url() + path, headers={**_headers(), **kwargs.pop("headers", {})},
                                timeout=timeout, **kwargs)
    except requests.RequestException as e:
        raise OpenShortsError(f"OpenShorts isn't reachable at {openshorts_url()}: {e}") from e
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if resp.status_code >= 400:
        detail = body.get("detail") if isinstance(body, dict) else None
        detail = detail.get("message") if isinstance(detail, dict) else detail
        raise OpenShortsError(f"OpenShorts {method} {path.split('?')[0]}: {resp.status_code} {detail or resp.text[:200]}")
    return body


def reachable(refresh=False):
    """{"ok", "url", "hosted", "error"}: whether OpenShorts answers, checked at most once a minute."""
    if refresh or time.time() - _reach["checked"] > 60:
        value = {"url": openshorts_url(), "hosted": bool(openshorts_key()), "ok": False, "error": None, "billing": None}
        try:
            value["billing"] = bool(_call("GET", "/api/config", timeout=4).get("billingEnabled"))
            value["ok"] = True
        except OpenShortsError as e:
            value["error"] = str(e)
        _reach.update(checked=time.time(), value=value)
    return _reach["value"]


def stretch(clip, duration):
    """The stretch of the long video one clip's job covers: the clip's segments plus a little room, widened to OpenShorts'
    one-minute minimum and kept inside the video."""
    start = max(0.0, min(s["start"] for s in clip["segments"]) - PAD_S)
    end = min(duration, max(s["end"] for s in clip["segments"]) + PAD_S)
    short = MIN_RANGE_S + 1 - (end - start)
    if short > 0:
        start, end = max(0.0, start - short / 2), min(duration, end + short / 2)
        if end - start < MIN_RANGE_S + 1:  # against an edge of the video: widen the other way
            start, end = (0.0, min(duration, MIN_RANGE_S + 1)) if start == 0 else (max(0.0, duration - MIN_RANGE_S - 1), duration)
    return round(start, 2), round(end, 2)


def start(plan_id, file=None, acknowledged=False):
    """Render every clip of a finished clip plan in the background. file: a video on this computer instead of the link."""
    if not acknowledged:
        raise ValueError("Confirm you own this video or have the creator's permission to clip it")
    if file and not Path(file).expanduser().is_file():
        raise ValueError(f"No video file at {file}")
    if plan_id in _running:
        raise RuntimeError("These clips are already rendering.")
    with db.connect() as conn:
        row = conn.execute("SELECT data FROM clip_plans WHERE id=? AND status='done'", (plan_id,)).fetchone()
    if not row:
        raise ValueError("Plan the clips first")
    status = reachable(refresh=True)
    if not status["ok"]:
        raise RuntimeError(status["error"])
    plan = json.loads(row["data"])
    _save(plan_id, {"status": "running", "message": "Starting", "file": file, "clips": [], "updated_at": db.now()})
    _running.add(plan_id)
    threading.Thread(target=_run, args=(plan_id, plan, file and str(Path(file).expanduser()), status["billing"]),
                     daemon=True).start()


def _save(plan_id, render):
    with db.connect() as conn:
        conn.execute("UPDATE clip_plans SET render=? WHERE id=?", (json.dumps(render), plan_id))


def _run(plan_id, plan, file, billing):
    render = {"status": "running", "file": file, "clips": [], "updated_at": db.now()}
    out = MEDIA / "clips" / str(plan_id)
    out.mkdir(parents=True, exist_ok=True)
    try:
        total, whole = len(plan["clips"]), None
        for k, clip in enumerate(plan["clips"]):
            def progress(message, k=k):
                _save(plan_id, {**render, "message": f"Clip {k + 1} of {total}: {message}", "updated_at": db.now()})
            try:
                if file or billing:
                    job, index, offset = stretch_job(clip, plan["source"], file, progress)
                else:
                    whole = whole or whole_job({"url": plan["source"]["url"]}, progress)
                    (job, index), offset = whole, 0.0
                finish(job, index, offset, clip, out / f"clip_{clip['rank']}.mp4", progress)
                render["clips"].append({"rank": clip["rank"], "job_id": job,
                                        "file": f"/media/clips/{plan_id}/clip_{clip['rank']}.mp4?v={int(time.time())}"})
            except Exception as e:
                render["clips"].append({"rank": clip["rank"], "error": str(e)})
        made = [c for c in render["clips"] if c.get("file")]
        errors = [c["error"] for c in render["clips"] if c.get("error")]
        render.update(status="done" if made else "failed", error=errors[0] if errors else None,
                      message=f"{len(made)} of {total} clips rendered")
    except Exception as e:
        render.update(status="failed", error=str(e))
    finally:
        render["updated_at"] = db.now()
        _save(plan_id, render)
        _running.discard(plan_id)
        db.log(None, "success" if render["status"] == "done" else "error",
               f"Clip plan #{plan_id}: {render.get('message') or render.get('error')}")


BASE_JOB = {"acknowledged": True, "target_clips": 1, "auto_hook": False, "captions": True, "output_format": "vertical"}


def stretch_job(clip, source, file, progress):
    """A job over the clip's stretch: cut from the local file and uploaded, or (hosted only) the link with a range.
    Returns (job id, clip index, the stretch's start in the long video)."""
    start, end = stretch(clip, source["duration"])
    if file:
        progress("cutting the stretch from your file")
        body = {"upload_id": _upload(_cut(file, start, end), progress)}
    else:
        body = {"url": source["url"], "source_start": start, "source_end": end}
    return (*_job(body, progress), start)


def whole_job(body, progress):
    """One job over the whole source (a self-hosted OpenShorts given a link). Returns (job id, clip index)."""
    return _job(body, progress)


def _job(body, progress):
    progress("sending to OpenShorts")
    job = _call("POST", "/api/process", json={**BASE_JOB, **body})["job_id"]
    return job, _first_clip(_wait(job, progress))


def finish(job, index, offset, clip, dest, progress):
    """Re-cut the job's clip to the plan's segments (shifted to the job's timeline), burn the hook on, download it."""
    progress("cutting to the planned segments")
    segments = [{"start": round(s["start"] - offset, 2), "end": round(s["end"] - offset, 2)} for s in clip["segments"]]
    url = _call("POST", "/api/clip/rerender", timeout=900, json={
        "job_id": job, "clip_index": index, "segments": segments, "snap_to_words": True, "reapply_captions": True})["new_video_url"]
    if clip.get("on_screen"):
        progress("adding the hook text")
        url = _call("POST", "/api/hook", timeout=600, json={"job_id": job, "clip_index": index, "text": clip["on_screen"],
                                                             "position": "auto", "style": HOOK_STYLE})["new_video_url"]
    progress("downloading")
    _download(url, dest)


def _first_clip(result):
    """The index OpenShorts' editing calls want for the job's first clip. A finished job lists only the clips that
    rendered, so the index comes from the clip's file name ("..._clip_<n>.mp4", n counting from 1), not its place."""
    for clip in (result or {}).get("clips") or []:
        match = re.search(r"_clip_(\d+)\.mp4", clip.get("video_url") or "")
        if match:
            return int(match.group(1)) - 1
    raise OpenShortsError("OpenShorts made no clip from this stretch")


def _cut(file, start, end):
    """The stretch of a local video as its own file, re-encoded so it starts exactly at start."""
    fd, path = tempfile.mkstemp(suffix=".mp4", prefix="openshorts_")
    os.close(fd)
    run = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-i", file, "-t", str(round(end - start, 2)),
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                          "-movflags", "+faststart", path], capture_output=True, text=True)
    if run.returncode:
        raise OpenShortsError(f"ffmpeg couldn't cut the file: {run.stderr[-300:]}")
    return path


def _upload(path, progress):
    try:
        slot = _call("POST", "/api/uploads", json={"filename": Path(path).name})
        progress("uploading the stretch")
        with open(path, "rb") as f:
            resp = requests.put(slot["upload_url"], data=f, headers=_headers(), timeout=900)
        if resp.status_code >= 400:
            raise OpenShortsError(f"OpenShorts upload: {resp.status_code} {resp.text[:200]}")
        return slot["upload_id"]
    finally:
        os.remove(path)


def _wait(job, progress):
    deadline = time.time() + JOB_TIMEOUT_S
    while time.time() < deadline:
        status = _call("GET", f"/api/status/{job}")
        state = status.get("status")
        if state == "completed":
            return status.get("result")
        if state in ("failed", "error", "cancelled"):
            logs = [line for line in status.get("logs") or [] if line.strip()]
            raise OpenShortsError("OpenShorts job failed" + (f": {logs[-1][:200]}" if logs else ""))
        queue = status.get("queue") or {}
        logs = [line for line in status.get("logs") or [] if line.strip()]
        last = logs[-1].split("\r")[-1].strip() if logs else ""  # progress bars redraw with \r: keep the latest
        progress(f"OpenShorts is {state}" + (f" (#{queue['position']} in line)" if queue.get("position") else "")
                 + (f" · {last[:80]}" if last else ""))
        time.sleep(POLL_S)
    raise OpenShortsError("OpenShorts took over an hour on one clip")


def _download(url, dest):
    full = url if url.startswith("http") else openshorts_url() + url
    with requests.get(full, headers=_headers() if full.startswith(openshorts_url()) else {}, stream=True, timeout=300) as resp:
        if resp.status_code >= 400:
            raise OpenShortsError(f"Couldn't download the clip: {resp.status_code}")
        tmp = Path(str(dest) + ".part")
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)
        tmp.replace(dest)
