"""Match a person's own video to the winning videos in the research that look like it: format first, then subject.

    python3 match.py <video> --post briefs/<slug> [--project <id>] [--top 8] [--no-ai] [--fresh]

1. Measures the video: length, shape, how often the shot changes, and whether anyone talks (it transcribes the
   speech, so a talking video takes a minute).
2. Describes it in the teardowns' own terms (format, audio, angle, video type, delivery, story, hook pattern) by
   showing its frames and transcript to the AI the research app uses (the `claude` command or OpenRouter), with the
   same instructions the research gave every outlier. Without an AI, or with --no-ai, it writes the frames and the
   prompt to match/describe.md instead: look at them, write match/video.json yourself, and run it again.
3. Scores every torn-down reel and Short: the same format counts most, then talking vs music, angle, video type and
   story, the subject (shared words), length and pace, and how far the post beat its creator.
4. Writes match/matches.md (each match's numbers, hook, captions, call to action and link, and how the top matches
   are edited), match/sheet.jpg (the person's frames on top, each match's below) and reel.suggested.json, a starting
   reel.json in the layout that fits. The hook in it is left for you: write it in the matches' pattern, from what's
   true about the person's video.

The research database is only read. The person's frames go to data/media/_match/ (where the AI may read them).
"""

import argparse
import json
import math
import os
import re
import sqlite3
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from videokit import cuts, key, probe, words as transcribe  # noqa: E402


def find_repo():
    starts = [Path(os.environ["RESEARCH_REPO"])] if os.environ.get("RESEARCH_REPO") else []
    starts += [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]
    return next((d for d in starts if (d / "research_app" / "server.py").exists()), Path.cwd())


REPO = find_repo()
DB = REPO / "data" / "research.db"
MEDIA = REPO / "data" / "media"
SPEECH = {"original_voice", "voice_plus_music"}
FAMILY = {f: "on camera" for f in ("talking_head", "setting_change", "shot_angle_change", "visual_prop", "multitasking",
                                   "qa", "talking_back_forth", "clone", "whiteboard", "reaction")}
FAMILY.update({"green_screen": "cut out over a picture", "voiceover": "off camera", "audio_broll_text": "off camera"})
LAYOUT = {"talking_head": "talking", "setting_change": "talking", "shot_angle_change": "talking",
          "multitasking": "talking", "qa": "talking", "whiteboard": "talking", "voiceover": "talking",
          "visual_prop": "talking", "green_screen": "green-screen", "audio_broll_text": "text"}
STOP = set("""a an the and or but if of to in on at for with from by is are was were be been it its this that these those
i im i'm me my we our you your he she they them his her their what which who how when where why so just very really
than then there here not no do does did done have has had can could will would should get got make made one two all
about into out up down over more most some any like as also only even much many own same new day days video""".split())


def connect():
    if not DB.exists():
        raise SystemExit(f"No research database at {DB}. Run the research first (research.py).")
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def handle(username):
    return "@" + re.sub(r"^(tt|yt):", "", username or "")


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9']+", (text or "").lower()) if len(w) > 2 and w not in STOP}


def value(fields, name):
    f = fields.get(name)
    return f.get("value") if isinstance(f, dict) else f


# --- 1 and 2: measure and describe the person's video ------------------------------------------------------------

def frames(video, folder, length):
    folder.mkdir(parents=True, exist_ok=True)
    hook = [t / 2 for t in range(6) if t / 2 < length]
    over = [length * (k + 0.5) / 12 for k in range(12)]
    paths = {"hook": [], "overview": []}
    for kind, times in (("hook", hook), ("overview", over)):
        for k, t in enumerate(times):
            dest = folder / f"{kind}_{k + 1:02d}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                            "-vf", "scale='min(720,iw)':-2", "-q:v", "3", str(dest)], check=True)
            paths[kind].append(dest)
    return paths


def lines(said):
    """The transcript as timed sentences, for the prompt and the write-up."""
    out, cur, start = [], [], None
    for k, w in enumerate(said):
        start = w["s"] if start is None else start
        cur.append(w["w"])
        nxt = said[k + 1] if k + 1 < len(said) else None
        if not nxt or re.search(r"[.!?]$", w["w"]) or nxt["s"] - w["e"] > 0.8:
            out.append(f"[{start:.1f}s] {' '.join(cur)}")
            cur, start = [], None
    return out


def measure(video, work):
    info = probe(video)
    length = info["duration"]
    changes = cuts(video)
    said = transcribe(video, work) if info["audio"] else []
    wps = len(said) / length if length else 0
    return {"length_s": round(length, 1), "width": info["width"], "height": info["height"],
            "cuts": len(changes), "avg_shot_s": round(length / (len(changes) + 1), 1),
            "has_speech": len(said) >= 8 and wps > 0.6, "words_per_second": round(wps, 2),
            "transcript": lines(said)}


def describe(video, measured, shots, out, no_ai):
    """The teardown fields for the person's video: from the AI, or from match/video.json written by hand."""
    sys.path.insert(0, str(REPO))
    from research_app import config
    config.load_env()
    from research_app import ai, llm
    text = (f"This is the person's OWN video, not posted yet, so there are no stats or caption. Length "
            f"{measured['length_s']} s, {measured['width']}x{measured['height']}.\n\n"
            f"AUDIO FACTS: {'someone talks (the transcript is their speech)' if measured['has_speech'] else 'no speech found'}"
            f"\n\nTRANSCRIPT:\n" + ("\n".join(measured["transcript"])[:8000] or "(none)") +
            f"\n\nAUTOMATIC PRE-ANNOTATIONS (hints):\n" +
            json.dumps({"cuts": measured["cuts"], "avg_shot_s": measured["avg_shot_s"],
                        "words_per_second": measured["words_per_second"]}))
    parts = [("text", text), ("text", f"HOOK FRAMES (first 3 s, 0.5 s apart, {len(shots['hook'])} images):")]
    parts += [("image", str(p)) for p in shots["hook"]]
    parts += [("text", f"OVERVIEW FRAMES (sampled across the video, {len(shots['overview'])} images, numbered in order):")]
    parts += [("image", str(p)) for p in shots["overview"]]
    if no_ai or not llm.available():
        (out / "describe.md").write_text(
            "# Describe the video by hand\n\nNo AI ran" + (" (--no-ai)" if no_ai else " (no `claude` command or "
            "OPENROUTER_API_KEY)") + ". Look at the frames below, then write `match/video.json` with the keys and the "
            "allowed values the instructions list (at least format, audio, angle, video_type, delivery, story_type, "
            "hook_pattern, topic, value_summary), and run match.py again.\n\n## Instructions\n\n" + ai.SYSTEM +
            "\n\n## What the model would get\n\n" + "\n\n".join(p if k == "text" else f"![]({p})" for k, p in parts))
        raise SystemExit(f"Wrote {out / 'describe.md'}: describe the video there, save match/video.json, run again.")
    print(f"describing the video with {llm.label(config.DEFAULT_SETTINGS['ai_model'])}...", flush=True)
    result, _ = llm.ask_json(ai.SYSTEM, parts, config.DEFAULT_SETTINGS["ai_model"], 2000, 0.2)
    from research_app.annotate import VOCAB
    for name in ("format", "audio", "angle", "video_type", "delivery", "story_type", "hook_pattern"):
        if result.get(name) is not None and result[name] not in VOCAB.get(name, [result[name]]):
            result[name] = None  # off-vocabulary: unknown rather than wrong
    return result


# --- 3: score the research's videos ------------------------------------------------------------------------------

def candidates(conn):
    rows = conn.execute("""
        select t.shortcode, t.data, r.platform, r.kind, r.views, r.comments, r.saves, r.duration, r.username, r.url,
               r.caption, c.followers,
               (select max(o.ratio) from outliers o where o.shortcode = t.shortcode) as ratio,
               (select o.basis from outliers o where o.shortcode = t.shortcode order by o.ratio desc limit 1) as basis,
               (select o.typical from outliers o where o.shortcode = t.shortcode order by o.ratio desc limit 1) as typical,
               (select group_concat(distinct o.project_id) from outliers o where o.shortcode = t.shortcode) as projects
        from teardowns t join reels r on r.shortcode = t.shortcode left join creators c on c.username = r.username
        where r.kind in ('reel', 'short')""").fetchall()
    out = []
    for r in rows:
        fields = (json.loads(r["data"] or "{}").get("fields")) or {}
        if not value(fields, "format"):
            continue
        out.append({**dict(r), "fields": fields, "projects": {int(p) for p in (r["projects"] or "").split(",") if p}})
    return out


TRAITS = (("angle", 1.0), ("story_type", 0.7), ("video_type", 0.7), ("hook_pattern", 0.4), ("delivery", 0.3))


def rarity(cands):
    """How rare each trait value is across the research: a shared rare trait ("transformation", 12 of 264) says far
    more about two videos than a common one ("tip_hack", 125 of 264)."""
    n = len(cands)
    counts = Counter((name, value(c["fields"], name)) for c in cands for name, _ in TRAITS)
    return lambda name, v: math.log((n + 1) / (counts[(name, v)] + 1))


def score(mine, measured, cand, project, rare):
    f = cand["fields"]
    why, s = [], 0.0
    fmt, theirs = mine.get("format"), value(f, "format")
    talking = bool(measured["has_speech"])
    if fmt and fmt == theirs:
        s += 6 if talking else 4  # with talking, the format decides the whole edit
        why.append(f"same format ({fmt.replace('_', ' ')})")
    elif fmt and FAMILY.get(fmt) and FAMILY.get(fmt) == FAMILY.get(theirs):
        s += 1.5 if talking else 3  # with no talking, "talking head" and "visual prop" are both just a person on screen
        why.append(f"also {FAMILY[fmt]}")
    talks = value(f, "audio") in SPEECH
    if talks == talking:
        s += 2
        why.append("talks" if talks else "no talking")
    else:
        s -= 2
    for name, weight in TRAITS:
        v = mine.get(name)
        if v and v not in ("none", "niche_specific") and v == value(f, name):
            s += weight * rare(name, v)
            why.append(f"{name.replace('_', ' ')}: {v.replace('_', ' ')}")
    a = tokens(f"{mine.get('topic')} {mine.get('value_summary')} {' '.join(measured['transcript'])[:400]}")
    b = tokens(f"{value(f, 'topic')} {value(f, 'value_summary')} {(cand['caption'] or '')[:300]}")
    shared = a & b
    if a and b:
        s += 4 * len(shared) / math.sqrt(len(a) * len(b))  # 4 when the words are the same, 0 when none are shared
    if shared:
        why.append("subject: " + ", ".join(sorted(shared)[:5]))
    if cand["duration"] and measured["length_s"]:
        s += math.exp(-abs(math.log(measured["length_s"] / cand["duration"])))
    avg = value(f, "avg_shot_s")
    if avg and measured["avg_shot_s"]:
        s += 0.5 * math.exp(-abs(math.log(measured["avg_shot_s"] / float(avg))))
    if project and project in cand["projects"]:
        s += 1
        why.append("this niche")
    s += min(1.5, 0.5 * math.log(max(1.0, cand["ratio"] or 1)))
    return s, why


# --- 4: write it up ----------------------------------------------------------------------------------------------

def beat(c):
    ratio = c["ratio"] or 0
    if c["platform"] == "youtube":
        return f"{ratio:.1f}× the channel's typical Short ({c['typical']:,.0f} views)" if c["typical"] else f"{ratio:.1f}×"
    note = " (kept as the creator's repeated template)" if c["basis"] == "template" else ""
    return f"{ratio:.1f}× followers{note}"


def edit_summary(top):
    """How the top matches are edited, in counts, to set the layout's options."""
    caps = Counter()
    for c in top:
        style = (value(c["fields"], "captions") or "none").lower()
        caps["word-by-word captions" if "word" in style else "a static text block" if style.startswith("static")
             or "static" in style[:40] else "no captions" if style.startswith("none") else "other text"] += 1
    audio = Counter((value(c["fields"], "audio") or "unknown").replace("_", " ") for c in top)
    ctas = Counter((value(c["fields"], "cta_mechanic") or "none").replace("_", " ") for c in top)
    lengths = [c["duration"] for c in top if c["duration"]]
    shots = [float(value(c["fields"], "avg_shot_s")) for c in top if value(c["fields"], "avg_shot_s")]
    hooks = sum(1 for c in top if value(c["fields"], "written_hook"))
    return {"captions": caps.most_common(), "audio": audio.most_common(), "cta": ctas.most_common(),
            "length_s": round(statistics.median(lengths), 1) if lengths else None,
            "avg_shot_s": round(statistics.median(shots), 1) if shots else None, "written_hook": f"{hooks} of {len(top)}"}


def suggest(mine, measured, top, video, post):
    fmt = mine.get("format") or value(top[0]["fields"], "format")
    layout = LAYOUT.get(fmt, "talking" if measured["has_speech"] else "text")
    if layout == "talking" and not measured["has_speech"]:
        layout = "text"
    styles = " ".join((value(c["fields"], "captions") or "").lower() for c in top[:5])
    try:
        rel = str(Path(video).resolve().relative_to(post.resolve()))
    except ValueError:
        rel = str(Path(video).resolve())
    spec = {"layout": layout, "video": rel, "hook": "",
            "_hook_patterns_that_won": [value(c["fields"], "written_hook") for c in top[:5] if value(c["fields"], "written_hook")],
            "hook_style": "white-box" if "white box" in styles or "white background" in styles
                          else "box" if "black box" in styles or "box" in styles else "outline"}
    if layout == "text":
        spec.update({"second_line": "", "second_line_at": 0.33, "slow": 2.0 if measured["length_s"] < 10 else 1,
                     "headroom": 0})
    else:
        spec.update({"cut_pauses": 0.5, "captions": {"words": 3, "style": "box" if "box" in styles and "outline" not in styles
                     else "outline", "highlight": []}})
        if layout == "green-screen":
            spec["backgrounds"] = [{"src": "assets/<screenshot or photo>.jpg", "at": 0}]
        else:
            spec["broll"] = []
    icon = post / "assets/app-icon-1024.png"
    brand = {}
    if (post / "post.json").exists():
        brand = json.loads((post / "post.json").read_text()).get("brand") or {}
    if icon.exists():
        spec["end_card"] = {"icon": "assets/app-icon-1024.png", "name": brand.get("name", ""),
                            "where": brand.get("where", ""), "seconds": 2.5}
    return spec


def sheet(shots, top, dest):
    """The person's frames on the first row, each match's hook and three moments below, labelled."""
    tw, th, pad = 180, 320, 34
    try:
        font = ImageFont.load_default(size=20)
    except TypeError:
        font = ImageFont.load_default()
    rows = [("YOUR VIDEO", [shots["hook"][0]] + shots["overview"][2:11:3])]
    for k, c in enumerate(top, 1):
        folder = MEDIA / c["shortcode"]
        pics = sorted(folder.glob("hook_*.jpg"))[:1] + sorted(folder.glob("f_*.jpg"))[2::4][:3]
        if not pics and (folder / "cover.jpg").exists():
            pics = [folder / "cover.jpg"]
        rows.append((f"{k}. {handle(c['username'])}  {beat(c).replace('×', 'x')}", pics))
    img = Image.new("RGB", (tw * 4, len(rows) * (th + pad)), "white")
    draw = ImageDraw.Draw(img)
    for r, (label, pics) in enumerate(rows):
        y = r * (th + pad)
        draw.text((8, y + 6), label, fill="black", font=font)
        for k, p in enumerate(pics[:4]):
            try:
                im = Image.open(p).convert("RGB")
            except OSError:
                continue
            im.thumbnail((tw, th))
            img.paste(im, (k * tw + (tw - im.width) // 2, y + pad))
    img.save(dest, quality=85)


def write(mine, measured, top, summary, spec, out, video):
    md = [f"# Outliers that match `{Path(video).name}`", "",
          f"**Your video:** {measured['length_s']} s, {measured['width']}x{measured['height']}, "
          f"{'talking' if measured['has_speech'] else 'no talking'}, a shot change every {measured['avg_shot_s']} s. "
          f"Format: **{(mine.get('format') or 'unknown').replace('_', ' ')}**, audio {mine.get('audio')}, angle "
          f"{mine.get('angle')}, video type {mine.get('video_type')}, story {mine.get('story_type')}.", "",
          f"> {mine.get('topic') or ''}", "", "## The matches", "",
          "Score: how alike the two videos are (the same format counts most, then shared rare traits and subject). "
          "A score well under the top one is a looser match: read its row before copying it.", "",
          "| # | Score | Creator | Beat their size by | Views | Comments | Length | Format | Why it matches |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for k, c in enumerate(top, 1):
        md.append(f"| {k} | {c['score']:.1f} | [{handle(c['username'])}]({c['url']}) | {beat(c)} | {c['views'] or 0:,} | "
                  f"{c['comments'] or 0:,} | {c['duration'] or 0:.0f} s | {(value(c['fields'], 'format') or '').replace('_', ' ')} "
                  f"| {'; '.join(c['why'])} |")
    md += ["", "## How each one is made", ""]
    for k, c in enumerate(top, 1):
        f = c["fields"]
        md += [f"**{k}. {handle(c['username'])}** ({c['platform']} {c['kind']}, `{c['shortcode']}`)",
               f"- On-screen hook: {value(f, 'written_hook') or '(none)'}",
               f"- Spoken hook: {value(f, 'verbal_hook') or '(none)'}",
               f"- Captions: {value(f, 'captions') or '(none)'}",
               f"- Structure: {value(f, 'structure_pattern') or '?'} · audio {value(f, 'audio')} · a shot every "
               f"{value(f, 'avg_shot_s')} s",
               f"- Ask: {value(f, 'cta_mechanic')}" + (f" ({value(f, 'cta_keyword')})" if value(f, 'cta_keyword') else "")
               + (f": {value(f, 'cta_text')}" if value(f, 'cta_text') else ""), ""]
    md += ["## What the top matches have in common", "",
           f"- On-screen hook: {summary['written_hook']}",
           f"- Text: " + ", ".join(f"{n}× {s}" for s, n in summary["captions"]),
           f"- Sound: " + ", ".join(f"{n}× {s}" for s, n in summary["audio"]),
           f"- Ask: " + ", ".join(f"{n}× {s}" for s, n in summary["cta"]),
           f"- Length: median {summary['length_s']} s (yours {measured['length_s']} s); a shot every "
           f"{summary['avg_shot_s']} s (yours {measured['avg_shot_s']} s)", "",
           f"## The layout to use: `{spec['layout']}`", "",
           "`reel.suggested.json` starts it. Write the hook in the pattern of the winners' hooks it lists, from what's "
           "true about this video, fill the blanks, save it as `reel.json` and run `reel.py`. "
           "references/video-layouts.md has every option.", ""]
    if measured["transcript"]:
        md += ["## Your transcript", "", *[f"    {line}" for line in measured["transcript"]], ""]
    (out / "matches.md").write_text("\n".join(md))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--post", required=True, help="the post folder, briefs/<slug>")
    ap.add_argument("--project", type=int, help="the research project for this niche: its posts get a small bonus")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--no-ai", action="store_true", help="write the frames and prompt instead of calling an AI")
    ap.add_argument("--fresh", action="store_true", help="describe the video again even if match/video.json exists")
    args = ap.parse_args()
    video, post = Path(args.video), Path(args.post)
    out = post / "match"
    out.mkdir(parents=True, exist_ok=True)
    conn = connect()
    vkey = key(video)
    print("measuring the video...", flush=True)
    measured = measure(video, post / "out" / "work")
    shots = frames(video, MEDIA / "_match" / vkey, measured["length_s"])
    saved = out / "video.json"
    mine = json.loads(saved.read_text()) if saved.exists() and not args.fresh else None
    if mine and mine.get("_video") not in (None, vkey):
        mine = None  # written for another video
    if not mine:
        mine = describe(video, measured, shots, out, args.no_ai)
        saved.write_text(json.dumps({**mine, "_video": vkey, "_measured": {k: v for k, v in measured.items()
                                                                           if k != "transcript"}}, indent=1))
    ranked, pool = [], candidates(conn)
    rare = rarity(pool)
    for c in pool:
        s, why = score(mine, measured, c, args.project, rare)
        ranked.append({**c, "score": s, "why": why})
    ranked.sort(key=lambda c: -c["score"])
    top = ranked[:args.top]
    summary = edit_summary(top)
    spec = suggest(mine, measured, top, video, post)
    (post / "reel.suggested.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    sheet(shots, top, out / "sheet.jpg")
    write(mine, measured, top, summary, spec, out, video)
    print(f"\nYour video: {(mine.get('format') or 'unknown').replace('_', ' ')}, "
          f"{'talking' if measured['has_speech'] else 'no talking'}, {measured['length_s']} s. Top matches:")
    for k, c in enumerate(top, 1):
        hook = value(c["fields"], "written_hook") or "(no on-screen hook)"
        print(f"{k:2}. {c['score']:4.1f}  {handle(c['username']):24} {beat(c):34} {c['views'] or 0:>10,} views  {hook[:50]}")
    print(f"\nLayout: {spec['layout']}. Wrote {out}/matches.md, {out}/sheet.jpg and {post}/reel.suggested.json")


if __name__ == "__main__":
    main()
