"""Keep a local copy of the TikTok and FTC rules this check cites, and search them for exact wording.

    python3 rules.py refresh                 # fetch every source with Firecrawl; says which changed since last time
    python3 rules.py status                  # each source, when it was fetched, and its size
    python3 rules.py search "<regex>" [--source <id>] [--context 2]   # matching lines, with the source's link
    python3 rules.py show <id>               # one source's text

The pages are saved to ~/.cache/tiktok-ftc-check/ (or $TIKTOK_FTC_CACHE), not in the repo: TikTok's text is TikTok's.
references/rules.md is the summary the check works from; when `refresh` reports a change, read the changed source and
update rules.md to match. The Firecrawl key comes from FIRECRAWL_API_KEY in the repo's .env (or the environment); never
paste it into a command. Each fetch costs one Firecrawl credit.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

CACHE = Path(os.environ.get("TIKTOK_FTC_CACHE") or Path.home() / ".cache/tiktok-ftc-check")
API = "https://api.firecrawl.dev/v2/scrape"

# Firecrawl won't serve TikTok's Community Guidelines pages ("we do not support this site"): read them with a normal web
# fetch (references/rules.md marks those quotes (CG)). refresh skips them rather than failing on them.
WEB_ONLY = {"tt-integrity", "tt-commercial", "tt-mental-health", "tt-fyf"}

SOURCES = [
    # TikTok: what any post may show or do
    ("tt-integrity", "TikTok Community Guidelines: Integrity and Authenticity (AI-generated content, fake accounts, "
     "fake engagement, misinformation)", "https://www.tiktok.com/community-guidelines/en/integrity-authenticity"),
    ("tt-commercial", "TikTok Community Guidelines: Regulated Goods and Commercial Activities (weight-loss products, "
     "drugs, paid promotion disclosure, scams)", "https://www.tiktok.com/community-guidelines/en/regulated-commercial-activities"),
    ("tt-mental-health", "TikTok Community Guidelines: Mental and Behavioral Health (disordered eating, body image, "
     "dangerous weight loss)", "https://www.tiktok.com/community-guidelines/en/mental-behavioral-health"),
    ("tt-fyf", "TikTok Community Guidelines: For You feed eligibility", "https://www.tiktok.com/community-guidelines/en/fyf-standards"),
    ("tt-branded", "TikTok Branded Content Policy", "https://www.tiktok.com/legal/page/global/bc-policy/en"),
    ("tt-disclosure", "TikTok Support: Promoting a brand, product, or service (the content disclosure setting)",
     "https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service"),
    ("tt-aigc", "TikTok Support: How is AI-generated content labeled on TikTok?",
     "https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content"),
    # FTC: US law for paid endorsements, testimonials and health claims
    ("ftc-endorsement-guides", "16 CFR Part 255: Guides Concerning the Use of Endorsements and Testimonials in "
     "Advertising (eCFR)", "https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-255"),
    ("ftc-reviews-rule", "16 CFR Part 465: Trade Regulation Rule on the Use of Consumer Reviews and Testimonials (eCFR)",
     "https://www.ecfr.gov/current/title-16/chapter-I/subchapter-D/part-465"),
    ("ftc-influencers", "FTC: Disclosures 101 for Social Media Influencers",
     "https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers"),
    ("ftc-endorsement-faq", "FTC: FTC's Endorsement Guides: What People Are Asking",
     "https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking"),
    ("ftc-health", "FTC: Health Products Compliance Guidance",
     "https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance"),
]


def key():
    if os.environ.get("FIRECRAWL_API_KEY"):
        return os.environ["FIRECRAWL_API_KEY"]
    for d in [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]:
        env = d / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("FIRECRAWL_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("No FIRECRAWL_API_KEY: add it to the repo's .env (FIRECRAWL_API_KEY=...)")


def scrape(url, tries=3):
    body = json.dumps({"url": url, "formats": ["markdown"], "onlyMainContent": True, "waitFor": 2000}).encode()
    for attempt in range(tries):
        req = urllib.request.Request(API, data=body, method="POST",
                                     headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.load(resp).get("data") or {}
            return data.get("markdown") or ""
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def path(sid):
    return CACHE / f"{sid}.md"


def meta():
    f = CACHE / "index.json"
    return json.loads(f.read_text()) if f.exists() else {}


def refresh(args):
    CACHE.mkdir(parents=True, exist_ok=True)
    index = meta()
    for sid, title, url in SOURCES:
        if args.only and sid not in args.only:
            continue
        if sid in WEB_ONLY:
            print(f"web      {sid}: read it with a web fetch (Firecrawl doesn't serve it): {url}")
            continue
        try:
            text = scrape(url)
        except RuntimeError as e:
            print(f"FAILED   {sid}: {e}")
            continue
        if len(text) < 500:
            print(f"FAILED   {sid}: only {len(text)} characters came back (blocked or moved?): {url}")
            continue
        digest = hashlib.sha256(text.encode()).hexdigest()[:16]
        old = index.get(sid, {})
        state = "new" if not old else "CHANGED" if old.get("sha") != digest else "same"
        path(sid).write_text(f"<!-- {title}\n{url}\nfetched {date.today()} -->\n\n{text}")
        index[sid] = {"title": title, "url": url, "fetched": str(date.today()), "sha": digest, "chars": len(text)}
        print(f"{state:8} {sid}: {len(text):,} characters")
    (CACHE / "index.json").write_text(json.dumps(index, indent=1))
    print(f"\nSaved to {CACHE}. Where a source CHANGED, read it and bring references/rules.md up to date.")


def status(_args):
    index = meta()
    for sid, title, url in SOURCES:
        m = index.get(sid)
        when = m["fetched"] if m else "web fetch" if sid in WEB_ONLY else "never fetched"
        print(f"{sid:24} {when:14} {m['chars'] if m else 0:>8,}  {url}")


def search(args):
    pattern = re.compile(args.pattern, re.I)
    found = 0
    for sid, title, url in SOURCES:
        if args.source and sid != args.source:
            continue
        if not path(sid).exists():
            continue
        lines = path(sid).read_text().splitlines()
        hits = [k for k, line in enumerate(lines) if pattern.search(line)]
        if not hits:
            continue
        print(f"\n== {sid}: {title}\n   {url}")
        shown = set()
        for k in hits:
            for j in range(max(0, k - args.context), min(len(lines), k + args.context + 1)):
                if j not in shown and lines[j].strip():
                    print(f"   {'>' if j == k else ' '} {lines[j][:300]}")
                    shown.add(j)
            found += 1
    if not found:
        print("No match. Run `rules.py refresh` if the cache is empty, or try other words.")


def show(args):
    if not path(args.id).exists():
        raise SystemExit(f"No cached copy of {args.id}; run: python3 rules.py refresh --only {args.id}")
    sys.stdout.write(path(args.id).read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("refresh")
    p.add_argument("--only", nargs="*", help="source ids to fetch (default: all)")
    p.set_defaults(fn=refresh)
    sub.add_parser("status").set_defaults(fn=status)
    p = sub.add_parser("search")
    p.add_argument("pattern")
    p.add_argument("--source")
    p.add_argument("--context", type=int, default=1)
    p.set_defaults(fn=search)
    p = sub.add_parser("show")
    p.add_argument("id")
    p.set_defaults(fn=show)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
