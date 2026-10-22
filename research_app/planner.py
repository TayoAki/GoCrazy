"""Weekly content plan built from the project's teardowns.

The model chooses and adapts proven structures (hook stacks, beats, formats) into new posts for the niche. The odds of
virality are computed here from the scanned reels, never by the model, so every number traces back to data.
"""

import json
import re
import statistics
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import requests

from . import db
from .ai import SEALCAM, SEALCAM_KEYS
from .annotate import BEATS, VOCAB
from .config import openrouter_key

URL = "https://openrouter.ai/api/v1/chat/completions"

# Weekly mix by follower tier: counts from the playbook (video #8), ordered so a shorter week stays balanced.
WEEK_PATTERNS = {
    "new": [("tofu", "follow"), ("mofu", "follow"), ("bofu", "follow"), ("tofu", "freebie"),
            ("mofu", "follow"), ("tofu", "follow"), ("bofu", "follow")],
    "growing": [("tofu", "follow"), ("mofu", "follow"), ("bofu", "follow"), ("tofu", "follow"),
                ("bofu", "paid_offer"), ("tofu", "freebie"), ("bofu", "follow")],
    "established": [("tofu", "follow"), ("mofu", "follow"), ("bofu", "paid_offer"), ("tofu", "follow"),
                    ("bofu", "paid_offer"), ("tofu", "freebie"), ("bofu", "follow")],
}
# Reach adjustments by funnel stage. The playbook's videos say broad TOFU content gets the most views and authority
# content the fewest; these factors are this app's judgement call and are shown with every estimate.
FUNNEL_FACTOR = {"tofu": 1.15, "mofu": 0.9, "bofu": 0.8}
AUTHORITY_FACTOR = 0.75
EVIDENCE_ATTRS = ["hook_pattern", "format", "angle", "video_type", "complexity", "delivery"]
SKIP_VALUES = {None, "", "none", "unknown", "niche_specific"}

RULES = """Hard rules:
1. Borrow STRUCTURE, never CONTENT. Reuse a teardown's hook pattern, beat sequence and format, but write every line new
   for this creator's niche. Never copy a sentence from a teardown. Frame words of a hook pattern ("Is it possible
   to…", "Here's the…") may stay. Never quote song lyrics.
2. Never invent facts about the creator (results, numbers, clients, stories, credentials). Use only facts given in
   ABOUT THE CREATOR. Where a post needs a personal fact you don't have, write a placeholder in double square
   brackets, e.g. [[YOUR CLIENT RESULT: before → after, with a number]].
3. Every post must teach or show something specific (a number, a named step, a concrete example): no fluff, no trends."""

OUTLINE_SYSTEM = """You plan a week of short-form videos (Instagram Reels) for a creator, using teardowns of proven viral
outliers from their niche. Each teardown lists what made a video work: hooks, hook pattern, angle, video type,
delivery, format, beats, CTA.

""" + RULES + """
4. One post per slot, same order, matching the slot's funnel stage, content type and CTA type.
5. Base each post on 1-3 teardowns (by id) whose hook, structure or format it reuses.
6. Spread the week: no format or angle more than twice. Never use the talking_head format: pick an engaging one.
7. Use only these values: angle {angle}; video_type {video_type}; delivery {delivery}; story_type {story_type};
   format {format}; hook_pattern {hook_pattern}; complexity {complexity}.

Reply with ONLY a JSON object {{"posts": [ ... ]}}, each post:
{{"slot": int, "title": "a working title", "topic": str, "angle": str, "video_type": str, "delivery": str,
 "story_type": str|null, "format": str, "hook_pattern": str, "complexity": str, "series_marker": str|null,
 "source_outliers": [teardown ids]}}"""

DETAIL_SYSTEM = """You write one short-form video (Instagram Reel) for a creator from an outline, reusing the structure of
the proven outliers it is based on.

""" + RULES + """
4. Follow the outline's angle, format, delivery and hook pattern, and the slot's funnel stage, content type and CTA type.
5. Beat labels: {beats}. CTA mechanic: {cta_mechanic}.

Reply with ONLY a JSON object:
{{"hook": {{"verbal": "the first sentence spoken (≤15 words)", "written": "on-screen text in the first 3 s (≤7 words)",
          "visual": "one filmable action for the first 3 s"}},
 "beats": [{{"label": BEAT, "say": "what to say, in full sentences, in the creator's voice",
            "show": "what to film", "edit": "editing note"}}],
 "cta": {{"mechanic": str, "line": "the exact closing line"}},
 "length_s": int, "caption_first_line": str, "hashtags": [3-5 strings without #],
 "why": "why this should work, citing the teardown ids and what you reused from each",
 "risk": "the most likely reason it underperforms, and how to avoid it",
 "needs_from_you": ["each [[placeholder]] used, explained"]}}"""

SHOTS_SYSTEM = """You write the shot list for one short-form video (an Instagram Reel) from its script, borrowing the shot
grammar of the proven outlier scenes it is based on. Each reference scene is described in SEALCaM.

""" + RULES + """

""" + SEALCAM + """

Rules for the shot list:
4. One shot per camera setup or cut, in order, covering every beat of the script; a beat can take several shots. The
   durations add up to about the script's length.
5. For each beat, borrow the framing, camera movement, lighting, pace and on-screen text style of the reference scenes
   with the same job, but write the subject and environment for THIS creator and THIS script. Never copy a reference's
   on-screen text or setting details that identify its creator.
6. Write each SEALCaM field as an explicit instruction for setting the shot up, in the terms above. SEALCaM is visual
   only: no sound, music or voice in any field.
7. say: the exact script words spoken during this shot (split a beat's line across its shots), or null.
   on_screen_text: the text to burn in, or null. reference: the scene it borrows from, as "<id> scene <n>", or null.
8. Beat labels: {beats}.

Reply with ONLY a JSON object: {{"shots": [{{"beat": str, "duration_s": number, "say": str|null,
 "on_screen_text": str|null, "S": str, "E": str, "A": str, "L": str, "Ca": str, "M": str, "reference": str|null}}]}}"""

_running = set()


def tier(followers):
    if followers is None or followers < 1000:
        return "new"
    return "growing" if followers < 10000 else "established"


def slots_for(followers, posts):
    pattern = WEEK_PATTERNS[tier(followers)][:posts]
    out, bofu_seen = [], 0
    for i, (funnel, cta) in enumerate(pattern, 1):
        if funnel == "tofu":
            content = "educational"
        elif funnel == "mofu":
            content = "storytelling"
        else:
            content = "educational" if bofu_seen % 2 == 0 else "authority"
            bofu_seen += 1
        out.append({"slot": i, "funnel": funnel, "content_type": content, "cta_type": cta})
    return out


def base_rates(project_id):
    """Share of reels from in-range scanned creators that beat 1x/2x/5x/10x their follower count."""
    with db.connect() as conn:
        settings = db.project_settings(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
        # Only creators in the follower range: an account you named to study can be far bigger and would skew the rates.
        rows = conn.execute("""SELECT r.views, c.followers FROM reels r
                               JOIN project_creators pc ON pc.username = r.username AND pc.project_id = ?
                               JOIN creators c ON c.username = r.username
                               WHERE pc.status = 'scanned' AND r.views IS NOT NULL AND c.followers BETWEEN ? AND ?""",
                            (project_id, max(1, settings["min_followers"]), settings["max_followers"])).fetchall()
    n = len(rows)
    rate = lambda t: (sum(1 for r in rows if r["views"] / r["followers"] >= t) / n) if n else None
    return {"reels": n, "p1": rate(1), "p2": rate(2), "p5": rate(5), "p10": rate(10)}


def teardown_summaries(project_id):
    with db.connect() as conn:
        rows = conn.execute("""SELECT o.shortcode, o.ratio, r.username, t.data FROM outliers o
                               JOIN reels r ON r.shortcode = o.shortcode JOIN teardowns t ON t.shortcode = o.shortcode
                               WHERE o.project_id = ? AND o.status <> 'dismissed' AND t.status = 'done'
                               ORDER BY o.ratio DESC""", (project_id,)).fetchall()
    out = []
    for r in rows:
        data = json.loads(r["data"])
        if any("Sponsored" in n for n in data.get("notes", [])):
            continue  # the playbook excludes paid posts from outliers
        f = {k: v.get("value") for k, v in data["fields"].items()}
        out.append({
            "id": r["shortcode"], "creator": "@" + r["username"], "ratio": r["ratio"],
            "verbal_hook": f.get("verbal_hook"), "written_hook": f.get("written_hook"), "visual_hook": f.get("visual_hook"),
            "hook_pattern": f.get("hook_pattern"), "angle": f.get("angle"), "video_type": f.get("video_type"),
            "delivery": f.get("delivery"), "story_type": f.get("story_type"), "format": f.get("format"),
            "content_type": f.get("content_type"), "funnel": f.get("funnel"), "complexity": f.get("complexity"),
            "beats": f.get("structure_pattern"), "value": f.get("value_summary"), "cta_mechanic": f.get("cta_mechanic"),
            "is_series": f.get("is_series"), "length_s": (f.get("stats") or {}).get("duration_s"),
            "words_per_second": f.get("words_per_second"),
        })
    return out


def odds(post, slot, teardowns, rates):
    """Base rate from the scan x evidence multiplier from how many outliers share the post's choices x funnel factor."""
    n = len(teardowns)
    support = []
    for attr in EVIDENCE_ATTRS:
        value = post.get(attr)
        if value in SKIP_VALUES:
            continue
        count = sum(1 for t in teardowns if t.get(attr) == value)
        support.append({"attr": attr, "value": value, "count": count, "of": n})
    share = statistics.mean(s["count"] / n for s in support) if support and n else 0
    sources = [t["ratio"] for t in teardowns if t["id"] in (post.get("source_outliers") or [])]
    source_bonus = 0.25 if sources and statistics.median(sources) >= 10 else 0
    evidence = 1 + 2 * share + source_bonus
    funnel = FUNNEL_FACTOR[slot["funnel"]] * (AUTHORITY_FACTOR if slot["content_type"] == "authority" else 1)
    multiplier = round(max(0.5, min(3.0, evidence * funnel)), 2)
    p = {k: (min(0.6, rates[k] * multiplier) if rates.get(k) is not None else None) for k in ("p1", "p2", "p5", "p10")}
    rel = multiplier
    band = "strong" if rel >= 1.75 else "good" if rel >= 1.2 else "average" if rel >= 0.9 else "below average"
    confidence = "medium" if n >= 15 and rates["reels"] >= 500 else "low"
    return {**p, "multiplier": multiplier, "band": band, "confidence": confidence, "support": support,
            "factors": {"evidence": round(evidence, 2), "funnel": round(funnel, 2), "source_median_ratio":
                        round(statistics.median(sources), 1) if sources else None}}


def start(project_id, about, followers, start_date, posts, model):
    if project_id in _running:
        raise RuntimeError("A plan is already being generated for this project.")
    teardowns = teardown_summaries(project_id)
    if len(teardowns) < 3:
        raise RuntimeError("Tear down at least 3 outliers first: the plan is built from teardowns.")
    with db.connect() as conn:
        cur = conn.execute("INSERT INTO plans (project_id, status, input, created_at) VALUES (?, 'running', ?, ?)",
                           (project_id, json.dumps({"about": about, "followers": followers, "start_date": start_date,
                                                    "posts": posts, "model": model}), db.now()))
        plan_id = cur.lastrowid
    _running.add(project_id)
    threading.Thread(target=_run, args=(plan_id, project_id, about, followers, start_date, posts, model, teardowns),
                     daemon=True).start()
    return plan_id


def _run(plan_id, project_id, about, followers, start_date, posts, model, teardowns):
    try:
        data = _generate(project_id, about, followers, start_date, posts, model, teardowns)
        with db.connect() as conn:
            conn.execute("UPDATE plans SET status='done', data=? WHERE id=?", (json.dumps(data), plan_id))
        db.log(project_id, "success", f"Week plan #{plan_id} ready: {len(data['posts'])} posts")
    except Exception as e:
        with db.connect() as conn:
            conn.execute("UPDATE plans SET status='failed', error=? WHERE id=?", (str(e), plan_id))
        db.log(project_id, "error", f"Week plan #{plan_id} failed: {e}")
    finally:
        _running.discard(project_id)


def _chat(model, system, user, temperature, max_tokens=6000):
    resp = requests.post(URL, timeout=300, headers={"Authorization": f"Bearer {openrouter_key()}"}, json={
        "model": model, "temperature": temperature, "max_tokens": max_tokens, "usage": {"include": True},
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    })
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code != 200 or "choices" not in body:
        raise RuntimeError(f"OpenRouter {resp.status_code}: {(body.get('error') or {}).get('message') or resp.text[:200]}")
    return body["choices"][0]["message"]["content"] or "", (body.get("usage") or {}).get("cost") or 0


def _parse(reply):
    match = re.search(r"\{.*\}", reply, re.S)
    if not match:
        raise ValueError("no JSON object in the reply")
    return json.loads(match.group(0))  # JSONDecodeError is a ValueError


def _chat_json(model, system, user, temperature, max_tokens=6000):
    """One call, plus one repair pass if the reply isn't valid JSON. Returns (parsed, cost)."""
    reply, cost = _chat(model, system, user, temperature, max_tokens)
    try:
        return _parse(reply), cost
    except ValueError:
        fixed, fix_cost = _chat(model, "You repair broken JSON. Reply with only the corrected JSON object, changing nothing else.",
                                reply, 0, max_tokens)
        return _parse(fixed), cost + fix_cost


def reference_scenes(shortcodes):
    """Scene-by-scene SEALCaM breakdowns of the given teardowns, for those that have one."""
    if not shortcodes:
        return {}
    with db.connect() as conn:
        rows = conn.execute(f"SELECT shortcode, data FROM teardowns WHERE status='done' AND shortcode IN "
                            f"({','.join('?' * len(shortcodes))})", list(shortcodes)).fetchall()
    out = {}
    for r in rows:
        data = json.loads(r["data"])
        scenes = [{k: sc.get(k) for k in ("i", "start", "end", "cut", "flash_cuts", "beat", "said", "on_screen_text", *SEALCAM_KEYS)}
                  for sc in data.get("scenes") or [] if sc.get("S")]
        if scenes:
            out[r["shortcode"]] = {"creator": "@" + data["username"], "scenes": scenes}
    return out


def add_shots(posts, context, model):
    """Fill post["shots"] for each post (in parallel). Returns the cost. A failed post gets post["shots_error"]."""
    refs = reference_scenes({s for p in posts for s in p.get("source_outliers") or []})
    system = SHOTS_SYSTEM.format(beats=", ".join(BEATS))

    def one(post):
        script = {k: post.get(k) for k in ("title", "format", "angle", "delivery", "complexity", "length_s", "hook", "beats", "cta")}
        sources = {s: refs[s] for s in post.get("source_outliers") or [] if s in refs}
        try:
            got, c = _chat_json(model, system, context + f"SCRIPT:\n{json.dumps(script, ensure_ascii=False)}\n\n"
                                f"REFERENCE SCENES (SEALCaM, by outlier id):\n{json.dumps(sources, ensure_ascii=False) if sources else '(none)'}",
                                0.5, 10000)
        except Exception as e:
            post["shots_error"] = str(e)
            return 0
        post["shots"] = [{**{k: sh.get(k) for k in ("beat", "duration_s", "say", "on_screen_text", *SEALCAM_KEYS)},
                          "reference": sh.get("reference")} for sh in got.get("shots") or [] if sh.get("S")]
        post.pop("shots_error", None)
        return c

    with ThreadPoolExecutor(max_workers=4) as pool:
        return sum(pool.map(one, posts))


def add_shot_lists(plan_id):
    """Backfill shot lists on a finished plan made before they existed. Returns the cost."""
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
        project = conn.execute("SELECT * FROM projects WHERE id=?", (row["project_id"],)).fetchone()
    data, inp = json.loads(row["data"]), json.loads(row["input"])
    cost = add_shots(data["posts"], _context(project, inp.get("about") or "", inp.get("followers")), inp["model"])
    data["cost"] = round((data.get("cost") or 0) + cost, 4)
    with db.connect() as conn:
        conn.execute("UPDATE plans SET data=? WHERE id=?", (json.dumps(data), plan_id))
    return cost


def _context(project, about, followers):
    return (f"NICHE: {project['niche'] or project['name']}\nKEYWORDS: {', '.join(json.loads(project['keywords']))}\n\n"
            f"ABOUT THE CREATOR (the only facts you may use about them):\n{about.strip() or '(nothing given: use [[placeholders]])'}\n"
            f"Followers: {followers if followers is not None else 'unknown'}\n\n")


def _outline_problems(posts):
    """Breaches of outline rule 6, which the model sometimes ignores."""
    problems = [f"slot {p.get('slot')} uses the talking_head format" for p in posts if p.get("format") == "talking_head"]
    for key in ("format", "angle"):
        problems += [f"{key} {value} is used {n} times (max 2)" for value, n in Counter(p.get(key) for p in posts).items()
                     if value and n > 2]
    return problems


def _generate(project_id, about, followers, start_date, posts, model, teardowns):
    with db.connect() as conn:
        project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    rates = base_rates(project_id)
    slots = slots_for(followers, posts)
    vocab = {k: ", ".join(VOCAB[k]) for k in ("angle", "video_type", "delivery", "story_type", "format", "hook_pattern",
                                               "complexity", "cta_mechanic")}
    context = _context(project, about, followers)
    cost = 0.0

    # Stage 1: the week's outline, so formats and angles are spread across days.
    outline_user = (context + f"SLOTS (one post each, in order):\n{json.dumps(slots)}\n\n"
                    f"TEARDOWNS OF PROVEN OUTLIERS ({len(teardowns)}):\n{json.dumps(teardowns, ensure_ascii=False)}")
    outline, c = _chat_json(model, OUTLINE_SYSTEM.format(**vocab), outline_user, 0.6)
    cost += c
    problems = _outline_problems(outline.get("posts", []))
    if problems:  # one revision pass when the model ignores rule 6
        outline, c = _chat_json(model, OUTLINE_SYSTEM.format(**vocab),
                                outline_user + f"\n\nYOUR PREVIOUS OUTLINE:\n{json.dumps(outline, ensure_ascii=False)}\n\n"
                                "Return it again with only these problems fixed:\n- " + "\n- ".join(problems), 0.3)
        cost += c
    by_slot = {p.get("slot"): p for p in outline.get("posts", [])}
    if len(by_slot) < len(slots):
        raise RuntimeError(f"The outline had {len(by_slot)} of {len(slots)} posts")

    # Stage 2: each post written in full from its own sources, in parallel.
    teardown_by_id = {t["id"]: t for t in teardowns}

    def detail(slot):
        post = by_slot[slot["slot"]]
        sources = [teardown_by_id[s] for s in post.get("source_outliers") or [] if s in teardown_by_id] or teardowns[:3]
        return _chat_json(model, DETAIL_SYSTEM.format(beats=", ".join(BEATS), **vocab),
                          context + f"SLOT: {json.dumps(slot)}\nOUTLINE: {json.dumps(post, ensure_ascii=False)}\n\n"
                          f"SOURCE TEARDOWNS:\n{json.dumps(sources, ensure_ascii=False)}", 0.7)

    with ThreadPoolExecutor(max_workers=4) as pool:
        details = list(pool.map(detail, slots))
    result = {"posts": []}
    for slot, (d, c) in zip(slots, details):
        cost += c
        result["posts"].append({**by_slot[slot["slot"]], **d})

    known = {t["id"] for t in teardowns}
    start = date.fromisoformat(start_date) if start_date else date.today() + timedelta(days=1)
    planned = []
    for slot, post in zip(slots, result.get("posts", [])):
        for key in ("angle", "video_type", "delivery", "story_type", "format", "hook_pattern", "complexity"):
            if post.get(key) not in VOCAB[key]:
                post[key] = None
        post["source_outliers"] = [s for s in post.get("source_outliers") or [] if s in known]
        post["beats"] = [b for b in post.get("beats") or [] if b.get("label") in BEATS]
        planned.append({**post, **slot, "date": (start + timedelta(days=slot["slot"] - 1)).isoformat(),
                        "odds": odds(post, slot, teardowns, rates)})
    if len(planned) < len(slots):
        raise RuntimeError(f"The model returned {len(planned)} of {len(slots)} posts")

    # Stage 3: a SEALCaM shot list for each post, from its script and its sources' scene breakdowns.
    cost += add_shots(planned, context, model)
    mix = Counter(p["format"] for p in planned)
    return {"posts": planned, "rates": rates, "teardowns_used": len(teardowns), "tier": tier(followers),
            "model": model, "cost": round(cost, 4), "format_mix": mix.most_common(),
            "method": ("Odds = this niche's base rate (share of scanned reels that beat each multiple of the creator's "
                       "followers) × an evidence multiplier (1 + 2 × the average share of torn-down outliers that use "
                       "the same hook pattern, format, angle, video type, structure and delivery; +0.25 when its source "
                       "outliers median 10×+) × a funnel factor (TOFU 1.15, MOFU 0.9, BOFU 0.8; authority ×0.75). "
                       "Capped at 3×. An estimate from a small sample, not a forecast.")}
