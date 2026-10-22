"""Turn a week plan into briefs: the content idea and the script, as Markdown, for whoever films and edits next.

Placeholders stay as [[...]] so they're easy to find and replace. Outlier ids the planner cites become @handles.
"""

import json
import re
from datetime import date

from . import db
from .ai import SEALCAM_KEYS
from .planner import reference_scenes

SEALCAM_NAMES = {"S": "Subject", "E": "Environment", "A": "Action", "L": "Lighting", "Ca": "Camera", "M": "Metatokens"}


def _label(value):
    return str(value).replace("_", " ") if value not in (None, "", "none", "unknown") else ""


def _pct(p):
    return "n/a" if p is None else f"{p * 100:.1f}%"


def _day(iso):
    d = date.fromisoformat(iso)
    return f"{d:%a} {d.day} {d:%b %Y}"


def _slug(text):
    text = re.sub(r"\[\[.*?\]\]", "", text or "").lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60].rstrip("-") or "post"


def _sources(shortcodes):
    if not shortcodes:
        return {}
    with db.connect() as conn:
        rows = conn.execute(f"""SELECT o.shortcode, MAX(o.ratio) AS ratio, MAX(o.basis) AS basis, r.username, r.url FROM outliers o
                                JOIN reels r ON r.shortcode = o.shortcode
                                WHERE o.shortcode IN ({",".join("?" * len(shortcodes))}) GROUP BY o.shortcode""",
                             list(shortcodes)).fetchall()
    return {r["shortcode"]: dict(r) for r in rows}


def _cards(shortcodes):
    """Each reference reel's teardown card: fields, audio and caption."""
    if not shortcodes:
        return {}
    with db.connect() as conn:
        rows = conn.execute(f"SELECT shortcode, data FROM teardowns WHERE status='done' AND shortcode IN "
                            f"({','.join('?' * len(shortcodes))})", list(shortcodes)).fetchall()
    out = {}
    for r in rows:
        d = json.loads(r["data"])
        out[r["shortcode"]] = {"fields": {k: v.get("value") for k, v in d["fields"].items()}, "music": d.get("music") or {},
                               "caption": d.get("caption")}
    return out


def _card_markdown(src, card):
    f, music = card["fields"], card["music"]
    st = f.get("stats") or {}
    num = lambda n: f"{n:,}" if isinstance(n, (int, float)) else None
    stats = [f"{num(st.get('views'))} views" if st.get("views") else None,
             f"{num(st.get('followers'))} followers ({src['ratio']}×)" if st.get("followers") else None,
             f"{num(st.get('likes'))} likes" if st.get("likes") is not None else None,
             f"{num(st.get('comments'))} comments" if st.get("comments") is not None else None,
             f"{round(st['duration_s'])} s" if st.get("duration_s") else None,
             f"posted {_day(st['posted'][:10])}" if st.get("posted") else None]
    hook = [f"said “{f['verbal_hook']}”" if f.get("verbal_hook") else None,
            f"on screen “{f['written_hook']}”" if f.get("written_hook") else None,
            f"shows {f['visual_hook']}" if f.get("visual_hook") else None]
    kinds = [(k, _label(f.get(k))) for k in ("hook_pattern", "format", "angle", "video_type", "delivery", "story_type", "complexity")]
    pace = [f.get("structure_pattern"), f"{f['cuts']} hard cuts" if f.get("cuts") is not None else None,
            f"average shot {f['avg_shot_s']} s" if f.get("avg_shot_s") else None,
            f"{f['word_count']} words ({f['words_per_second']}/s)" if f.get("word_count") else None]
    cta = [_label(f.get("cta_type")), _label(f.get("cta_mechanic")), f"keyword “{f['cta_keyword']}”" if f.get("cta_keyword") else None]
    if music.get("uses_original_audio"):
        audio = "original audio (the creator's own recording)"
    elif music.get("song_name"):
        audio = f"“{music['song_name']}” by {music.get('artist_name') or 'unknown'}"
    else:
        audio = _label(f.get("audio")) or None
    caption = (card.get("caption") or "").split("\n")[0][:200]
    lines = [("Stats", " · ".join(x for x in stats if x)),
             ("Why it's a reference", "a doubled-down template: the account keeps posting it and it keeps working"
              if src.get("basis") == "template" else f"it passed the outlier test ({src['ratio']}× the creator's followers)"),
             ("Hook", " · ".join(x for x in hook if x)),
             ("Type", " · ".join(f"{_label(k).capitalize()}: {v}" for k, v in kinds if v)),
             ("Structure", " · ".join(str(x) for x in pace if x)),
             ("What it teaches", f.get("value_summary")),
             ("Call to action", ", ".join(x for x in cta if x) + (f": “{f['cta_text']}”" if f.get("cta_text") else "")),
             ("Series", f"{_label(f.get('series_type')) or 'yes'}" + (f", marker “{f['episode_marker']}”" if f.get("episode_marker") else "")) if f.get("is_series") else ("Series", None),
             ("Audio", audio),
             ("Caption", f"“{caption}”" if caption else None)]
    return [f"- **{k}:** {v}" for k, v in lines if v]


def _handles(text, sources):
    text = str(text or "")
    for shortcode, s in sources.items():
        text = text.replace(shortcode, "@" + s["username"])
    return text


def _sealcam(item, t):
    return [f"- **{k} ({SEALCAM_NAMES[k]}):** {t(item.get(k))}" for k in SEALCAM_KEYS if item.get(k)]


def post_markdown(post, rates, sources, refs=None, level=1, cards=None):
    h = "#" * level
    t = lambda text: _handles(text, sources)
    hook, cta = post.get("hook") or {}, post.get("cta") or {}
    odds = post.get("odds") or {}
    meta = [_day(post["date"]), post["funnel"].upper(), _label(post.get("content_type")).capitalize(),
            _label(post.get("format")).capitalize(), f"about {post['length_s']} s" if post.get("length_s") else ""]
    style = ", ".join(x for x in (_label(post.get("complexity")), _label(post.get("delivery")),
                                  f"{_label(post.get('story_type'))} story" if _label(post.get("story_type")) else "") if x)
    out = [f"{h} {t(post.get('title'))}", "", " · ".join(x for x in meta if x), "",
           f"{h}# The idea", "",
           f"- **Topic:** {t(post.get('topic'))}",
           f"- **Angle:** {_label(post.get('angle')).capitalize()} · **Hook pattern:** {_label(post.get('hook_pattern')).capitalize()}"
           + (f" · **Style:** {style}" if style else "")]
    if post.get("series_marker"):
        out.append(f"- **Series:** {post['series_marker']}")
    out += [f"- **Odds:** {_pct(odds.get('p5'))} chance of a 5× outlier (this niche's base rate is {_pct(rates.get('p5'))}), "
            f"rated {odds.get('band', 'n/a')}, {odds.get('confidence', 'low')} confidence. "
            f"{_pct(odds.get('p1'))} to beat your follower count, {_pct(odds.get('p2'))} to reach 2×, {_pct(odds.get('p10'))} to reach 10×."]
    factors = odds.get("factors") or {}
    if odds.get("multiplier") is not None:  # the same reasoning the app shows under the odds
        out.append(f"  - {odds['multiplier']}× the niche base rate: evidence ×{factors.get('evidence')} · funnel stage ×{factors.get('funnel')}"
                   + (f" · its sources median {factors['source_median_ratio']}×" if factors.get("source_median_ratio") else ""))
        out += [f"  - {_label(s['attr']).capitalize()} “{_label(s['value'])}”: used by {s['count']} of {s['of']} outliers"
                for s in odds.get("support") or []]
    out.append(f"- **Why it should work:** {t(post.get('why'))}")
    borrowed = [sources[s] for s in post.get("source_outliers") or [] if s in sources]
    if borrowed:
        out.append("- **Borrows its structure from:**")
        out += [f"  - @{s['username']}, {s['ratio']}× their followers: {s['url']}" for s in borrowed]
    out += [f"- **Risk:** {t(post.get('risk'))}", ""]

    needs = post.get("needs_from_you") or []
    if needs:
        out += [f"{h}# Before you film", "", "Replace every [[placeholder]] in the script with your own facts:", ""]
        out += [f"- {t(n)}" for n in needs] + [""]

    out += [f"{h}# Script", "", f"{h}## Hook (first 3 seconds)", "",
            f"- **Say:** “{t(hook.get('verbal'))}”",
            f"- **On screen:** {t(hook.get('written'))}",
            f"- **Show:** {t(hook.get('visual'))}", "",
            f"{h}## Beats", ""]
    for i, beat in enumerate(post.get("beats") or [], 1):
        out.append(f"{i}. **{beat.get('label')}**")
        out += [f"   - {k}: {t(beat.get(key))}" for k, key in (("Say", "say"), ("Film", "show"), ("Edit", "edit")) if beat.get(key)]
    tags = " ".join("#" + str(x).lstrip("#") for x in post.get("hashtags") or [])
    cta_kind = ", ".join(dict.fromkeys(x for x in (_label(post.get("cta_type")), _label(cta.get("mechanic"))) if x))
    out += ["", f"{h}## Close and post", "",
            f"- **Call to action:** “{t(cta.get('line'))}”"
            + (f" ({cta_kind})" if cta_kind else ""),
            f"- **Caption:** {t(post.get('caption_first_line'))}"]
    if tags:
        out.append(f"- **Hashtags:** {tags}")
    shots = post.get("shots") or []
    if shots:
        out += ["", f"{h}# Shot list (SEALCaM)", "",
                "One shot per camera setup or cut, in order. Each borrows its shot grammar from a scene in the reference "
                "breakdown below; the subject and setting are yours.", ""]
        for i, shot in enumerate(shots, 1):
            head = " · ".join(x for x in (f"Shot {i}", shot.get("beat"), f"about {shot['duration_s']:g} s" if shot.get("duration_s") else "") if x)
            out += [f"{h}## {head}", ""]
            if shot.get("say"):
                out.append(f"- **Say:** “{t(shot['say'])}”")
            if shot.get("on_screen_text"):
                out.append(f"- **On screen:** {t(shot['on_screen_text'])}")
            out += _sealcam(shot, t)
            if shot.get("reference"):
                out.append(f"- **Borrowed from:** {t(shot['reference'])}")
            out.append("")
    says = [t(b["say"]) for b in post.get("beats") or [] if b.get("say")]
    if says:
        out += ["", f"{h}# Teleprompter", "", "Just the words, in order.", "", *[x for s in says for x in (s, "")]]
    for sc_id in post.get("source_outliers") or []:
        if (refs or {}).get(sc_id) and sources.get(sc_id):
            out += [""] + reference_markdown(sources[sc_id], refs[sc_id], level, (cards or {}).get(sc_id))
    return "\n".join(out).rstrip() + "\n"


def reference_markdown(src, ref, level=1, card=None):
    h = "#" * level
    out = [f"{h}# Reference breakdown: @{src['username']} ({src['ratio']}×)", "", src["url"], ""]
    if card:
        out += _card_markdown(src, card) + [""]
    out += ["Scene by scene in SEALCaM. A scene that continues the same shot is a segment of a long hold.", ""]
    for sc in ref["scenes"]:
        how = "hard cut" if sc.get("cut", True) else "same shot continues"
        n = sc.get("flash_cuts") or 0
        flashes = f" · {n} flash cut{'' if n == 1 else 's'}" if n else ""
        out += [f"{h}## Scene {sc['i']} · {sc['start']:.1f}–{sc['end']:.1f} s · {sc.get('beat') or 'n/a'} · {how}{flashes}", ""]
        if sc.get("said"):
            out.append(f"- **Said:** “{sc['said']}”")
        if sc.get("on_screen_text"):
            out.append(f"- **On screen:** {sc['on_screen_text']}")
        out += _sealcam(sc, lambda x: x) + [""]
    return out


def plan_exports(project_id, data):
    """{"week": {...}, "posts": {slot: {...}}}, each with a filename and its Markdown."""
    posts, rates = data["posts"], data.get("rates") or {}
    ids = {s for p in posts for s in p.get("source_outliers") or []}
    sources, refs, cards = _sources(ids), reference_scenes(ids), _cards(ids)
    with db.connect() as conn:
        project = conn.execute("SELECT name, niche FROM projects WHERE id=?", (project_id,)).fetchone()
    first = posts[0]["date"] if posts else date.today().isoformat()
    week = [f"# Week of {_day(first)}", "",
            f"{len(posts)} posts for {project['niche'] or project['name'] if project else 'this niche'}, adapted from "
            f"{data.get('teardowns_used')} teardowns of viral outliers. Odds use this niche's base rates from "
            f"{rates.get('reels')} scanned reels: {_pct(rates.get('p1'))} beat the creator's follower count, "
            f"{_pct(rates.get('p2'))} reach 2×, {_pct(rates.get('p5'))} reach 5×, {_pct(rates.get('p10'))} reach 10×.", "",
            "| Day | Post | Funnel | Format | Chance of a 5× outlier |", "|---|---|---|---|---|"]
    for p in posts:
        title = _handles(p.get("title"), sources).replace("|", "/")
        week.append(f"| {_day(p['date'])} | {title} | {p['funnel'].upper()} | {_label(p.get('format')).capitalize()} | "
                    f"{_pct((p.get('odds') or {}).get('p5'))} ({(p.get('odds') or {}).get('band', 'n/a')}) |")
    week.append("")
    for p in posts:  # each source's breakdown appears once, at the end, rather than under every post using it
        week += ["---", "", post_markdown(p, rates, sources, level=2)]
    used = [s for s in dict.fromkeys(s for p in posts for s in p.get("source_outliers") or []) if s in refs and s in sources]
    if used:
        week += ["---", "", "# Reference breakdowns", "",
                 "The outliers this week borrows from, scene by scene. Shots in the shot lists name the scene they borrow from.", ""]
        for s in used:
            week += reference_markdown(sources[s], refs[s], level=2, card=cards.get(s)) + [""]
    return {
        "week": {"filename": f"week-of-{first}.md", "markdown": "\n".join(week).rstrip() + "\n"},
        "posts": {p["slot"]: {"filename": f"{p['date']}-{_slug(p.get('title'))}.md",
                              "markdown": post_markdown(p, rates, sources, refs, cards=cards)} for p in posts},
    }
