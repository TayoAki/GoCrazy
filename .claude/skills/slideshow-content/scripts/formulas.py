"""Read a research project's slideshow and carousel outliers (read-only) to find the formulas that win.

    python3 formulas.py refs <project id> [--out DIR]            # every outlier as refs.md (to read) and refs.json
    python3 formulas.py stats <project id> [groups.json]         # numbers per formula, plus patterns across all winners
    python3 formulas.py sheet <shortcode> [<shortcode> ...] --out sheet.jpg   # a post's slides side by side

groups.json maps each formula you named to its posts: {"Food swaps": ["7693408989891104022", ...], ...}.

Numbers it reports:
- ratio: plays ÷ the creator's followers. An outlier is 5× or more. Instagram carousels show no plays, so theirs are
  estimated from likes (marked ≈); treat them as a ranking.
- saves per 1,000 plays: how often people kept it. TikTok only (Instagram doesn't show saves). This is the number that
  says a post was useful, so formulas are ranked by it.
"""

import argparse
import json
import os
import re
import sqlite3
import statistics
from collections import Counter
from pathlib import Path


def find_repo():
    starts = [Path(os.environ["RESEARCH_REPO"])] if os.environ.get("RESEARCH_REPO") else []
    starts += [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]
    return next((d for d in starts if (d / "research_app" / "server.py").exists()), Path.cwd())


REPO = find_repo()
DB = REPO / "data" / "research.db"
MEDIA = REPO / "data" / "media"
SLIDE_KINDS = ("slideshow", "carousel")
PROMO = re.compile(r"#(ad|ads|sponsored|partner|paidpartnership|gifted)\b|paid partnership|\buse (my )?code\b|"
                   r"\bcode [A-Z0-9]{3,}\b|#use[a-z]+", re.I)
METRICS = """How to read these numbers:
- Plays ÷ followers: a post's plays divided by its creator's followers. A 1,000-follower account whose post got 50,000
  plays scores 50×. An outlier scores 5× or more. Instagram carousels show no plays, so theirs are estimated from likes.
- Median: the middle value across a formula's posts, so one freak hit can't carry a formula.
- Saves per 1,000 plays: how many of every thousand viewers saved the post to keep. It's the sign a post was useful,
  so formulas are ranked by it. TikTok shows saves; Instagram doesn't.
- A formula is proven when 3+ posts from 2+ creators won with it. With 2 posts it's a lead; with one creator, it's
  that creator's template."""


def connect():
    if not DB.exists():
        raise SystemExit(f"No research database at {DB}. Run the research first (research.py).")
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def handle(username):
    return "@" + re.sub(r"^(tt|yt):", "", username or "")


def aspect(shortcode):
    """The first slide's shape, e.g. 3:4, from the saved image."""
    path = MEDIA / shortcode / "slide_01.jpg"
    if not path.exists():
        return None
    try:
        from PIL import Image
        w, h = Image.open(path).size
    except Exception:
        return None
    r = h / w
    return min({"1:1": 1.0, "4:5": 1.25, "3:4": 4 / 3, "9:16": 16 / 9}.items(), key=lambda kv: abs(kv[1] - r))[0]


def posts(conn, project_id):
    rows = conn.execute(f"""
        SELECT o.shortcode, o.ratio, o.basis, o.measure, o.keyword, r.url, r.username, r.platform, r.kind, r.views, r.likes,
               r.saves, r.shares, r.comments, r.taken_at, r.caption, r.music, c.followers, t.status AS td_status, t.data
        FROM outliers o JOIN reels r ON r.shortcode = o.shortcode LEFT JOIN creators c ON c.username = r.username
        LEFT JOIN teardowns t ON t.shortcode = o.shortcode
        WHERE o.project_id = ? AND o.status <> 'dismissed' AND r.kind IN ({','.join('?' * len(SLIDE_KINDS))})
        ORDER BY o.ratio DESC""", (project_id, *SLIDE_KINDS)).fetchall()
    out = []
    for r in rows:
        d = json.loads(r["data"]) if r["data"] and r["td_status"] == "done" else {}
        f = {k: (v or {}).get("value") for k, v in (d.get("fields") or {}).items()}
        music = d.get("music") or (json.loads(r["music"]) if r["music"] else {}) or {}
        sound = music.get("song_name") or music.get("title")
        plays = r["views"] or (round(r["ratio"] * r["followers"]) if r["followers"] else None)
        hooks = (d.get("madlib") or {}).get("hooks") or {}
        out.append({
            "shortcode": r["shortcode"], "url": r["url"], "handle": handle(r["username"]), "platform": r["platform"],
            "kind": r["kind"], "followers": r["followers"], "plays": plays, "plays_estimated": not r["views"],
            "ratio": r["ratio"], "basis": r["basis"], "keyword": r["keyword"], "saves": r["saves"],
            "saves_per_1k": round(1000 * r["saves"] / r["views"], 1) if r["saves"] and r["views"] else None,
            "likes": r["likes"], "shares": r["shares"], "comments": r["comments"], "posted": (r["taken_at"] or "")[:10],
            "torn_down": bool(d), "slides": (f.get("stats") or {}).get("slides") if d else None,
            "aspect": aspect(r["shortcode"]), "cover": f.get("written_hook"),
            "cover_template": (hooks.get("written") or {}).get("template"), "type": f.get("carousel_type"),
            "topic": f.get("topic"), "value": f.get("value_summary"), "style": f.get("captions"),
            "cta": f.get("cta_mechanic"), "cta_text": f.get("cta_text"), "sound": sound,
            "sponsored": any("ponsor" in n or "aid partnership" in n for n in d.get("notes") or [])
                         or bool(PROMO.search(r["caption"] or "")),
            "app_account": bool(re.search(r"app|\bai\b", handle(r["username"]).lower())),
            "caption": (r["caption"] or "").strip(),
            "slide_text": [(s.get("on_screen_text") or "").strip() for s in d.get("scenes") or []],
        })
    # A paid campaign posts the same caption from many accounts: the same opening line from 2+ creators is one.
    opening = lambda c: re.sub(r"\W+", " ", c.lower()).strip()[:60]
    creators = {}
    for i in out:
        if len(opening(i["caption"])) >= 25:
            creators.setdefault(opening(i["caption"]), set()).add(i["handle"])
    for i in out:
        i["campaign"] = len(creators.get(opening(i["caption"]), ())) > 1
        i["promo"] = i["sponsored"] or i["campaign"] or i["app_account"]
    return out


def refs(args):
    conn = connect()
    items = posts(conn, args.project)
    out = Path(args.out) if args.out else Path.cwd()
    out.mkdir(parents=True, exist_ok=True)
    (out / "refs.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    lines = [f"# Slideshow and carousel outliers, project #{args.project}", "",
             f"{len(items)} posts, {sum(i['torn_down'] for i in items)} torn down. Ratio = plays ÷ followers "
             "(≈ = estimated from likes). Saves per 1,000 plays: TikTok only.", ""]
    for i in items:
        est = "≈" if i["plays_estimated"] else ""
        lines.append(f"## {i['shortcode']} · {i['handle']} ({i['platform']} {i['kind']}) · {est}{i['ratio']}×")
        lines.append(f"{i['url']} · {i['followers']} followers · {est}{i['plays']} plays · "
                     f"{i['saves_per_1k'] if i['saves_per_1k'] is not None else '-'} saves per 1,000 · "
                     f"{i['slides'] or '?'} slides · {i['aspect'] or '?'} · posted {i['posted']}"
                     + (" · SPONSORED" if i["sponsored"] else "") + (" · CAMPAIGN (same caption on other accounts)" if i["campaign"] else "")
                     + (" · APP ACCOUNT" if i["app_account"] else "") + (f" · found as {i['basis']}" if i["basis"] != "followers" else "")
                     + (" · TINY ACCOUNT: the ratio means little, judge it by saves" if (i["followers"] or 0) < 1000 else ""))
        if i["torn_down"]:
            lines.append(f"- cover: {i['cover']!r} · template: {i['cover_template']!r} · type: {i['type']}")
            lines.append(f"- topic: {i['topic']}")
            lines.append(f"- style: {i['style']}")
            lines.append(f"- slides: " + " | ".join(t.replace("\n", " / ")[:120] for t in i["slide_text"]))
            lines.append(f"- ask: {i['cta']} {i['cta_text'] or ''} · sound: {i['sound'] or '-'}")
        lines.append(f"- caption: {i['caption'][:220]!r}")
        lines.append("")
    (out / "refs.md").write_text("\n".join(lines))
    print(f"{len(items)} posts -> {out / 'refs.md'} and refs.json ({sum(not i['torn_down'] for i in items)} not torn down)")


def med(values):
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 1) if values else None


def stats(args):
    conn = connect()
    items = {i["shortcode"]: i for i in posts(conn, args.project)}
    lines = [f"# Formulas, project #{args.project}", "", METRICS, ""]
    if args.groups:
        groups = json.loads(Path(args.groups).read_text())
        lines += ["## Formulas", "",
                  "| Formula | Posts | Creators | Median plays ÷ followers | Median saves per 1,000 | Median plays | Most saved |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        rows = []
        for name, codes in groups.items():
            members = [items[c] for c in codes if c in items]
            missing = [c for c in codes if c not in items]
            if missing:
                print(f"{name}: not outliers in this project, skipped: {', '.join(missing)}")
            if not members:
                continue
            best = max(members, key=lambda m: m["saves_per_1k"] or -1)
            rows.append((med(m["saves_per_1k"] for m in members) or -1, name, members, best))
        for saves, name, members, best in sorted(rows, key=lambda r: r[0], reverse=True):
            creators = len({m["handle"] for m in members})
            proof = "" if len(members) >= 3 and creators >= 2 else " (a lead)" if creators >= 2 else " (one creator)"
            lines.append(f"| {name}{proof} | {len(members)} | {creators} | "
                         f"{med(m['ratio'] for m in members)}× | {saves if saves >= 0 else '-'} | "
                         f"{med(m['plays'] for m in members):,.0f} | {best['handle']} ({best['saves_per_1k']}) |")
        lines.append("")
    done = [i for i in items.values() if i["torn_down"]]
    covers = [i["cover"] or "" for i in done]
    words = [len(c.split()) for c in covers if c]
    sounds = Counter(i["sound"] for i in done if i["sound"])
    lines += [f"## Across all {len(done)} torn-down winners", "",
              f"- Slides: median {med(i['slides'] for i in done)}, most common {Counter(i['slides'] for i in done).most_common(4)}",
              f"- Shape: {Counter(i['aspect'] for i in done).most_common()}",
              f"- Cover words: median {med(words)}" + (f", middle half {sorted(words)[len(words) // 4]}–{sorted(words)[3 * len(words) // 4]}" if words else ""),
              f"- Covers with a number: {sum(bool(re.search(r'[0-9]', c)) for c in covers)} of {len(covers)}",
              f"- Sound: original sound on {sum(1 for i in done if (i['sound'] or '').lower().startswith('original sound'))}, "
              f"a song on {sum(1 for i in done if i['sound'] and not i['sound'].lower().startswith('original sound'))}, none on {sum(1 for i in done if not i['sound'])}",
              f"- Sounds under 2+ winners: " + ("; ".join(f"{s} ({n})" for s, n in sounds.most_common() if n > 1) or "none"),
              f"- Ask: {Counter(i['cta'] for i in done).most_common(6)}",
              f"- Type: {Counter(i['type'] for i in done).most_common(8)}",
              f"- Promotions: {sum(i['sponsored'] for i in done)} marked as ads or with ad hashtags or codes, "
              f"{sum(i['campaign'] for i in done)} in campaigns (same caption on several accounts), "
              f"{sum(i['app_account'] for i in done)} from app accounts. They show a brand can ride a format; "
              f"weigh them apart from creators' own posts",
              f"- Median saves per 1,000 (TikTok): {med(i['saves_per_1k'] for i in items.values())}", ""]
    text = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(text)
    print(text)


def sheet(args):
    from PIL import Image, ImageDraw, ImageFont
    conn = connect()
    rows, h, gap = [], args.height, 10
    for sc in args.shortcodes:
        slides = sorted((MEDIA / sc).glob("slide_*.jpg"))[: args.max]
        if not slides:
            print(f"{sc}: no slides on disk (tear it down first)")
            continue
        ims = [Image.open(p).convert("RGB") for p in slides]
        ims = [im.resize((round(im.width * h / im.height), h)) for im in ims]
        r = conn.execute("SELECT r.username, o.ratio FROM reels r LEFT JOIN outliers o ON o.shortcode = r.shortcode "
                         "WHERE r.shortcode = ?", (sc,)).fetchone()
        rows.append((f"{handle(r['username']) if r else sc} · {r['ratio'] if r and r['ratio'] else '?'}x", ims))
    if not rows:
        raise SystemExit("Nothing to draw")
    label = 34
    width = max(sum(im.width for im in ims) + gap * (len(ims) - 1) for _, ims in rows)
    canvas = Image.new("RGB", (width, len(rows) * (h + label + gap)), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default(size=26)
    except TypeError:  # Pillow before 10.1
        font = ImageFont.load_default()
    y = 0
    for title, ims in rows:
        draw.text((4, y + 4), title, fill="black", font=font)
        x = 0
        for im in ims:
            canvas.paste(im, (x, y + label))
            x += im.width + gap
        y += h + label + gap
    canvas.save(args.out, quality=85)
    print(f"{len(rows)} posts -> {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("refs")
    p.add_argument("project", type=int)
    p.add_argument("--out")
    p.set_defaults(fn=refs)
    p = sub.add_parser("stats")
    p.add_argument("project", type=int)
    p.add_argument("groups", nargs="?")
    p.add_argument("--out")
    p.set_defaults(fn=stats)
    p = sub.add_parser("sheet")
    p.add_argument("shortcodes", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--max", type=int, default=10)
    p.set_defaults(fn=sheet)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
