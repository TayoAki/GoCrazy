"""Turn a week plan into briefs: the content idea and the script, as Markdown, for whoever films and edits next.

Placeholders stay as [[...]] so they're easy to find and replace. Outlier ids the planner cites become @handles.
"""

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
        rows = conn.execute(f"""SELECT o.shortcode, MAX(o.ratio) AS ratio, r.username, r.url FROM outliers o
                                JOIN reels r ON r.shortcode = o.shortcode
                                WHERE o.shortcode IN ({",".join("?" * len(shortcodes))}) GROUP BY o.shortcode""",
                             list(shortcodes)).fetchall()
    return {r["shortcode"]: dict(r) for r in rows}


def _handles(text, sources):
    text = str(text or "")
    for shortcode, s in sources.items():
        text = text.replace(shortcode, "@" + s["username"])
    return text


def _sealcam(item, t):
    return [f"- **{k} ({SEALCAM_NAMES[k]}):** {t(item.get(k))}" for k in SEALCAM_KEYS if item.get(k)]


def post_markdown(post, rates, sources, refs=None, level=1):
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
            f"{_pct(odds.get('p1'))} to beat your follower count, {_pct(odds.get('p2'))} to reach 2×, {_pct(odds.get('p10'))} to reach 10×.",
            f"- **Why it should work:** {t(post.get('why'))}"]
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
            out += [""] + reference_markdown(sources[sc_id], refs[sc_id], level)
    return "\n".join(out).rstrip() + "\n"


def reference_markdown(src, ref, level=1):
    h = "#" * level
    out = [f"{h}# Reference breakdown: @{src['username']} ({src['ratio']}×)", "",
           f"{src['url']} · scene by scene in SEALCaM. A scene that continues the same shot is a segment of a long hold.", ""]
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
    sources, refs = _sources(ids), reference_scenes(ids)
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
            week += reference_markdown(sources[s], refs[s], level=2) + [""]
    return {
        "week": {"filename": f"week-of-{first}.md", "markdown": "\n".join(week).rstrip() + "\n"},
        "posts": {p["slot"]: {"filename": f"{p['date']}-{_slug(p.get('title'))}.md",
                              "markdown": post_markdown(p, rates, sources, refs)} for p in posts},
    }
