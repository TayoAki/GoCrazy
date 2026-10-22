"""Find creators who have "doubled down": they found a template that works and keep posting it.

An outlier is one reel that beat the creator's follower count. A doubled-down account is different: the same template
(read from the first line of the caption, e.g. "Colour combinations compilation…", "Jeans & top guide") keeps coming
back and keeps reaching a real share of the audience. That's often the safer thing to copy.

A template qualifies when one phrase repeats in at least MIN_REELS of the creator's scanned reels, its typical (median)
reel reaches at least MIN_REACH of their followers, and it is either a habit (MIN_SHARE of their reels or more) or a
proven winner (its typical reel beats the follower count).
"""

import re
import statistics
from collections import Counter

MIN_REELS, MIN_SHARE, MIN_REACH, WINNER_REACH = 4, 0.2, 0.1, 1.0

# Words that carry no template: grammar, calls to action and shopping/credit boilerplate.
STOP = set("""a an the and or of to for in on with your you my me i we our is are be this that these those it its at by from
as so if do does did how what which who why when where all any more most just get got can will would should must need needs
save later follow comment link links bio tag share dm dms like send part new here there now one two three vs not no yes
look looks looking try favorite favourite outfit outfits shop shopping below code discount sale ltk liketk amazon
storefront affiliate sponsored partner gifted made using created edited http https www com video reel reels receive
post posts details info inbox message check out click""".split())
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
    rows = conn.execute("""SELECT pc.username, c.followers, c.full_name FROM project_creators pc
                           JOIN creators c ON c.username = pc.username
                           WHERE pc.project_id = ? AND pc.status = 'scanned' AND c.followers > 0""", (project_id,)).fetchall()
    accounts = []
    for row in rows:
        reels = [dict(r) for r in conn.execute("SELECT shortcode, views, caption FROM reels WHERE username=? AND views IS NOT NULL",
                                                (row["username"],))]
        found = templates(reels, row["followers"])
        if any(t["qualifies"] for t in found):  # the other repeated phrases come along, marked as not qualifying
            accounts.append({"username": row["username"], "full_name": row["full_name"], "followers": row["followers"],
                             "reels": len(reels), "median_views": int(statistics.median(r["views"] for r in reels)),
                             "templates": found})
    return sorted(accounts, key=lambda a: -max(t["reach"] or 0 for t in a["templates"]))
