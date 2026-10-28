"""Read everything a clipping campaign links to, with Firecrawl, into the campaign's folder.

    python3 explore.py <campaign folder> --search "DreamMe TikTok slideshow campaign"   # find the campaign's pages
    python3 explore.py <campaign folder> --url <url> [--url <url> ...] [--follow]        # read these pages

Links in <folder>/campaign.txt (the campaign as the person pasted it) are read too. --follow also reads the documents
a page links to (Notion, Google Docs and Drive, Loom, YouTube, Whop, Content Rewards), one level deep. Each page is
saved as <folder>/sources/NN-<site>.md, and sources/index.md lists them all, with the ones behind a login marked
LOCKED: those need the person (once they've joined) to paste or export them.

The key is FIRECRAWL_API_KEY in the repo's .env (or the environment); never paste it into a command. A search costs
about 2 credits; each page read costs 1. Firecrawl doesn't read some sites (TikTok and Instagram among them): those
are reported, not worked around.
"""

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

API = "https://api.firecrawl.dev/v2"
DOCS = re.compile(r"notion\.(so|site)|docs\.google|drive\.google|loom\.com|youtube\.com/watch|youtu\.be|whop\.com|"
                  r"contentrewards\.com|gamma\.app|canva\.com/design|dropbox\.com", re.I)
LOCKED = re.compile(r"visible once you join|join to (unlock|see)|sign in to (continue|view)|request access|you need "
                    r"(permission|access)|log ?in to (view|continue)|private (page|video)|this video is private", re.I)


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


def call(path, body, timeout=180):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code in (402, 403):  # out of credits, or a site Firecrawl won't read: retrying won't help
                return {"success": False, "error": f"{e.code}: {detail[:300]}"}
            last = f"{e.code}: {detail[:300]}"
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e)
        time.sleep(4 * (attempt + 1))
    return {"success": False, "error": last}


def search(query, limit=8):
    found = (call("/search", {"query": query, "limit": limit}).get("data") or {}).get("web", [])
    for k, x in enumerate(found, 1):
        print(f"{k}. {x['url']}\n   {x.get('title', '')[:90]}\n   {(x.get('description') or '')[:160].replace(chr(10), ' ')}")
    print("\nRead the ones that are the campaign's own pages: explore.py <folder> --url <url> ...")
    return found


def slug(url):
    p = urlparse(url)
    return re.sub(r"[^a-z0-9]+", "-", (p.netloc.replace("www.", "") + p.path).lower()).strip("-")[:60]


def read(folder, url, index):
    if any(s["url"] == url for s in index):
        return None
    result = call("/scrape", {"url": url, "formats": ["markdown", "links"], "onlyMainContent": False, "waitFor": 3000})
    entry = {"url": url, "fetched": str(date.today())}
    if not result.get("success"):
        entry.update({"state": "FAILED", "note": result.get("error", "")[:200]})
        index.append(entry)
        print(f"FAILED  {url}\n        {entry['note']}")
        return None
    data = result.get("data") or {}
    md = data.get("markdown") or ""
    name = f"{len(index) + 1:02d}-{slug(url)}.md"
    title = (data.get("metadata") or {}).get("title") or ""
    (folder / "sources" / name).write_text(f"<!-- {title}\n{url}\nfetched {date.today()} -->\n\n{md}")
    locked = LOCKED.findall(md)
    entry.update({"file": f"sources/{name}", "title": title, "chars": len(md),
                  "state": "LOCKED" if locked else "read", "links": data.get("links") or []})
    index.append(entry)
    print(f"{entry['state']:7} {url}  ({len(md):,} characters{'; part is behind a login' if locked else ''})")
    return entry


def write_index(folder, index):
    rows = ["# Sources", "", "| # | State | Page | File | Note |", "| --- | --- | --- | --- | --- |"]
    for k, s in enumerate(index, 1):
        name = (s.get("title") or s["url"])[:70].replace("|", "\\|")
        rows.append(f"| {k} | {s['state']} | [{name}]({s['url']}) | {s.get('file', '')} | "
                    f"{s.get('note', '') or ('part is behind a login: ask the person to paste it once they have joined' if s['state'] == 'LOCKED' else '')} |")
    (folder / "sources" / "index.md").write_text("\n".join(rows) + "\n")
    (folder / "sources" / "index.json").write_text(json.dumps([{k: v for k, v in s.items() if k != "links"} for s in index], indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--search")
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--follow", action="store_true", help="also read the documents the pages link to, one level deep")
    args = ap.parse_args()
    folder = Path(args.folder)
    (folder / "sources").mkdir(parents=True, exist_ok=True)
    if args.search:
        search(args.search)
        if not args.url:
            return
    saved = folder / "sources" / "index.json"
    index = json.loads(saved.read_text()) if saved.exists() else []
    urls = list(args.url)
    if (folder / "campaign.txt").exists():
        urls += re.findall(r"https?://[^\s)>\]]+", (folder / "campaign.txt").read_text())
    if not urls and not index:
        raise SystemExit("No links: the pasted campaign has none. Find its pages with --search, or ask the person for "
                         "the links (onboarding guide, tutorial, content vault, the campaign page).")
    for url in dict.fromkeys(urls):
        entry = read(folder, url, index)
        if entry and args.follow:
            for link in dict.fromkeys(entry.get("links") or []):
                if DOCS.search(link) and urlparse(link).netloc != urlparse(url).netloc:
                    read(folder, link, index)
    write_index(folder, index)
    print(f"\n{len(index)} pages in {folder}/sources/index.md. Read each one before filling campaign.json.")


if __name__ == "__main__":
    main()
