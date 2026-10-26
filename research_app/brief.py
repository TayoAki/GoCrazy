"""Turn a week plan into briefs: the content idea and the script, as Markdown, for whoever films and edits next.

Placeholders stay as [[...]] so they're easy to find and replace. Outlier ids the planner cites become @handles.
"""

import json
import re
from datetime import date

from . import db, doubledown, madlibs, textstyle
from .ai import SEALCAM_KEYS
from .planner import reference_scenes

SEALCAM_NAMES = {"S": "Subject", "E": "Environment", "A": "Action", "L": "Lighting", "Ca": "Camera", "M": "Metatokens"}
KIND_LABEL = {"reel": "reel", "carousel": "Instagram carousel", "slideshow": "TikTok slideshow", "video": "YouTube video",
              "short": "YouTube Short"}


def _against(src):
    """What a source's ratio is measured against."""
    return "their channel's median" if src.get("measure") == "median" else "their followers"


def _clock(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 60}:{seconds % 60:02d}"


def _first_up(text):
    return text[:1].upper() + text[1:]


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
        rows = conn.execute(f"""SELECT o.shortcode, MAX(o.ratio) AS ratio, MAX(o.basis) AS basis, MAX(o.measure) AS measure,
                                       r.username, r.url, r.kind FROM outliers o
                                JOIN reels r ON r.shortcode = o.shortcode
                                WHERE o.shortcode IN ({",".join("?" * len(shortcodes))}) GROUP BY o.shortcode""",
                             list(shortcodes)).fetchall()
    # "who" names the account in free text (with "(TikTok)"); "handle" goes next to a kind that already says TikTok.
    return {r["shortcode"]: {**dict(r), "who": db.who(r["username"]), "handle": "@" + db.handle(r["username"])} for r in rows}


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
                               "caption": d.get("caption"), "madlib": d.get("madlib")}
    return out


def _card_markdown(src, card):
    f, music = card["fields"], card["music"]
    st = f.get("stats") or {}
    num = lambda n: f"{n:,}" if isinstance(n, (int, float)) else None
    stats = [(f"about {num(st.get('views'))} views (estimated from likes)" if st.get("views_estimated") else
              f"{num(st.get('views'))} views") if st.get("views") else None,
             (f"{num(st.get('followers'))} subscribers, {src['ratio']}× the channel's median of {num(st.get('typical'))}"
              if src.get("measure") == "median" else f"{num(st.get('followers'))} followers ({src['ratio']}×)") if st.get("followers") else None,
             f"{num(st.get('likes'))} likes" if st.get("likes") is not None else None,
             f"{num(st.get('comments'))} comments" if st.get("comments") is not None else None,
             f"{num(st.get('saves'))} saves" if st.get("saves") is not None else None,
             f"{st['slides']} slides" if st.get("slides") else None,
             f"{round(st['duration_s'])} s" if st.get("duration_s") else None,
             f"posted {_day(st['posted'][:10])}" if st.get("posted") else None]
    youtube = src.get("kind") in ("video", "short")
    hook = [f"title “{f['written_hook']}” ({f['title_pattern']})" if src.get("kind") == "video" and f.get("written_hook") else None,
            f"thumbnail: {f['visual_hook']}" + (f", with the text “{f['thumbnail_text']}”" if f.get("thumbnail_text") else "")
            if src.get("kind") == "video" and f.get("visual_hook") else None,
            f"said “{f['verbal_hook']}”" if f.get("verbal_hook") else None,
            f"on screen “{f['written_hook']}”" if f.get("written_hook") and src.get("kind") != "video" else None,
            f"shows {f['visual_hook']}" if f.get("visual_hook") and src.get("kind") != "video" else None]
    kinds = [(k, _label(f.get(k))) for k in ("hook_pattern", "format", "carousel_type", "angle", "video_type", "delivery",
                                              "story_type", "complexity")]
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
             ("Why it's a reference", "; and ".join(x for x in (
                 _copied(src.get("replicated")),
                 "a doubled-down template: the account keeps posting it and it keeps working" if src.get("basis") == "template"
                 else None if src.get("basis") == "replicated"
                 else f"it passed the outlier test ({src['ratio']}× {'its channel' + chr(39) + 's median video' if src.get('measure') == 'median' else 'the creator' + chr(39) + 's followers'}"
                 + (", from views estimated from likes)" if src.get("measure") == "likes" else ")")) if x)),
             ("Hook", " · ".join(x for x in hook if x)),
             ("Type", " · ".join(f"{_label(k).capitalize()}: {v}" for k, v in kinds if v)),
             ("Structure", " · ".join(str(x) for x in pace if x)),
             ("What it teaches", f.get("value_summary")),
             ("Intro", f.get("intro") if youtube else None),
             ("Keeps people watching", f.get("retention") if youtube else None),
             ("Most rewatched", f.get("rewatch") if youtube else None),
             ("Sponsor or plug", f.get("sponsor") if youtube else None),
             ("Call to action", ", ".join(x for x in cta if x) + (f": “{f['cta_text']}”" if f.get("cta_text") else "")),
             ("Series", f"{_label(f.get('series_type')) or 'yes'}" + (f", marker “{f['episode_marker']}”" if f.get("episode_marker") else "")) if f.get("is_series") else ("Series", None),
             ("Audio", audio),
             ("Caption", f"“{caption}”" if caption else None)]
    return [f"- **{k}:** {v}" for k, v in lines if v]


def _copied(rep):
    """One line on a format several creators copy, or None."""
    if not rep:
        return None
    what = f"the phrase “{rep['signature']}”" if rep["how"] == "phrase" else f"the hook “{rep['signature']}”"
    return (f"a format {rep['creators']} creators copy ({what}); {rep['winners']} of them get "
            f"{rep['median_lift']}× their own typical post or more with it" if rep.get("median_lift") else
            f"a format {rep['creators']} creators copy ({what}), and {rep['winners']} of them beat their follower count with it")


def _madlib_markdown(m, h):
    """The reference's own script as fill-in-the-blank templates: original line, then its madlib."""
    out = [f"{h}## Madlib", "", f"Pattern: {m.get('pattern')}", ""]
    rows = [(f"{k.capitalize()} hook", v) for k, v in (m.get("hooks") or {}).items() if v and v.get("template")]
    rows += [(x.get("beat") or "Line", x) for x in m.get("spoken") or []]
    rows += [("On screen", x) for x in m.get("on_screen") or []]
    if (m.get("caption") or {}).get("template"):
        rows.append(("Caption", m["caption"]))
    for label, x in rows:
        out += [f"- **{label}:** `{x.get('template')}`"] + ([f"  - Original: “{x['original']}”"] if x.get("original") else [])
    if m.get("slots"):
        out += ["", "Slots:", ""] + [f"- `{{{{{s.get('name')}:{s.get('type')}}}}}`: {s.get('rule')}" + (f" (original: “{s['example']}”)" if s.get("example") else "")
                                     for s in m["slots"]]
    variables = madlibs.reference_sheet(m)["variables"]
    if variables:
        out += ["", "Variables (the original's values; write yours in the last column, or change them in the app's madlib editor):", "",
                "| Variable | Original value | Your value |", "|---|---|---|"]
        out += [f"| `{v['slot']}` | {v['value'].replace('|', '/')} | |" for v in variables]
    return out


def _handles(text, sources):
    text = str(text or "")
    for shortcode, s in sources.items():
        text = text.replace(shortcode, s["who"])
    return text


def _sealcam(item, t):
    return [f"- **{k} ({SEALCAM_NAMES[k]}):** {t(item.get(k))}" for k in SEALCAM_KEYS if item.get(k)]


def post_markdown(post, rates, sources, refs=None, level=1, cards=None):
    h = "#" * level
    t = lambda text: _handles(text, sources)
    hook, cta = post.get("hook") or {}, post.get("cta") or {}
    odds = post.get("odds") or {}
    slides = post.get("post_kind") in ("carousel", "slideshow")
    long_video = post.get("post_kind") == "video"
    length = (f"about {round(post['length_s'] / 60)} min" if long_video else f"about {post['length_s']} s") if post.get("length_s") else ""
    meta = [_day(post["date"]), post["funnel"].upper(), _label(post.get("content_type")).capitalize(),
            _first_up(KIND_LABEL[post["post_kind"]]) + f" of {len(post.get('beats') or [])} slides" if slides
            else " · ".join(x for x in (KIND_LABEL[post["post_kind"]] if post.get("post_kind") in ("video", "short") else "",
                                        _label(post.get("format")).capitalize()) if x), length]
    style = ", ".join(x for x in (_label(post.get("complexity")), _label(post.get("delivery")),
                                  f"{_label(post.get('story_type'))} story" if _label(post.get("story_type")) else "") if x)
    out = [f"{h} {t(post.get('title'))}", "", " · ".join(x for x in meta if x), "",
           f"{h}# The idea", "",
           f"- **Topic:** {t(post.get('topic'))}",
           (f"- **Carousel type:** {_label(post.get('carousel_type')).capitalize()} · " if post.get("carousel_type") else "- ")
           + f"**Angle:** {_label(post.get('angle')).capitalize()} · **Hook pattern:** {_label(post.get('hook_pattern')).capitalize()}"
           + (f" · **Style:** {style}" if style else "")]
    if post.get("series_marker"):
        out.append(f"- **Series:** {post['series_marker']}")
    rates = rates.get(odds.get("kind") or "reel") or rates.get("reel") or {} if "p5" not in rates else rates
    against = "your channel's median" if rates.get("basis") == "median" else "your follower count"
    out += [f"- **Odds:** {_pct(odds.get('p5'))} chance of a 5× outlier (5× {against}; this niche's base rate for "
            f"{KIND_LABEL.get(odds.get('kind') or 'reel')}s is {_pct(rates.get('p5'))}), "
            f"rated {odds.get('band', 'n/a')}, {odds.get('confidence', 'low')} confidence. "
            f"{_pct(odds.get('p1'))} to beat {against}, {_pct(odds.get('p2'))} to reach 2×, {_pct(odds.get('p10'))} to reach 10×."]
    factors = odds.get("factors") or {}
    if odds.get("multiplier") is not None:  # the same reasoning the app shows under the odds
        out.append(f"  - {odds['multiplier']}× the niche base rate: evidence ×{factors.get('evidence')} · funnel stage ×{factors.get('funnel')}"
                   + (f" · its sources median {factors['source_median_ratio']}×" if factors.get("source_median_ratio") else "")
                   + (f" · a format {factors['replicated_by']} creators copy" if factors.get("replicated_by") else ""))
        out += [f"  - {_label(s['attr']).capitalize()} “{_label(s['value'])}”: used by {s['count']} of {s['of']} outliers"
                for s in odds.get("support") or []]
    out.append(f"- **Why it should work:** {t(post.get('why'))}")
    borrowed = [sources[s] for s in post.get("source_outliers") or [] if s in sources]
    if borrowed:
        out.append("- **Borrows its structure from:**")
        out += [f"  - {s['handle']}'s {KIND_LABEL.get(s.get('kind') or 'reel')}, {s['ratio']}× {_against(s)}"
                + (" (estimated from likes)" if s.get("measure") == "likes" else "")
                + (f", {_copied(s['replicated'])}" if s.get("replicated") else "") + f": {s['url']}" for s in borrowed]
    out += [f"- **Risk:** {t(post.get('risk'))}"]
    if post.get("reuse"):
        out.append(f"- **Check:** this script reuses its reference's own content ({', '.join(post['reuse'])}); swap it for the creator's own.")
    if post.get("copied_value"):
        out.append(f"- **Check:** this script repeats its reference's own advice: {'; '.join(post['copied_value'])}. Replace it with your own.")
    out.append("")

    needs = post.get("needs_from_you") or []
    if needs:
        out += [f"{h}# Before you film", "", "Replace every [[placeholder]] in the script with your own facts:", ""]
        out += [f"- {t(n)}" for n in needs] + [""]

    madlib_from = sources.get(post.get("madlib_source") or "")
    out += [f"{h}# Script", ""]
    if madlib_from:
        out += [f"The {'slides fill' if slides else 'script fills'} the madlib of {madlib_from['handle']}'s "
                f"{KIND_LABEL.get(madlib_from.get('kind') or 'reel')} ({madlib_from['url']}): each line keeps its "
                "frame words and fills its slots with this creator's content.", ""]
    out += [f"{h}## {'Cover (slide 1)' if slides else 'Packaging: the title and thumbnail' if long_video else 'Hook (first 3 seconds)'}", ""]
    for label, key in ((("On the slide", "written"), ("Show", "visual")) if slides else
                       (("Title", "written"), ("Thumbnail", "visual"), ("Thumbnail text", "thumbnail_text"), ("First line", "verbal"))
                       if long_video else (("Say", "verbal"), ("On screen", "written"), ("Show", "visual"))):
        if not hook.get(key):
            continue
        value = t(hook.get(key))
        out.append(f"- **{label}:** " + (f"“{value}”" if key == "verbal" else value))
        if hook.get(f"{key}_template"):
            out.append(f"  - Madlib: `{hook[key + '_template']}`")
    out += ["", f"{h}## {'Slides' if slides else 'Intro, word for word (about the first minute)' if long_video else 'Beats'}", ""]
    for i, beat in enumerate(post.get("beats") or [], 1):
        out.append(f"{i}. **{beat.get('label')}**")
        if beat.get("template"):
            out.append(f"   - Madlib: `{beat['template']}`")
        rows = ((("On the slide", "text"), ("Image", "show"), ("Design", "edit")) if slides else
                (("Say", "say"), ("Film", "show"), ("Edit", "edit")))
        out += [f"   - {k}: {t(beat.get(key))}".replace("\n", " / ") for k, key in rows if beat.get(key)]
    if post.get("sections"):
        out += ["", f"{h}## Outline", "", "| # | Beat | Section | What it covers | Into the next section | Minutes |", "|---|---|---|---|---|---|"]
        out += [f"| {i} | {sec.get('label') or ''} | {t(sec.get('title'))} | {t(sec.get('covers'))} | {t(sec.get('retention'))} | {sec.get('minutes') or ''} |"
                .replace("\n", " ") for i, sec in enumerate(post["sections"], 1)]
    tags = " ".join("#" + str(x).lstrip("#") for x in post.get("hashtags") or [])
    cta_kind = ", ".join(dict.fromkeys(x for x in (_label(post.get("cta_type")), _label(cta.get("mechanic"))) if x))
    out += ["", f"{h}## Close and post", "",
            f"- **Call to action:** “{t(cta.get('line'))}”"
            + (f" ({cta_kind})" if cta_kind else ""),
            f"- **{'Description' if long_video else 'Caption'}:** {t(post.get('caption_first_line'))}"]
    if tags:
        out.append(f"- **Hashtags:** {tags}")
    if post.get("sound"):
        out.append(f"- **Sound:** {t(post['sound'])}")
    shots = post.get("shots") or []
    if shots:
        out += ["", f"{h}# {'Slide list' if slides else 'Shot list'} (SEALCaM)", "",
                "One entry per slide, in order. Each borrows its look from a slide in the reference breakdown below; the "
                "subject and setting are yours." if slides else
                "One shot per camera setup or cut, in order. Each borrows its shot grammar from a scene in the reference "
                "breakdown below; the subject and setting are yours.", ""]
        for i, shot in enumerate(shots, 1):
            head = " · ".join(x for x in (f"{'Slide' if slides else 'Shot'} {i}", shot.get("beat"),
                                          f"about {shot['duration_s']:g} s" if shot.get("duration_s") else "") if x)
            out += [f"{h}## {head}", ""]
            if shot.get("say"):
                out.append(f"- **Say:** “{t(shot['say'])}”")
            if shot.get("on_screen_text"):
                out.append(f"- **On screen:** {t(shot['on_screen_text'])}")
            for rt in shot.get("reference_text") or []:
                out.append(f"- **Text style (match the reference exactly; it said “{rt['text']}”):** {rt['spec']}")
            if shot.get("text_check"):
                out.append(f"- **Check the text:** {'; '.join(shot['text_check'])}")
            out += _sealcam(shot, t)
            if shot.get("reference"):
                ref = shot["reference"].replace(" scene ", " slide ") if slides else shot["reference"]
                out.append(f"- **Borrowed from:** {t(ref)}")
            if shot.get("kept"):
                out.append(f"- **Kept from the reference:** {t(shot['kept'])}")
            if shot.get("changed"):
                out.append(f"- **Changed:** {t(shot['changed'])}")
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
    slides = src.get("kind") in ("carousel", "slideshow")
    out = [f"{h}# Reference breakdown: {src['handle']}'s {KIND_LABEL.get(src.get('kind') or 'reel')} ({src['ratio']}×)", "", src["url"], ""]
    if card:
        out += _card_markdown(src, card) + [""]
        if card.get("madlib"):
            out += _madlib_markdown(card["madlib"], h) + [""]
    if any(sc.get("section") for sc in ref["scenes"]):  # a YouTube video: its chapters, not filmed scenes
        out += ["Section by section: the video's chapters (or even slices of its transcript), each with its beat.", ""]
        for sc in ref["scenes"]:
            out += [f"{h}## {sc.get('chapter') or 'Section ' + str(sc['i'])} · {_clock(sc.get('start'))}–{_clock(sc.get('end'))} · "
                    f"{sc.get('beat') or 'n/a'}", ""]
            out += [x for x in (f"- **Covers:** {sc['summary']}" if sc.get("summary") else None,
                                f"- **Said:** “{sc['said']}”" if sc.get("said") else None) if x] + [""]
        return out
    out += ["Slide by slide in SEALCaM. Slide 1 is the cover." if slides else
            "Scene by scene in SEALCaM. A scene that continues the same shot is a segment of a long hold.", ""]
    for sc in ref["scenes"]:
        if slides:
            out += [f"{h}## Slide {sc['i']} · {sc.get('beat') or 'n/a'}", ""]
        else:
            how = "hard cut" if sc.get("cut", True) else "same shot continues"
            n = sc.get("flash_cuts") or 0
            flashes = f" · {n} flash cut{'' if n == 1 else 's'}" if n else ""
            out += [f"{h}## Scene {sc['i']} · {sc['start']:.1f}–{sc['end']:.1f} s · {sc.get('beat') or 'n/a'} · {how}{flashes}", ""]
        if sc.get("said"):
            out.append(f"- **Said:** “{sc['said']}”")
        if sc.get("on_screen_text"):
            out.append(f"- **On screen:** {sc['on_screen_text']}")
        for b in sc.get("text_blocks") or []:
            out.append(f"- **Text “{b.get('text')}”:** {textstyle.describe(b)}")
        out += _sealcam(sc, lambda x: x) + [""]
    return out


def plan_exports(project_id, data):
    """{"week": {...}, "posts": {slot: {...}}}, each with a filename and its Markdown."""
    posts, rates = data["posts"], data.get("rates") or {}
    by_kind = data.get("rates_by_kind") or {"reel": rates}
    ids = {s for p in posts for s in p.get("source_outliers") or []}
    sources, refs, cards = _sources(ids), reference_scenes(ids), _cards(ids)
    with db.connect() as conn:
        project = conn.execute("SELECT name, niche FROM projects WHERE id=?", (project_id,)).fetchone()
        replicated = doubledown.replicated_by_post(conn, project_id)
    for sc, s in sources.items():
        s["replicated"] = replicated.get(sc)
    first = posts[0]["date"] if posts else date.today().isoformat()
    week = [f"# Week of {_day(first)}", "",
            f"{len(posts)} posts for {project['niche'] or project['name'] if project else 'this niche'}, adapted from "
            f"{data.get('teardowns_used')} teardowns of viral outliers. Odds use this niche's base rates: "
            + "; ".join(f"from {r.get('reels')} scanned {KIND_LABEL.get(k, k)}s"
                        + (" (views estimated from likes)" if r.get("estimated") else "")
                        + f", {_pct(r.get('p1'))} beat {'their channel' + chr(39) + 's median' if r.get('basis') == 'median' else 'the creator' + chr(39) + 's follower count'}, {_pct(r.get('p2'))} reach 2×, "
                        f"{_pct(r.get('p5'))} reach 5×, {_pct(r.get('p10'))} reach 10×" for k, r in by_kind.items()) + ".", "",
            "| Day | Post | Funnel | Format | Chance of a 5× outlier |", "|---|---|---|---|---|"]
    for p in posts:
        title = _handles(p.get("title"), sources).replace("|", "/")
        kind = p.get("post_kind") or "reel"
        shape = _first_up(KIND_LABEL[kind]) if kind != "reel" else _label(p.get("format")).capitalize()
        week.append(f"| {_day(p['date'])} | {title} | {p['funnel'].upper()} | {shape} | "
                    f"{_pct((p.get('odds') or {}).get('p5'))} ({(p.get('odds') or {}).get('band', 'n/a')}) |")
    week.append("")
    for p in posts:  # each source's breakdown appears once, at the end, rather than under every post using it
        week += ["---", "", post_markdown(p, by_kind, sources, level=2)]
    used = [s for s in dict.fromkeys(s for p in posts for s in p.get("source_outliers") or []) if s in refs and s in sources]
    if used:
        week += ["---", "", "# Reference breakdowns", "",
                 "The outliers this week borrows from, scene by scene (a YouTube video section by section). Shots in the shot "
                 "lists name the scene they borrow from.", ""]
        for s in used:
            week += reference_markdown(sources[s], refs[s], level=2, card=cards.get(s)) + [""]
    return {
        "week": {"filename": f"week-of-{first}.md", "markdown": "\n".join(week).rstrip() + "\n"},
        "posts": {p["slot"]: {"filename": f"{p['date']}-{_slug(p.get('title'))}.md",
                              "markdown": post_markdown(p, by_kind, sources, refs, cards=cards)} for p in posts},
    }
