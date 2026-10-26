"""Clip plans: cut one long YouTube video into Shorts, reels and TikToks, and write each clip's hook from the niche.

The moments come from what YouTube shows about the video: its timed transcript, its "most replayed" graph, its chapters
and its top comments. The hooks come from the niche's short-form winners: the opening lines and on-screen text of the
reels, Shorts and slideshows that beat their creators in this project, and in other projects researching the same
keywords (a YouTube project and an Instagram/TikTok project on one niche share their evidence). OpenShorts renders a
plan (openshorts.py): the vertical crop, burned captions and the hook text.
"""

import json
import re
import statistics
import threading

from . import ai, db, llm, pipeline, teardown
from .config import scrapecreators_key
from .scrapecreators import ScrapeCreators, ScrapeError, yt_from_item, yt_handle, yt_shortcode

SHORT_FORM = ("reel", "short", "slideshow", "carousel")
KIND_LABEL = {"reel": "reel", "short": "YouTube Short", "slideshow": "TikTok slideshow", "carousel": "Instagram carousel"}
MIN_CLIP_S, MAX_CLIP_S = 15, 90
MAX_SEGMENTS = 3
MIN_SEGMENT_S = 1.5
MIN_SOURCE_S = 180  # shorter than this is already a short
EVIDENCE = 30
VIDEO_ID = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})")
_running = set()

CLIP_SYSTEM = """You cut one long YouTube video into short vertical clips (YouTube Shorts, Instagram Reels, TikTok) and write
each clip's hook, using what wins in short form in this niche.

You get the account that will post the clips, the video's transcript (each line starts when it is said), its chapters,
YouTube's "most replayed" graph, its top comments, and the niche's short-form winners: the first line each one says, its
on-screen text and how far it beat its creator.

Rules:
1. Each clip stands alone. Someone who never saw the long video understands it and gets a payoff: a number, a reveal, a
   reaction, a verdict or a tip they can use. One idea per clip.
2. The first 1-3 seconds hook. spoken_hook is the first sentence heard, quoted exactly from the transcript. If the
   moment's strongest line comes after its setup, open on it (a cold open): the clip's first segment is that line
   (2-8 s), then it cuts back to the setup and plays through (the line may play again in place). Never open on a
   greeting, a sponsor read, "so" or context.
3. segments: what plays, in the order it plays, in seconds of the long video, at most 3, each at least 2 s. Start and
   end on a transcript line's start time. A clip without a cold open is one segment.
4. Length: aim for the niche's winning length (given below), within 15-60 s unless a moment truly needs up to 90 s.
5. Prefer moments YouTube's viewers replayed most and moments the top comments quote or argue about. Say which in why.
6. on_screen: the hook text burned over the clip, at most 8 words, modelled on one of the niche's winners (put its id in
   follows and its pattern in hook_pattern). It adds the stakes or the number; it doesn't repeat the spoken line.
   Spread the models: no more than two clips on the same winner.
7. ends_on: the last words heard, quoted exactly. End on the payoff or a line that loops back to the start, never mid
   sentence and never on a "subscribe" ask.
8. title: the YouTube Shorts title, at most 70 characters. caption: for TikTok and Instagram, 1-2 short lines and 3-5
   hashtags; credit the video's creator when the poster is someone else.
9. check: what to fix before posting: claims to verify, context the clip lacks, a sponsor mention or a brand that must
   be cut or kept, anything that needs the creator's permission. "" when nothing.
10. No two clips overlap. Rank them best first. Skip a moment rather than pad the list.

Reply with JSON only:
{"clips": [{"rank": 1, "idea": "the clip's one idea, in a sentence", "segments": [{"start": 0.0, "end": 0.0}],
  "cold_open": false, "spoken_hook": "...", "on_screen": "...", "follows": "<id of a winner>", "hook_pattern": "...",
  "ends_on": "...", "title": "...", "caption": "...", "why": "...", "check": "..."}],
 "skipped": "one line: strong moments you left out and why"}"""


def video_id(source):
    """The 11-character id from a YouTube link, a "yt-" shortcode or a bare id; None for anything else."""
    source = (source or "").strip()
    if source.startswith("yt-") and len(source) == 14:
        return source[3:]
    match = VIDEO_ID.search(source)
    if match:
        return match.group(1)
    return source if re.fullmatch(r"[A-Za-z0-9_-]{11}", source) else None


def sibling_projects(conn, project_id):
    """This project and every project sharing at least half its keywords: one niche researched on other platforms."""
    rows = conn.execute("SELECT id, keywords FROM projects").fetchall()
    mine = {k.lower() for r in rows if r["id"] == project_id for k in json.loads(r["keywords"])}
    return [r["id"] for r in rows if r["id"] == project_id or
            (mine and len(mine & {k.lower() for k in json.loads(r["keywords"])}) >= len(mine) / 2)]


def hook_evidence(project_id, talking=18, slides=10):
    """The niche's short-form winners with their hooks, from this project and its siblings: the strongest reels and Shorts
    (their spoken first lines) and the strongest slideshows and carousels (their cover text), each group by ratio. The
    groups are kept apart because slide posts beat their creators' follower counts by far more than videos do."""
    with db.connect() as conn:
        projects = sibling_projects(conn, project_id)
        rows = conn.execute(f"""SELECT o.shortcode, MAX(o.ratio) AS ratio, o.measure, r.username, r.url, r.kind, r.duration,
                                       t.data FROM outliers o JOIN reels r ON r.shortcode = o.shortcode
                                JOIN teardowns t ON t.shortcode = o.shortcode
                                WHERE o.project_id IN ({','.join('?' * len(projects))}) AND o.status <> 'dismissed'
                                  AND t.status = 'done' AND r.kind IN ({','.join('?' * len(SHORT_FORM))})
                                GROUP BY o.shortcode ORDER BY ratio DESC""", projects + list(SHORT_FORM)).fetchall()
    out, room = [], {"talking": talking, "slides": slides}
    for r in rows:
        group = "talking" if r["kind"] in ("reel", "short") else "slides"
        if not room[group]:
            continue
        data = json.loads(r["data"])
        if any("Sponsored" in n or "paid promotion" in n for n in data.get("notes") or []):
            continue
        f = {k: (v or {}).get("value") for k, v in data["fields"].items()}
        said, shown = f.get("verbal_hook"), f.get("written_hook")
        if not (said if group == "talking" else shown):
            continue
        hooks = (data.get("madlib") or {}).get("hooks") or {}
        out.append({"id": r["shortcode"], "who": db.who(r["username"]), "url": r["url"], "kind": r["kind"], "group": group,
                    "ratio": r["ratio"], "against": "the channel's median" if r["measure"] == "median" else "followers",
                    "length_s": round(r["duration"]) if r["duration"] else None, "said": (said or "")[:200] or None,
                    "on_screen": (shown or "")[:150] or None, "hook_pattern": f.get("hook_pattern"),
                    "said_template": (hooks.get("verbal") or {}).get("template"),
                    "on_screen_template": (hooks.get("written") or {}).get("template")})
        room[group] -= 1
    return out


def winning_length(evidence):
    """The median length of the winning reels and Shorts, in seconds (None without at least 5)."""
    lengths = [e["length_s"] for e in evidence if e["kind"] in ("reel", "short") and e["length_s"]]
    return round(statistics.median(lengths)) if len(lengths) >= 5 else None


def default_about(project_id):
    """The newest week plan's "about" text from this project or a sibling: who will post the clips."""
    with db.connect() as conn:
        projects = sibling_projects(conn, project_id)
        row = conn.execute(f"""SELECT input FROM plans WHERE project_id IN ({','.join('?' * len(projects))})
                               AND input IS NOT NULL ORDER BY id DESC LIMIT 1""", projects).fetchone()
    return (json.loads(row["input"]).get("about") or "") if row else ""


def start(project_id, source, clips, about, model):
    """Plan clips for a long video, from a YouTube link or a "yt-" shortcode. Returns the clip plan's id."""
    vid = video_id(source)
    if not vid:
        raise ValueError("Give a YouTube video link")
    if not scrapecreators_key():
        raise RuntimeError("SCRAPECREATORS_API_KEY is not set")
    if vid in _running:
        raise RuntimeError("Clips are already being planned for this video.")
    about = (about or "").strip() or default_about(project_id)
    with db.connect() as conn:
        cur = conn.execute("INSERT INTO clip_plans (project_id, shortcode, status, input, created_at) VALUES (?,?,?,?,?)",
                           (project_id, yt_shortcode(vid), "running",
                            json.dumps({"clips": clips, "about": about, "model": model}), db.now()))
        plan_id = cur.lastrowid
    _running.add(vid)
    threading.Thread(target=_run, args=(plan_id, project_id, vid, clips, about, model), daemon=True).start()
    return plan_id


def _run(plan_id, project_id, vid, clips, about, model):
    try:
        data = build(project_id, vid, clips, about, model)
        with db.connect() as conn:
            conn.execute("UPDATE clip_plans SET status='done', data=?, error=NULL WHERE id=?", (json.dumps(data), plan_id))
        db.log(project_id, "success", f"Clip plan #{plan_id} ready: {len(data['clips'])} clips from {data['source']['title']}")
    except Exception as e:
        message = "Out of ScrapeCreators credits" if isinstance(e, ScrapeError) and e.out_of_credits else str(e)
        with db.connect() as conn:
            conn.execute("UPDATE clip_plans SET status='failed', error=? WHERE id=?", (message, plan_id))
        db.log(project_id, "error", f"Clip plan #{plan_id} failed: {message}")
    finally:
        _running.discard(vid)


def source_video(client, vid):
    """The long video's details, transcript and comments: from its teardown when there is one (no credits), else fetched
    (2-3 credits). The details are always fetched for the full most-replayed graph (cached by ScrapeCreators for 30 days).
    The video is saved to the reels table so it shows up like any other post."""
    url = f"https://www.youtube.com/watch?v={vid}"
    shortcode = yt_shortcode(vid)
    detail = client.yt_video(url)
    post = yt_from_item({**detail, "id": vid}, "video")
    if (post["duration"] or 0) < MIN_SOURCE_S:
        raise ValueError("This video is already short: clip a video longer than 3 minutes")
    with db.connect() as conn:
        known = conn.execute("SELECT username FROM reels WHERE shortcode=?", (shortcode,)).fetchone()
        username = known["username"] if known else (f"yt:{yt_handle(detail.get('channel'))}" if yt_handle(detail.get("channel")) else None)
        if not username:
            raise ValueError("YouTube didn't say whose video this is")
        if not conn.execute("SELECT 1 FROM creators WHERE username=?", (username,)).fetchone():
            channel = detail.get("channel") or {}
            pipeline.save_creator(conn, username, channel.get("title"), channel.get("subscriberCount"), False)
        pipeline.upsert_reel(conn, post, username)
        row = conn.execute("SELECT data FROM teardowns WHERE shortcode=? AND status='done'", (shortcode,)).fetchone()
    torn = json.loads(row["data"]) if row else {}
    notes = []
    transcript = torn.get("transcript") or teardown._youtube_transcript(client, url, notes)
    if not transcript:
        raise ValueError("This video has no captions, so there's no transcript to pick moments from")
    comments = torn.get("comments")
    if comments is None:
        try:
            comments = sorted(({"text": (c.get("content") or "")[:500], "likes": (c.get("engagement") or {}).get("likes") or 0}
                               for c in client.yt_comments(url) if c.get("content")), key=lambda c: -c["likes"])[:20]
        except ScrapeError as e:
            if e.out_of_credits:
                raise
            comments = []
    return {"shortcode": shortcode, "url": url, "username": username, "title": detail.get("title") or post["caption"],
            "description": (detail.get("description") or "")[:1500], "duration": post["duration"], "views": post["views"],
            "posted": post["taken_at"], "chapters": [{"start": c["startSeconds"], "title": c.get("title")}
                                                     for c in detail.get("chapters") or [] if c.get("startSeconds") is not None],
            "replay": [{"start": m["startMillis"] / 1000, "end": (m["startMillis"] + m["durationMillis"]) / 1000,
                        "intensity": round(m.get("intensityScoreNormalized") or 0, 3)}
                       for m in (detail.get("most_replayed") or {}).get("markers") or []],
            "transcript": transcript, "comments": comments or [], "notes": notes, "credits_used": client.credits_used}


def _clock(seconds):
    return ai._clock(seconds)


def _prompt(src, evidence, clips, about):
    replay = src["replay"]
    graph = " | ".join(f"{_clock(m['start'])} {m['intensity']:.2f}" for m in replay) or "(YouTube shows no most-replayed graph)"
    average = round(statistics.mean(m["intensity"] for m in replay), 2) if replay else None
    lines = "\n".join(f"[{_clock(s['start'])}] {s['text']}" for s in src["transcript"]["segments"])
    if len(lines) > 90000:  # very long videos: one line every ~10 s keeps the whole video in view
        merged, bucket = [], []
        for s in src["transcript"]["segments"]:
            if bucket and s["start"] - bucket[0]["start"] >= 10:
                merged.append(f"[{_clock(bucket[0]['start'])}] " + " ".join(b["text"] for b in bucket))
                bucket = []
            bucket.append(s)
        merged += [f"[{_clock(bucket[0]['start'])}] " + " ".join(b["text"] for b in bucket)] if bucket else []
        lines = "\n".join(merged)
    def table(group):
        return "\n".join(f"{e['id']} | {e['kind']} by {e['who']} | {e['ratio']}× {e['against']} | "
                         + (f"{e['length_s'] or '?'} s | said: {e['said'] or '-'} | " if group == "talking" else "")
                         + f"on screen: {e['on_screen'] or '-'} | pattern: {e['hook_pattern'] or '-'}"
                         for e in evidence if e["group"] == group) or "(none torn down yet)"
    length = winning_length(evidence)
    return (f"POSTED BY (the account that will post these clips):\n{about or '(not given: write as the video’s own creator)'}\n\n"
            f"THE LONG VIDEO: \"{src['title']}\" by {db.who(src['username'])} · {src['views']} views · "
            f"{_clock(src['duration'])} long · posted {src['posted']}\n\nDESCRIPTION (start):\n{src['description'] or '(none)'}\n\n"
            "CHAPTERS:\n" + ("\n".join(f"{_clock(c['start'])} {c['title']}" for c in src["chapters"]) or "(none)") +
            f"\n\nMOST REPLAYED (YouTube's graph in 100 slices, start time and intensity, 1.00 = the most replayed slice; "
            f"the video averages {average}):\n{graph}\n\n"
            "TOP COMMENTS:\n" + ("\n".join(f"- ({c['likes']} likes) {c['text'][:300]}" for c in src["comments"][:15]) or "(none)") +
            f"\n\nTRANSCRIPT:\n{lines}\n\n"
            "WHAT WINS IN SHORT FORM IN THIS NICHE. Talking videos, for the spoken hook (id | post | how far it beat its "
            f"creator | length | first line said | on-screen text | hook pattern):\n{table('talking')}\n\n"
            "Slide posts, for the on-screen text (their ratios run far higher than videos', so compare within a group "
            f"only):\n{table('slides')}\n\n"
            f"The winning reels and Shorts here run {f'{length} s at the median' if length else 'about 30-45 s'}.\n\n"
            f"Make up to {clips} clips.")


def word_times(transcript):
    """Every word with an estimated start and end. Auto-captions overlap (a line stays up while the next one is said), so
    each line's words are spread evenly from its start to the next line's start."""
    segments = sorted(transcript["segments"], key=lambda s: s["start"])
    words = []
    for i, seg in enumerate(segments):
        end = max(segments[i + 1]["start"] if i + 1 < len(segments) else seg["end"], seg["start"] + 0.2)
        parts = seg["text"].split()
        step = (end - seg["start"]) / max(len(parts), 1)
        words += [{"w": w, "n": _norm(w), "t0": seg["start"] + k * step, "t1": seg["start"] + (k + 1) * step}
                  for k, w in enumerate(parts)]
    return words


def _norm(word):
    """A word for matching: lower case, letters, digits and apostrophes; "" for speaker marks (>>) and [music]-style tags."""
    return "" if word.startswith("[") else re.sub(r"[^a-z0-9']", "", word.lower())


def _locate(words, quote, near, first, window=25.0, k=6):
    """The index of the quote's first word (first=True) or last word in the transcript, searching within window seconds
    of near. None when no stretch matches at least 60% of the quote's first (or last) k words."""
    q = [t for t in (_norm(w) for w in (quote or "").split()) if t]
    q = q[:k] if first else q[-k:]
    if not q:
        return None
    best = None
    for i, w in enumerate(words):
        if not w["n"] or abs(w["t0"] - near) > window:
            continue
        j, hits, idx = i, 0, []
        for token in q:
            while j < len(words) and not words[j]["n"]:
                j += 1
            if j == len(words):
                break
            hits += words[j]["n"] == token
            idx.append(j)
            j += 1
        score = hits / len(q) - abs(w["t0"] - near) / 1000  # ties go to the stretch nearest where the AI put it
        if idx and (best is None or score > best[0]):
            best = (score, idx[0] if first else idx[-1])
    return best[1] if best and best[0] >= 0.6 else None


def _sentence_edge(words, t, start, reach=8.0):
    """Widen a cut to whole sentences: the start of the sentence that t falls in (start=True), or the end of it. A
    sentence starts after a full stop, question or exclamation mark or a speaker change (>>) and ends on one of those
    marks. Looks back (or ahead) up to reach seconds, else keeps the nearest word's edge."""
    if start:
        edges = [w["t0"] for i, w in enumerate(words) if w["n"] and t - reach <= w["t0"] <= t + 0.5
                 and (i == 0 or words[i - 1]["w"] == ">>" or words[i - 1]["w"].endswith((".", "?", "!")))]
        return max(edges) if edges else _nearest(words, t, "t0")
    edges = [w["t1"] for w in words if w["n"] and t - 0.5 <= w["t1"] <= t + reach and w["w"].endswith((".", "?", "!"))]
    return min(edges) if edges else _nearest(words, t, "t1")


def _nearest(words, t, key):
    spoken = [w[key] for w in words if w["n"]]
    return min(spoken, key=lambda x: abs(x - t)) if spoken else t


def _spoken(words, start, end):
    return " ".join(w["w"] for w in words if start <= (w["t0"] + w["t1"]) / 2 < end and w["w"] != ">>")


def _replay(replay, segments):
    """The clip's mean most-replayed intensity over the video's mean (1.0 = as replayed as the video overall)."""
    if not replay:
        return None
    covered = [m["intensity"] for m in replay if any(m["start"] < seg["end"] and m["end"] > seg["start"] for seg in segments)]
    average = statistics.mean(m["intensity"] for m in replay)
    return round(statistics.mean(covered) / average, 2) if covered and average else None


def cut(c, words, duration):
    """The clip's segments, aligned to the transcript: the first starts on the first word of its spoken hook and the last
    ends on the last word of its closing line (both as quoted), and the edges between them land on sentence edges.
    Returns (segments, problems)."""
    raw = []
    for seg in (c.get("segments") or [])[:MAX_SEGMENTS]:
        try:
            raw.append([max(0.0, float(seg["start"])), min(float(seg["end"]), duration)])
        except (KeyError, TypeError, ValueError):
            continue
    if not raw:
        return [], []
    problems = []
    for k, seg in enumerate(raw):
        seg[0] = _sentence_edge(words, seg[0], True)
        seg[1] = _sentence_edge(words, seg[1], False)
    i = _locate(words, c.get("spoken_hook"), raw[0][0], True)
    if i is None:
        problems.append("The planned first line wasn't found where the clip starts: check the opening")
    else:
        raw[0][0] = words[i]["t0"]
    i = _locate(words, c.get("ends_on"), raw[-1][1], False)
    if i is None:
        problems.append("The planned last line wasn't found where the clip ends: check the ending")
    else:
        raw[-1][1] = words[i]["t1"]
    segments = [{"start": round(max(0.0, a), 2), "end": round(min(duration, b), 2)} for a, b in raw if b - a >= MIN_SEGMENT_S]
    return segments, problems


def clean(result, src, evidence, clips):
    """Align each clip to the transcript, drop overlapping and broken clips, and add what it says, its length, its replay
    level and the winner it follows."""
    words, duration = word_times(src["transcript"]), src["duration"]
    by_id = {e["id"]: e for e in evidence}
    out, taken = [], []
    for c in sorted((c for c in result.get("clips") or [] if isinstance(c, dict)), key=lambda c: c.get("rank") or 99):
        segments, problems = cut(c, words, duration)
        if not segments:
            continue
        length = round(sum(s["end"] - s["start"] for s in segments), 1)
        if not MIN_CLIP_S <= length <= MAX_CLIP_S:
            continue
        span = (min(s["start"] for s in segments), max(s["end"] for s in segments))
        if any(span[0] < t[1] and t[0] < span[1] for t in taken):
            continue  # overlaps a better clip
        taken.append(span)
        follows = by_id.get(c.get("follows"))
        out.append({"rank": len(out) + 1, "idea": c.get("idea"), "segments": segments, "length_s": length,
                    "cold_open": len(segments) > 1, "spoken_hook": c.get("spoken_hook"), "on_screen": c.get("on_screen"),
                    "follows": {k: follows[k] for k in ("id", "who", "url", "kind", "ratio", "against", "said", "on_screen")}
                    if follows else None, "hook_pattern": c.get("hook_pattern"), "ends_on": c.get("ends_on"),
                    "title": (c.get("title") or "")[:100], "caption": c.get("caption"), "why": c.get("why"),
                    "check": c.get("check") or "", "said": " … ".join(_spoken(words, s["start"], s["end"]) for s in segments),
                    "replay": _replay(src["replay"], segments), "problems": problems})
        if len(out) == clips:
            break
    return out


def build(project_id, vid, clips, about, model):
    client = ScrapeCreators(scrapecreators_key())
    src = source_video(client, vid)
    evidence = hook_evidence(project_id)
    result, cost = llm.ask_json(CLIP_SYSTEM, [("text", _prompt(src, evidence, clips, about))], model, 8000, 0.4)
    planned = clean(result, src, evidence, clips)
    if not planned:
        raise RuntimeError("The AI found no clip that stands alone in this video")
    return {"source": {k: src[k] for k in ("shortcode", "url", "username", "title", "duration", "views", "posted")},
            "clips": planned, "skipped": result.get("skipped"), "evidence": len(evidence),
            "winning_length_s": winning_length(evidence), "notes": src["notes"],
            "credits_used": src["credits_used"], "model": llm.label(model), "cost": cost}


# ---- the brief ----

def _when(segments):
    parts = [f"{_clock(s['start'])}–{_clock(s['end'])}" for s in segments]
    return parts[0] if len(parts) == 1 else f"{parts[0]} (cold open), then " + ", then ".join(parts[1:])


def markdown(plan):
    """The clip plan as a Markdown brief: per clip, the cut, the hook (said and on screen), the title and caption."""
    src = plan["source"]
    out = [f"# Clips from \"{src['title']}\"", "",
           f"[{db.who(src['username'])}]({src['url']}) · {_clock(src['duration'])} long"
           + (f" · {src['views']:,} views" if src.get("views") else ""), "",
           f"{len(plan['clips'])} clips, best first. Each one opens on its strongest line and ends on its payoff. The hook "
           f"on screen is modelled on the niche's short-form winners ({plan['evidence']} reels, Shorts and slideshows that "
           f"beat their creators).", "",
           "**Before posting:** only post clips of a video you own, or one whose creator has agreed to clipping "
           "(a sponsorship or clipping deal). Check each clip's \"Check\" line.", ""]
    for c in plan["clips"]:
        follows = c.get("follows")
        model = (f"[{re.sub(r' [(](YouTube|TikTok)[)]$', '', follows['who'])}'s {KIND_LABEL.get(follows['kind'], follows['kind'])}]"
                 f"({follows['url']}) ({follows['ratio']}× {follows['against']})" if follows else "—")
        out += [f"## {c['rank']}. {c['title'] or c['idea']}", "", c.get("idea") or "", "",
                "| | |", "| --- | --- |",
                f"| Cut | {_when(c['segments'])} · {c['length_s']:.0f} s |",
                f"| Hook, said (first 3 s) | \"{c['spoken_hook']}\" |",
                f"| Hook, on screen | **{c['on_screen']}** |",
                f"| Modelled on | {model}{' · ' + c['hook_pattern'] if c.get('hook_pattern') else ''} |",
                f"| Ends on | \"{c['ends_on']}\" |",
                f"| Shorts title | {c['title']} |",
                f"| TikTok / Instagram caption | {c['caption']} |",
                f"| Why it should work | {c['why']}" + (f" Replayed {c['replay']}× the video's average." if c.get("replay") else "") + " |"]
        if c.get("check") or c.get("problems"):
            out.append(f"| Check | {' '.join(filter(None, [c.get('check')] + c.get('problems', [])))} |")
        out += ["", f"> {c['said']}", ""]
    if plan.get("skipped"):
        out += ["**Left out:** " + plan["skipped"], ""]
    return "\n".join(out)
