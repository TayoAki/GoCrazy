"""Teardown of one outlier: post details + transcript + video frames -> the 17-element card (auto fields + review fields).

Carousels and TikTok slideshows are torn down slide by slide instead: every slide is saved, slide 1 is the hook, each
slide is a scene (SEALCaM, measured text), and the madlib templates the slides' text.
"""

import json
import re
import threading

from PIL import Image

from . import ai, annotate, db, llm, media, reach, textstyle
from .annotate import field
from .config import MEDIA, has_ffmpeg, scrapecreators_key
from .scrapecreators import ScrapeCreators, ScrapeError, slideshow_from_tiktok_item

SLIDE_KINDS = ("carousel", "slideshow")
MAX_SLIDES = 20
SPONSORED = re.compile(r"#(ad|sponsored)\b|#\w*partner\b|paid partnership")


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
    return ai.merge(data, result, llm.label(model), usage)


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
        # Text blocks as the model read them, then size, position and colour measured from the scene's first frame.
        frame = MEDIA / data["shortcode"] / sc["frames"][0].rsplit("/", 1)[-1] if sc.get("frames") else None
        sc["text_blocks"] = []
        for block in got.get("text_blocks") or []:
            if not isinstance(block, dict) or not block.get("text"):
                continue
            try:
                block["measured"] = textstyle.measure(frame, block.get("box"), block.get("fill")) if frame and frame.exists() else None
            except Exception:  # a bad box or colour from the model: keep its description, without measurements
                block["measured"] = None
            sc["text_blocks"].append(block)
    data["notes"] = [n for n in data.get("notes") or [] if not n.startswith("Scene breakdown failed")]
    data["scenes_ai"] = {"model": llm.label(model), "cost": usage.get("cost"), "tokens": usage.get("total_tokens"),
                         "missing": [sc["i"] for sc in data["scenes"] if not sc.get("S")]}
    return data


def apply_madlib(data, model):
    """Fill-in-the-blank templates of the reel's own script, hooks, on-screen text and caption (playbook Phase 4)."""
    result, usage = ai.madlib(data, model)
    data["madlib"] = {**result, "model": llm.label(model), "cost": usage.get("cost")}
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
        if data.get("kind") in SLIDE_KINDS and (not frames or not all(f.exists() for f in frames)):
            client = ScrapeCreators(scrapecreators_key())
            with db.connect() as conn:
                reel = conn.execute("SELECT * FROM reels WHERE shortcode=?", (shortcode,)).fetchone()
            if not save_slides(shortcode, _fresh_slides(client, reel)[0]):
                raise RuntimeError("Could not download the slides")
        elif not frames or not all(f.exists() for f in frames):  # only fetch the video again when the scene frames are gone
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
        siblings = conn.execute("SELECT shortcode, url, caption, taken_at FROM reels WHERE username=? AND shortcode<>? AND kind=?",
                                (reel["username"], shortcode, reel["kind"])).fetchall()
        previous = conn.execute("SELECT data FROM teardowns WHERE shortcode=?", (shortcode,)).fetchone()
        lpv = reach.likes_per_view(conn, project_id)
    settings = db.project_settings(project)
    client = ScrapeCreators(scrapecreators_key())
    if reel["kind"] in SLIDE_KINDS:
        return _build_slides(reel, creator, outlier, settings, siblings, previous, client, lpv)
    notes = []

    post = client.post(reel["url"])
    duration = post.get("video_duration") or reel["duration"]
    caption_edges = (post.get("edge_media_to_caption") or {}).get("edges") or []
    caption = (caption_edges[0].get("node", {}).get("text") if caption_edges else None) or reel["caption"] or ""
    typename = post.get("__typename") or ""
    post_type = "carousel" if "Sidecar" in typename else "photo" if "Image" in typename else "reel"
    if post.get("is_paid_partnership") or post.get("is_ad") or SPONSORED.search(caption.lower()):
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
    if settings["ai_annotation"] and llm.available():
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


# ---------- carousels and slideshows ----------

def save_slides(shortcode, slides):
    """Save each slide as slide_NN.jpg (at most 1080 px wide) and slide 1, smaller, as the cover. Returns the file names in
    order, or None when a link no longer works (Instagram and TikTok links expire)."""
    out = media.media_dir(shortcode)
    for old in out.glob("slide_*.jpg"):
        old.unlink()
    names = []
    for k, slide in enumerate(slides[:MAX_SLIDES], 1):
        raw = out / f"_slide_{k}"
        try:
            if not media.download(slide["url"], raw):
                return None
            im = Image.open(raw).convert("RGB")
            if im.width > 1080:
                im = im.resize((1080, round(im.height * 1080 / im.width)), Image.LANCZOS)
            im.save(out / f"slide_{k:02d}.jpg", "JPEG", quality=88)
            if k == 1:
                im.resize((360, round(im.height * 360 / im.width)), Image.LANCZOS).save(media.cover_path(shortcode), "JPEG", quality=85)
        except OSError:  # not an image (an expired link can answer with an error page)
            return None
        finally:
            raw.unlink(missing_ok=True)
        names.append(f"slide_{k:02d}.jpg")
    return names


def _fresh_slides(client, reel):
    """Slide links, sound and caption from a fresh post lookup (1 credit). Returns (slides, music, caption, post)."""
    if reel["kind"] == "slideshow":
        detail = client.tiktok_post(reel["url"])
        fresh = slideshow_from_tiktok_item(detail) if detail else {}
        return fresh.get("slides") or [], fresh.get("music"), fresh.get("caption"), detail
    post = client.post(reel["url"])
    edges = (post.get("edge_sidecar_to_children") or {}).get("edges") or []
    slides = [{"url": e["node"]["display_url"], "video": bool(e["node"].get("is_video"))} for e in edges if e.get("node", {}).get("display_url")]
    music = post.get("clips_music_attribution_info") or {}
    caption_edges = (post.get("edge_media_to_caption") or {}).get("edges") or []
    caption = caption_edges[0].get("node", {}).get("text") if caption_edges else None
    return slides, ({"title": music["song_name"], "artist": music.get("artist_name")} if music.get("song_name") else None), caption, post


def _build_slides(reel, creator, outlier, settings, siblings, previous, client, lpv):
    shortcode, kind = reel["shortcode"], reel["kind"]
    notes = []
    slides = json.loads(reel["slides"] or "[]")
    music = json.loads(reel["music"]) if reel["music"] else None
    caption = reel["caption"] or ""
    post = {}
    if kind == "carousel":  # the post lookup (1 credit) adds the carousel's sound, which the posts feed leaves out
        fresh, fresh_music, fresh_caption, post = _fresh_slides(client, reel)
        slides, music, caption = fresh or slides, fresh_music or music, fresh_caption or caption
    names = save_slides(shortcode, slides) if slides else None
    if names is None and kind == "slideshow":
        fresh, fresh_music, fresh_caption, post = _fresh_slides(client, reel)
        names = save_slides(shortcode, fresh) if fresh else None
        music, caption = fresh_music or music, fresh_caption or caption
    if not names:
        raise RuntimeError("Could not download the slides")
    if len(slides) > MAX_SLIDES:
        notes.append(f"{len(slides)} slides: the first {MAX_SLIDES} are torn down.")
    if any(s.get("video") for s in slides[:MAX_SLIDES]):
        notes.append("Some slides are videos: their cover image stands in for them.")
    if post.get("is_paid_partnership") or post.get("is_ad") or SPONSORED.search(caption.lower()):
        notes.append("Sponsored or paid-partnership post. The playbook excludes these from outliers, so consider dismissing it.")

    first_line = caption.split("\n")[0]
    keyword = outlier["keyword"] if outlier else None
    views = reach.views(reel, lpv)
    estimated = kind == "carousel"
    sound = f'"{music["title"]}" by {music.get("artist") or "unknown"}' if music else None
    what = "TikTok photo slideshow" if kind == "slideshow" else "Instagram carousel"
    fields = {
        "stats": field({"views": views, "views_estimated": estimated, "followers": creator["followers"] if creator else None,
                        "ratio": outlier["ratio"] if outlier else None, "posted": reel["taken_at"], "likes": reel["likes"],
                        "comments": reel["comments"], "saves": reel["saves"], "shares": reel["shares"], "slides": len(names),
                        "duration_s": None}, "api",
                       f"Instagram shows no views for carousels: views estimated from likes at this niche's {lpv:.2%} "
                       "likes per view" if estimated else None),
        "post_type": field("carousel", "api", what),
        "carousel_type": field(None, "needs_review", "Pick one of the eight carousel types"),
        "topic": field(None, "needs_review", f'Found via "{keyword}"; set the sub-niche' if keyword else "Set the sub-niche"),
        "verbal_hook": field(None, "auto", "Slides: nothing is spoken"),
        "written_hook": field(None, "needs_review", "Copy the largest text on slide 1"),
        "visual_hook": field(None, "needs_review", "One sentence: what slide 1 shows"),
        "hook_pattern": annotate.hook_pattern(None, first_line),
        "angle": field(None, "needs_review"),
        "video_type": annotate.video_type("", caption),
        "delivery": field(None, "needs_review"),
        "story_type": field(None, "needs_review", "Only when delivery is storytelling"),
        **annotate.series(None, caption, siblings),
        "content_type": field(None, "needs_review"),
        "funnel": field(None, "needs_review"),
        "complexity": field(None, "needs_review"),
        "structure_pattern": field(None, "needs_review", "Label each slide's beat (HOOK, STEP, PROOF…)"),
        "word_count": field(None, "auto", "Slides: see the text on each slide"),
        "words_per_second": field(None, "auto", "Slides"),
        "value_summary": field(None, "needs_review", "One sentence: what the viewer learns or sees"),
        **annotate.cta("", caption),
        "format": field(None, "auto", f"{len(names)} slides, not a video: see the carousel type"),
        "audio": field("music_only", "api", f"Sound: {sound}") if music else field("none", "api", "No sound on the post"),
        "avg_shot_s": field(None, "auto", "Slides"),
        "cuts": field(None, "auto", "Slides"),
        "captions": field(None, "needs_review", "Text style on the slides, e.g. white sans on a dark box, centred"),
    }
    if previous and previous["data"]:  # human edits survive a re-run
        for key, old in json.loads(previous["data"])["fields"].items():
            if old.get("source") == "human" and key in fields:
                fields[key] = old

    base = f"/media/{shortcode}/"
    urls = [base + n for n in names]
    data = {
        "shortcode": shortcode, "url": reel["url"], "username": reel["username"], "caption": caption, "kind": kind,
        "platform": reel["platform"], "fields": fields, "transcript": None, "notes": notes, "credits_used": client.credits_used,
        "music": {"song_name": music["title"], "artist_name": music.get("artist"), "uses_original_audio": None} if music else None,
        "media": {"cover": base + "cover.jpg", "hook_frames": urls[:1], "frames": urls},
        "scenes": [{"i": k, "slide": True, "start": None, "end": None, "flash_cuts": 0, "cut": True, "frames": [u],
                    "video": bool((slides[k - 1] if k - 1 < len(slides) else {}).get("video"))} for k, u in enumerate(urls, 1)],
        "created_at": db.now(),
    }
    if settings["ai_annotation"] and llm.available():
        for step, name in ((apply_ai, "AI analysis"), (apply_scenes, "Scene breakdown"), (apply_madlib, "Madlib")):
            try:
                data = step(data, settings["ai_model"])
            except Exception as e:
                notes.append(f"{name} failed: {e}")
    return data
