"""Set up a campaign folder, check its campaign.json, and work out what the pay actually means.

    python3 campaign.py new <slug>                 # briefs/campaign-<slug>/ with campaign.txt and a campaign.json to fill
    python3 campaign.py check <folder>             # missing fields, open questions, and the payout math
    python3 campaign.py pay <folder>               # just the payout math, as a markdown table for the brief

campaign.json's fields are in references/campaign-schema.md. Every rule keeps the words it came from and where, so the
brief and the compliance check (tiktok-ftc-check) can quote it.
"""

import json
import sys
from pathlib import Path

REQUIRED = {"name": str, "brand": dict, "platform": str, "format": str, "pay": dict, "submit": dict, "rules": list}
KINDS = ("platform", "format", "audience", "language", "content", "account", "tools", "quality", "pay", "submit")
SKELETON = {
    "name": "", "brand": {"name": "", "what": "", "store": "", "maker": ""},
    "organizer": {"name": "", "platform": "", "url": ""},
    "platform": "tiktok", "format": "photo slideshow (native)", "slides": [5, 10], "language": "English",
    "audience": {"tier1_min": 0.4, "countries": ["US", "UK", "CA", "AU"]},
    "pay": {"per_1k": 1.0, "min_payout": 1, "max_per_post": 400, "budget": 0, "min_views": 1000, "currency": "USD",
            "budget_left": None},
    "submit": {"within_minutes": None, "proof": [], "payouts": ""},
    "rules": [{"id": "C1", "kind": "content", "text": "", "source": "campaign.txt line N", "status": "stated", "note": ""}],
    "locked": [], "open_questions": [],
}


def money(x):
    return f"${x:,.0f}" if x >= 10 or x == int(x) else f"${x:,.2f}"


def payout(pay):
    per = float(pay.get("per_1k") or 0)
    if not per:
        return []
    cap, budget = float(pay.get("max_per_post") or 0), float(pay.get("budget") or 0)
    rows = [("Views to qualify", f"{int(pay.get('min_views') or 0):,}",
             f"earns {money(per * (pay.get('min_views') or 0) / 1000)}")]
    if cap:
        rows.append(("Views where the cap is reached", f"{int(cap / per * 1000):,}", f"{money(cap)} per post, no more"))
    if budget:
        rows.append(("Views the whole budget pays for", f"{int(budget / per * 1000):,}", f"{money(budget)}"))
        if cap:
            rows.append(("Capped posts the budget covers", f"{budget / cap:,.0f}", "then the campaign is spent"))
    left = pay.get("budget_left")
    if left is not None:
        rows.append(("Budget left (when last checked)", money(float(left)),
                     f"{int(float(left) / per * 1000):,} more paid views across all creators"))
    for views in (1_000, 10_000, 50_000, 100_000, 400_000, 1_000_000):
        earned = min(cap or 1e12, per * views / 1000)
        if views >= (pay.get("min_views") or 0):
            rows.append((f"A post with {views:,} views", "", money(earned) + (" (capped)" if cap and per * views / 1000 > cap else "")))
    return rows


def table(rows):
    out = ["| | Views | Pay |", "| --- | --- | --- |"]
    out += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    return "\n".join(out)


def load(folder):
    f = Path(folder) / "campaign.json"
    if not f.exists():
        raise SystemExit(f"No {f}. Start one: python3 campaign.py new <slug>")
    return json.loads(f.read_text())


def new(slug):
    folder = Path("briefs") / f"campaign-{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "sources").mkdir(exist_ok=True)
    if not (folder / "campaign.txt").exists():
        (folder / "campaign.txt").write_text("Paste the campaign here, exactly as the brand or agency wrote it.\n")
    if not (folder / "campaign.json").exists():
        (folder / "campaign.json").write_text(json.dumps(SKELETON, indent=1, ensure_ascii=False))
    print(f"{folder}/: paste the campaign into campaign.txt, read its pages (explore.py), then fill campaign.json.")


def check(folder):
    c = load(folder)
    problems = [f"missing or wrong type: {k}" for k, t in REQUIRED.items() if not isinstance(c.get(k), t) or not c.get(k)]
    for r in c.get("rules", []):
        if not r.get("text") or not r.get("source"):
            problems.append(f"rule {r.get('id')}: needs its text and where it came from")
        if r.get("kind") not in KINDS:
            problems.append(f"rule {r.get('id')}: kind should be one of {', '.join(KINDS)}")
        if r.get("status") not in ("stated", "unclear", "conflict"):
            problems.append(f"rule {r.get('id')}: status should be stated, unclear or conflict")
    print(f"# {c.get('name')}\n")
    for p in problems:
        print(f"- FIX: {p}")
    unclear = [r for r in c.get("rules", []) if r.get("status") in ("unclear", "conflict")]
    for r in unclear:
        print(f"- {r['status'].upper()}: {r['id']} {r['text']} ({r.get('note', '')})")
    for q in c.get("open_questions", []):
        print(f"- ASK: {q}")
    for item in c.get("locked", []):
        print(f"- LOCKED: {item} (behind the campaign's login: ask the person to paste it once they've joined)")
    print("\n" + table(payout(c.get("pay", {}))))
    by_kind = {}
    for r in c.get("rules", []):
        by_kind.setdefault(r.get("kind"), []).append(r["id"])
    print("\nRules by kind: " + "; ".join(f"{k} {', '.join(v)}" for k, v in by_kind.items()))
    print("\nNext: write brief.md, then run the check (tiktok-ftc-check) on campaign.txt, campaign.json and brief.md.")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("new", "check", "pay"):
        raise SystemExit(__doc__)
    cmd, arg = sys.argv[1:]
    if cmd == "new":
        new(arg)
    elif cmd == "check":
        check(arg)
    else:
        print(table(payout(load(arg).get("pay", {}))))


if __name__ == "__main__":
    main()
