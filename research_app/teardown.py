"""Teardown of one outlier: post details + transcript + video frames -> the 17-element card (auto fields + review fields)."""

import json
import re
import threading

from . import ai, annotate, db, media
from .annotate import field
from .config import MEDIA, has_ffmpeg, openrouter_key, scrapecreators_key
from .scrapecreators import ScrapeCreators, ScrapeError


def start_ai(shortcode, project_id):
    """Re-run only the AI pass on an existing teardown (no ScrapeCreators credits)."""
    with db.connect() as conn:
        row = conn.execute("SELECT status, data FROM teardowns WHERE shortcode=?", (shortcode,)).fetchone()
        if not row or row["status"] != "done":
            raise RuntimeError("Tear the outlier down first.")
        conn.execute("UPDATE teardowns SET status='running', updated_at=? WHERE shortcode=?", (db.now(), shortcode))
    threading.Thread(target=_run_ai, args=(shortcode, project_id, json.loads(row["data"])), daemon=True).start()


def _run_ai(shortcode, project_id, data):
    error = None
    try:
        with db.connect() as conn:
            settings = db.project_settings(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
        data = apply_ai(data, settings["ai_model"])
    except Exception as e:
        error = str(e)
    with db.connect() as conn:
        conn.execute("UPDATE teardowns SET status='done', data=?, error=?, updated_at=? WHERE shortcode=?",
                     (json.dumps(data), error, db.now(), shortcode))
    db.log(project_id, "error" if error else "success",
           f"AI analysis {'failed' if error else 'done'} for {shortcode}" + (f": {error}" if error else ""))


def apply_ai(data, model):
    result, usage = ai.analyze(data, model)
    data["notes"] = [n for n in data.get("notes") or [] if not n.startswith("AI analysis failed")]  # it worked this time
    return ai.merge(data, result, model, usage)


def apply_scenes(data, model):
    """SEALCaM for every scene. Run after apply_ai, which drops the transcript when it's only song lyrics."""
    for sc in data.get("scenes") or []:
        sc["said"] = ai.spoken_in(data.get("transcript"), sc["start"], sc["end"])
    found, usage = ai.breakdown(data, model)
    by_i = {s.get("i"): s for s in found}
    for sc in data["scenes"]:
        got = by_i.get(sc["i"]) or {}
        sc["beat"] = got.get("beat") if got.get("beat") in annotate.BEATS else None
        sc["on_screen_text"] = got.get("on_screen_text")
        sc.update({k: got.get(k) for k in ai.SEALCAM_KEYS})
    data["notes"] = [n for n in data.get("notes") or [] if not n.startswith("Scene breakdown failed")]
    data["scenes_ai"] = {"model": model, "cost": usage.get("cost"), "tokens": usage.get("total_tokens"),
                         "missing": [sc["i"] for sc in data["scenes"] if not sc.get("S")]}
    return data


def apply_madlib(data, model):
    """Fill-in-the-blank templates of the reel's own script, hooks, on-screen text and caption (playbook Phase 4)."""
    result, usage = ai.madlib(data, model)
    data["madlib"] = {**result, "model": model, "cost": usage.get("cost")}
    data["notes"] = [n for n in data.get("notes") or [] if not n.startswith("Madlib failed")]
    return data


def start_madlib(shortcode, project_id):
    with db.connect() as conn:
        row = conn.execute("SELECT status, data FROM teardowns WHERE shortcode=?", (shortcode,)).fetchone()
        if not row or row["status"] != "done":
            raise RuntimeError("Tear the outlier down first.")
        conn.execute("UPDATE teardowns SET status='running', updated_at=? WHERE shortcode=?", (db.now(), shortcode))
    threading.Thread(target=_run_madlib, args=(shortcode, project_id, json.loads(row["data"])), daemon=True).start()


def _run_madlib(shortcode, project_id, data):
    error = None
    try:
        with db.connect() as conn:
            settings = db.project_settings(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
        data = apply_madlib(data, settings["ai_model"])
    except Exception as e:
        error = str(e)
    with db.connect() as conn:
        conn.execute("UPDATE teardowns SET status='done', data=?, error=?, updated_at=? WHERE shortcode=?",
                     (json.dumps(data), error, db.now(), shortcode))
    db.log(project_id, "error" if error else "success", f"Madlib {'failed' if error else 'done'} for {shortcode}" + (f": {error}" if error else ""))


def start_scenes(shortcode, project_id):
    """Scene-by-scene SEALCaM breakdown for an existing teardown: fetches the video again (the post lookup is cached)."""
    with db.connect() as conn:
        row = conn.execute("SELECT status, data FROM teardowns WHERE shortcode=?", (shortcode,)).fetchone()
        if not row or row["status"] != "done":
            raise RuntimeError("Tear the outlier down first.")
        conn.execute("UPDATE teardowns SET status='running', updated_at=? WHERE shortcode=?", (db.now(), shortcode))
    threading.Thread(target=_run_scenes, args=(shortcode, project_id, json.loads(row["data"])), daemon=True).start()


def _run_scenes(shortcode, project_id, data):
    error = None
    try:
        with db.connect() as conn:
            settings = db.project_settings(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
        frames = [MEDIA / shortcode / url.rsplit("/", 1)[-1] for sc in data.get("scenes") or [] for url in sc["frames"]]
        if not frames or not all(f.exists() for f in frames):  # only fetch the video again when the scene frames are gone
            client = ScrapeCreators(scrapecreators_key())
            post = client.post(data["url"])
            if not post.get("video_url"):
                raise RuntimeError("This post has no video")
            video = _analyze_video(client, data["url"], shortcode, post)
            if video.get("error"):
                raise RuntimeError(video["error"])
            data["media"].update(_media_urls(shortcode, video))
            data["scenes"] = _scenes(shortcode, video)
        data = apply_scenes(data, settings["ai_model"])
    except Exception as e:
        error = str(e)
    with db.connect() as conn:
        conn.execute("UPDATE teardowns SET status='done', data=?, error=?, updated_at=? WHERE shortcode=?",
                     (json.dumps(data), error, db.now(), shortcode))
    db.log(project_id, "error" if error else "success",
           f"Scene breakdown {'failed' if error else 'done'} for {shortcode}" + (f": {error}" if error else ""))


def _analyze_video(client, url, shortcode, post):
    """A cached post lookup can hold an expired video link: retry once with a fresh lookup (1 credit)."""
    video = media.analyze_video(post["video_url"], shortcode, post.get("video_duration"))
    if video.get("error"):
        fresh = client.post(url, fresh=True)
        if fresh.get("video_url") and fresh["video_url"] != post["video_url"]:
            video = media.analyze_video(fresh["video_url"], shortcode, fresh.get("video_duration"))
    return video


def _media_urls(shortcode, video):
    base = f"/media/{shortcode}/"
    return {"hook_frames": [base + f for f in video.get("hook_frames", [])], "frames": [base + f for f in video.get("frames", [])]}


def _scenes(shortcode, video):
    base = f"/media/{shortcode}/"
    return [{"i": k, "start": sc["start"], "end": sc["end"], "flash_cuts": sc["flash_cuts"], "cut": sc["cut"],
             "frames": [base + f for f in sc["frames"]]} for k, sc in enumerate(video.get("scenes") or [], 1)]


def start_teardown(shortcode, project_id):
    with db.connect() as conn:
        row = conn.execute("SELECT status FROM teardowns WHERE shortcode=?", (shortcode,)).fetchone()
        if row and row["status"] == "running":
            raise RuntimeError("This teardown is already running.")
        conn.execute("""INSERT INTO teardowns (shortcode, status, updated_at) VALUES (?, 'running', ?)
                        ON CONFLICT(shortcode) DO UPDATE SET status='running', error=NULL, updated_at=excluded.updated_at""",
                     (shortcode, db.now()))
    threading.Thread(target=_run, args=(shortcode, project_id), daemon=True).start()


def _run(shortcode, project_id):
    try:
        data = build(shortcode, project_id)
        with db.connect() as conn:
            conn.execute("UPDATE teardowns SET status='done', data=?, error=NULL, updated_at=? WHERE shortcode=?",
                         (json.dumps(data), db.now(), shortcode))
        db.log(project_id, "success", f"Teardown ready: @{data['username']} ({shortcode}) · {data['credits_used']} credits")
    except Exception as e:
        message = "Out of ScrapeCreators credits" if isinstance(e, ScrapeError) and e.out_of_credits else str(e)
        with db.connect() as conn:
            conn.execute("UPDATE teardowns SET status='failed', error=?, updated_at=? WHERE shortcode=?",
                         (message, db.now(), shortcode))
        db.log(project_id, "error", f"Teardown failed for {shortcode}: {message}")


def build(shortcode, project_id):
    with db.connect() as conn:
        reel = conn.execute("SELECT * FROM reels WHERE shortcode=?", (shortcode,)).fetchone()
        if not reel:
            raise ValueError("Unknown reel")
        creator = conn.execute("SELECT * FROM creators WHERE username=?", (reel["username"],)).fetchone()
        outlier = conn.execute("SELECT * FROM outliers WHERE project_id=? AND shortcode=?", (project_id, shortcode)).fetchone()
        project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        siblings = conn.execute("SELECT shortcode, url, caption, taken_at FROM reels WHERE username=? AND shortcode<>?",
                                (reel["username"], shortcode)).fetchall()
        previous = conn.execute("SELECT data FROM teardowns WHERE shortcode=?", (shortcode,)).fetchone()
    settings = db.project_settings(project)
    client = ScrapeCreators(scrapecreators_key())
    notes = []

    post = client.post(reel["url"])
    duration = post.get("video_duration") or reel["duration"]
    caption_edges = (post.get("edge_media_to_caption") or {}).get("edges") or []
    caption = (caption_edges[0].get("node", {}).get("text") if caption_edges else None) or reel["caption"] or ""
    typename = post.get("__typename") or ""
    post_type = "carousel" if "Sidecar" in typename else "photo" if "Image" in typename else "reel"
    if post.get("is_paid_partnership") or post.get("is_ad") or re.search(r"#(ad|sponsored)\b|#\w*partner\b|paid partnership", caption.lower()):
        notes.append("Sponsored or paid-partnership post. The playbook excludes these from outliers, so consider dismissing it.")

    transcript = None
    if post_type == "photo":
        notes.append("Photo post: no transcript or video analysis.")
    elif duration and duration > 120 and not settings["allow_long_transcription"]:
        notes.append(f"Transcript skipped: {round(duration)}s is over 120s (would cost 10 credits per started minute; "
                     "turn on long transcription in the project settings to allow it).")
    else:
        try:
            t = client.transcript(reel["url"], allow_long=settings["allow_long_transcription"])
            if t and t.get("text"):
                segs = t.get("transcript_with_timestamp")
                transcript = {"text": t["text"],
                              "segments": [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in segs] if segs else None}
            else:
                notes.append("No speech detected in the video.")
        except ScrapeError as e:
            if e.out_of_credits:
                raise
            notes.append(f"Transcript unavailable: {e}")

    video = {}
    if post.get("video_url") and has_ffmpeg():
        video = _analyze_video(client, reel["url"], shortcode, post)
        if video.get("error"):
            notes.append(video["error"])
    elif not has_ffmpeg():
        notes.append("ffmpeg isn't installed, so no frames or cut count.")
    thumb = post.get("thumbnail_src") or reel["thumb_url"]
    if thumb and not media.cover_path(shortcode).exists():
        media.download(thumb, media.media_dir(shortcode) / "cover.jpg")

    cuts = video.get("cuts")
    avg_shot = round(duration / (cuts + 1), 1) if cuts is not None and duration else None
    text = transcript["text"] if transcript else ""
    hook = annotate.verbal_hook(transcript)
    first_line = caption.split("\n")[0]
    keyword = outlier["keyword"] if outlier else None

    fields = {
        "stats": field({"views": reel["views"] or post.get("video_play_count"), "followers": creator["followers"] if creator else None,
                        "ratio": outlier["ratio"] if outlier else None, "posted": reel["taken_at"], "likes": reel["likes"],
                        "comments": reel["comments"], "duration_s": duration}, "api"),
        "post_type": field(post_type, "api"),
        "topic": field(None, "needs_review", f'Found via "{keyword}"; set the sub-niche' if keyword else "Set the sub-niche"),
        "verbal_hook": hook,
        "written_hook": field(None, "needs_review", "Copy the largest on-screen text from the hook frames"),
        "visual_hook": field(None, "needs_review", "One sentence: what happens in the hook frames"),
        "hook_pattern": annotate.hook_pattern(hook["value"], first_line),
        "angle": field(None, "needs_review"),
        "video_type": annotate.video_type(text, caption),
        "delivery": field(None, "needs_review"),
        "story_type": field(None, "needs_review", "Only when delivery is storytelling"),
        **annotate.series(hook["value"], caption, siblings),
        "content_type": field(None, "needs_review"),
        "funnel": field(None, "needs_review"),
        **annotate.structure(text, duration),
        "value_summary": field(None, "needs_review", "One sentence: what the viewer learns or sees"),
        **annotate.cta(text, caption),
        "format": annotate.format_guess(avg_shot),
        "audio": annotate.audio(post.get("clips_music_attribution_info"), bool(text)),
        "avg_shot_s": field(avg_shot, "auto"),
        "cuts": field(cuts, "auto"),
        "captions": field(None, "needs_review", "e.g. word_by_word, center, 2 colors"),
    }
    # Re-running a teardown refreshes the automatic fields but never overwrites what a person entered.
    if previous and previous["data"]:
        for key, old in json.loads(previous["data"])["fields"].items():
            if old.get("source") == "human":
                fields[key] = old

    base = f"/media/{shortcode}/"
    data = {
        "shortcode": shortcode, "url": reel["url"], "username": reel["username"], "caption": caption,
        "fields": fields, "transcript": transcript, "notes": notes, "credits_used": client.credits_used,
        "music": {k: (post.get("clips_music_attribution_info") or {}).get(k) for k in ("song_name", "artist_name", "uses_original_audio")},
        "media": {"cover": base + "cover.jpg" if media.cover_path(shortcode).exists() else None, **_media_urls(shortcode, video)},
        "scenes": _scenes(shortcode, video),
        "created_at": db.now(),
    }
    if settings["ai_annotation"] and openrouter_key():
        try:
            data = apply_ai(data, settings["ai_model"])
        except Exception as e:  # the automatic card is still useful without the AI pass
            notes.append(f"AI analysis failed: {e}")
        if data["scenes"]:
            try:
                data = apply_scenes(data, settings["ai_model"])
            except Exception as e:
                notes.append(f"Scene breakdown failed: {e}")
        try:
            data = apply_madlib(data, settings["ai_model"])
        except Exception as e:
            notes.append(f"Madlib failed: {e}")
    return data
