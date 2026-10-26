"""Find creators who have "doubled down": they found a template that works and keep posting it.

An outlier is one reel that beat the creator's follower count. A doubled-down account is different: the same template
(read from the first line of the caption, e.g. "Colour combinations compilation…", "Jeans & top guide") keeps coming
back and keeps reaching a real share of the audience. That's often the safer thing to copy.

A template qualifies when one phrase repeats in at least MIN_REELS of the creator's scanned reels, its typical (median)
reel reaches at least MIN_REACH of their followers, and it is either a habit (MIN_SHARE of their reels or more) or a
proven winner (its typical reel beats the follower count).

Reels, carousels and slideshows are counted separately (a creator's carousel template is its own template), and a
carousel's views are estimated from its likes.

A format that several creators copy is stronger evidence still: it works for different audiences, not just one
account's. niche_templates() finds them: one phrase (from caption headlines, plus the cover or hook text of torn-down
posts) or one hook frame (a torn-down hook's madlib with its blanks removed, e.g. "how to be a ___") used by at least
MIN_CREATORS creators, where most of them (at least MIN_WINNERS, and at least half) get MIN_LIFT times their own typical
post or more with it, and its typical lift across those creators is MIN_LIFT or more. A creator with too few posts to
know their typical one counts as a win only with a real outlier: min_ratio times their followers, from at least
min_followers (beating a tiny account's follower count says nothing). A phrase inside one of the
project's keywords, or holding a one-word keyword ("learning mahjong"), is the niche itself, not a format, so it is
skipped.
"""

import json
import re
import statistics
from collections import Counter, defaultdict

from . import db, reach

MIN_REELS, MIN_SHARE, MIN_REACH, WINNER_REACH = 4, 0.2, 0.1, 1.0
MIN_CREATORS, MIN_WINNERS, MIN_LIFT = 3, 2, 2.0
MIN_TYPICAL = 5  # posts of one kind needed to know a creator's typical post
SLOT = re.compile(r"\{\{[^}]+\}\}")

# Words that carry no template: grammar, calls to action and shopping/credit boilerplate.
STOP = set("""a an the and or of to for in on with your you my me i we our is are be this that these those it its at by from
as so if do does did how what which who why when where all any more most just get got can will would should must need needs
save later follow comment link links bio tag share dm dms like send part new here there now one two three vs not no yes
look looks looking try favorite favourite outfit outfits shop shopping below code discount sale ltk liketk amazon
storefront affiliate sponsored partner gifted made using created edited http https www com video reel reels receive
post posts details info inbox message check out click don doesn didn isn aren wasn won can have has had been being about
but ever make makes made they them their than then every some really actually thing things way people know want going
into next let lets talk said says""".split())
SAME = {"colour": "color", "colours": "color", "colors": "color", "combos": "combinations", "combo": "combinations",
        "combination": "combinations", "pairing": "pairings", "guides": "guide"}


def title(caption):
    """The caption's headline: its first line, cut at " | " or the first sentence end, without links, tags or handles."""
    line = (caption or "").split("\n")[0]
    line = re.split(r"\s[|•]\s|[.!?](?:\s|$)", line)[0]
    return re.sub(r"https?://\S+|www\.\S+|#\w+|@[\w.]+", " ", line).strip()[:120]


def phrases(caption):
    words = [SAME.get(w, w) for w in re.findall(r"[a-z]+", title(caption).lower())]
    words = [w for w in words if w not in STOP and len(w) > 2]
    return {" ".join(pair) for pair in zip(words, words[1:])}


def templates(reels, followers, limit=3):
    """The creator's repeated templates, biggest first: each phrase claims its reels before the next is counted."""
    reels = [r for r in reels if r.get("views")]
    pool, found = list(reels), []
    for _ in range(limit):
        counts = Counter(p for r in pool for p in phrases(r.get("caption")))
        if not counts:
            break
        phrase, n = counts.most_common(1)[0]
        if n < MIN_REELS:
            break
        hits = [r for r in pool if phrase in phrases(r.get("caption"))]
        others = [r for r in reels if r not in hits]
        median = statistics.median(r["views"] for r in hits)
        other = statistics.median(r["views"] for r in others) if others else None
        reach = median / followers if followers else None
        found.append({
            "phrase": phrase, "count": n, "of": len(reels), "share": round(n / len(reels), 2),
            "median_views": int(median), "reach": round(reach, 2) if reach is not None else None,
            "vs_other_reels": round(median / other, 2) if other else None,
            "qualifies": n >= MIN_REELS and (reach or 0) >= MIN_REACH and (n / len(reels) >= MIN_SHARE or (reach or 0) >= WINNER_REACH),
            "examples": [r["shortcode"] for r in sorted(hits, key=lambda r: -r["views"])[:4]],
        })
        pool = [r for r in pool if r not in hits]
    return found


def project_accounts(conn, project_id):
    """Every scanned creator in the project with at least one qualifying template, best reach first."""
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    kinds = (reach.enabled_kinds(db.project_settings(project)) if project else None) or ["reel"]
    lpv = reach.likes_per_view(conn, project_id)
    rows = conn.execute("""SELECT pc.username, c.followers, c.full_name FROM project_creators pc
                           JOIN creators c ON c.username = pc.username
                           WHERE pc.project_id = ? AND pc.status = 'scanned' AND c.followers > 0""", (project_id,)).fetchall()
    accounts = []
    for row in rows:
        posts = [dict(r) for r in conn.execute(f"SELECT shortcode, kind, views, likes, caption FROM reels WHERE username=? "
                                               f"AND kind IN ({','.join('?' * len(kinds))})", (row["username"], *kinds))]
        for post in posts:
            post["views"] = reach.views(post, lpv)
        posts = [p for p in posts if p["views"]]
        found = [{**t, "kind": kind} for kind in kinds for t in templates([p for p in posts if p["kind"] == kind], row["followers"])]
        if any(t["qualifies"] for t in found):  # the other repeated phrases come along, marked as not qualifying
            accounts.append({"username": row["username"], "full_name": row["full_name"], "followers": row["followers"],
                             "reels": len(posts), "median_views": int(statistics.median(p["views"] for p in posts)),
                             "templates": found, "lpv": lpv})
    return sorted(accounts, key=lambda a: -max(t["reach"] or 0 for t in a["templates"]))


def frame(template):
    """A hook madlib's frame words with every blank as "___", e.g. "how to be a ___"; None if fewer than 2 frame words."""
    text = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", SLOT.sub(" ___ ", (template or "").lower()))).strip()
    return text if len([w for w in text.split() if w != "___"]) >= 2 else None


def niche_templates(conn, project_id):
    """Formats several creators replicate and win with, strongest first (see the module notes)."""
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project:
        return []
    settings = db.project_settings(project)
    kinds = reach.enabled_kinds(settings) or ["reel"]
    keywords = [k.lower() for k in json.loads(project["keywords"])]
    niche_words = {k for k in keywords if " " not in k}
    niche_phrases = set().union(*(phrases(k) for k in keywords)) if keywords else set()  # "what i eat in a day" -> "eat day"
    is_niche = lambda p: p in niche_phrases or any(p in k for k in keywords) or bool(set(p.split()) & niche_words)
    lpv = reach.likes_per_view(conn, project_id)
    rows = conn.execute(f"""SELECT r.shortcode, r.username, r.kind, r.views, r.likes, r.caption, r.taken_at, c.followers, t.data
                            FROM reels r JOIN project_creators pc ON pc.username = r.username AND pc.project_id = ?
                            JOIN creators c ON c.username = r.username
                            LEFT JOIN teardowns t ON t.shortcode = r.shortcode AND t.status = 'done'
                            WHERE c.followers > 0 AND r.kind IN ({','.join('?' * len(kinds))})""",
                        (project_id, *kinds)).fetchall()
    posts, typical = [], defaultdict(list)
    for r in rows:
        views = reach.views(r, lpv)
        if not views:
            continue
        data = json.loads(r["data"]) if r["data"] else {}
        hooks = (data.get("madlib") or {}).get("hooks") or {}
        cover = ((data.get("fields") or {}).get("written_hook") or {}).get("value")
        signatures = {("phrase", p) for p in phrases(r["caption"]) | phrases(cover) if not is_niche(p)}
        signatures |= {("frame", f) for f in (frame((hooks.get(k) or {}).get("template")) for k in ("written", "verbal")) if f}
        posts.append({"shortcode": r["shortcode"], "username": r["username"], "kind": r["kind"], "views": views,
                      "followers": r["followers"], "caption": r["caption"], "cover": cover, "signatures": signatures})
        typical[(r["username"], r["kind"])].append(views)
    typical = {k: statistics.median(v) for k, v in typical.items() if len(v) >= MIN_TYPICAL}
    groups = defaultdict(list)
    for post in posts:
        post["lift"] = post["views"] / typical[(post["username"], post["kind"])] if (post["username"], post["kind"]) in typical else None
        post["ratio"] = post["views"] / post["followers"]
        for sig in post["signatures"]:
            groups[(post["kind"], *sig)].append(post)

    found = []
    for (kind, how, signature), members in groups.items():
        by_creator = defaultdict(list)
        for post in members:
            by_creator[post["username"]].append(post)
        if len(by_creator) < MIN_CREATORS:
            continue
        creators = []
        for username, mine in by_creator.items():
            lifts = [p["lift"] for p in mine if p["lift"] is not None]
            lift = statistics.median(lifts) if lifts else None  # this creator's typical post of the template vs their typical post
            best = max(mine, key=lambda p: p["views"])
            creators.append({"username": username, "posts": len(mine), "lift": round(lift, 1) if lift else None,
                             "wins": lift >= MIN_LIFT if lift is not None else
                             best["followers"] >= settings["min_followers"] and best["ratio"] >= settings["min_ratio"],
                             "best": best})
        winners = sum(c["wins"] for c in creators)
        lifts = [c["lift"] for c in creators if c["lift"]]
        if winners < max(MIN_WINNERS, len(creators) / 2) or (lifts and statistics.median(lifts) < MIN_LIFT):
            continue
        found.append({
            "signature": signature, "how": how, "kind": kind, "creators": len(creators), "winners": winners,
            "posts": len(members), "median_lift": round(statistics.median(lifts), 1) if lifts else None,
            "median_ratio": round(statistics.median(c["best"]["ratio"] for c in creators), 1),
            "shortcodes": {p["shortcode"] for p in members},
            "examples": [{"shortcode": c["best"]["shortcode"], "username": c["username"], "views": int(c["best"]["views"]),
                          "ratio": round(c["best"]["ratio"], 1), "lift": c["lift"], "wins": c["wins"], "posts": c["posts"],
                          "estimated": kind == "carousel", "title": title(c["best"]["caption"]) or c["best"]["cover"]}
                         for c in sorted(creators, key=lambda c: (-c["wins"], -c["best"]["ratio"]))],
        })
    # Strongest first; a template whose posts are mostly another's (e.g. "body workout" inside "full body") is dropped.
    found.sort(key=lambda t: (-t["winners"], -(t["median_lift"] or 0), -t["creators"]))
    kept = []
    for t in found:
        if not any(k["kind"] == t["kind"] and len(t["shortcodes"] & k["shortcodes"]) >= 0.8 * len(t["shortcodes"]) for k in kept):
            kept.append(t)
    for t in kept:
        t["shortcodes"] = sorted(t["shortcodes"])
    return kept


def replicated_by_post(conn, project_id):
    """{shortcode: the strongest niche template its post belongs to}, for the planner and the briefs."""
    out = {}
    for t in niche_templates(conn, project_id):  # strongest first, so the first template a post is found in wins
        for sc in t["shortcodes"]:
            out.setdefault(sc, {k: t[k] for k in ("signature", "how", "kind", "creators", "winners", "median_lift")})
    return out
