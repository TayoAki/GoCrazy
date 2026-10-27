"""Find real, freely licensed photos for a post's photo spots, choose them by looking, and keep their credits.

    python3 find-photos.py search "<query>" <post folder> --key <photo key> [--src commons,openverse] [--n 12]
    python3 find-photos.py get <post folder> --key <photo key> <number on the sheet>
    python3 find-photos.py label <post folder> --key <photo key> <number>     # a product's nutrition label photo
    python3 find-photos.py collage <post folder> --key cover --cols 2 popcorn greek-yogurt light-mayo beef-93 skim-milk

search writes <post>/photo-search/<key>.json (the candidates) and <key>.jpg, a numbered contact sheet showing each
photo with its licence, so you pick by looking at it, never by its title. get downloads the one you pick to
<post>/photos/<key>.jpg (what render.py fills the spot with) and records it in <post>/photos/SOURCES.md: title,
author, licence and page, the credit a CC BY or CC BY-SA photo needs.

Sources (no keys, no logins):
  commons    Wikimedia Commons files. Fast. It also holds many Unsplash, Pexels and Flickr photos under CC0 or
             CC BY; put "unsplash" or "pexels" in the query to find stock-style shots.
  openverse  Openverse (api.openverse.org), filtered to licences that allow commercial use and changes. It's
             slow (about 40 s a search) but covers more of Flickr.

Only licences that allow commercial use and changes are kept: CC0, public domain, CC BY and CC BY-SA. CC BY needs a
credit (put it in the caption); CC BY-SA also asks that what you make from it is shared under the same licence, so
prefer CC0, public domain and CC BY for marketing. Nothing here is generated: every candidate is a real photo with a
page you can open.
"""

import argparse
import datetime
import html
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": os.environ.get("PHOTO_UA", "SlideshowContentSkill/1.0 (slide research; contact via repo owner)")}
OK_LICENCE = re.compile(r"^(cc0|cc[ -]?zero|pd|public domain|pdm|cc[ -]by(-sa)?[ -]?[\d.]*|by(-sa)?)\b", re.I)


def get(url, timeout=60, tries=6):
    """Fetch, waiting out rate limits: Wikimedia answers 429 with a Retry-After when an address calls too often."""
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == tries - 1:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 5 * (attempt + 1)
            if wait > 90:
                raise RuntimeError(f"{urllib.parse.urlparse(url).netloc} asks to wait {wait // 60} min "
                                   "(it limits busy addresses); try the other source") from e
            print(f"rate-limited, waiting {wait} s", file=sys.stderr)
            time.sleep(wait)


def plain(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def commons(query, n):
    api = "https://commons.wikimedia.org/w/api.php?"
    found = json.loads(get(api + urllib.parse.urlencode({
        "action": "query", "list": "search", "srnamespace": 6, "srsearch": f"{query} filetype:bitmap",
        "srlimit": n * 2, "format": "json"})))["query"]["search"]
    if not found:
        return []
    info = json.loads(get(api + urllib.parse.urlencode({
        "action": "query", "titles": "|".join(r["title"] for r in found), "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 2000, "format": "json"})))["query"]["pages"]
    out = []
    for page in info.values():
        ii = (page.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        licence = plain((meta.get("LicenseShortName") or {}).get("value"))
        if not ii.get("mime", "").startswith("image/") or not OK_LICENCE.match(licence or ""):
            continue
        out.append({"src": "commons", "title": page["title"].removeprefix("File:"), "licence": licence,
                    "author": plain((meta.get("Artist") or {}).get("value"))[:120] or "unknown",
                    "licence_url": plain((meta.get("LicenseUrl") or {}).get("value")),
                    "page": ii.get("descriptionurl"), "url": ii.get("thumburl") or ii.get("url"),
                    "thumb": (ii.get("thumburl") or ii.get("url")).replace("/2000px-", "/400px-"),
                    "width": ii.get("width"), "height": ii.get("height")})
    return out[:n]


def openverse(query, n):
    url = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({
        "q": query, "license_type": "commercial,modification", "page_size": n, "mature": "false"})
    out = []
    for r in json.loads(get(url, timeout=90)).get("results", []):
        licence = f"{'CC0' if r['license'] == 'cc0' else 'Public domain' if r['license'] == 'pdm' else 'CC ' + r['license'].upper()}" \
                  f"{' ' + r['license_version'] if r.get('license_version') and r['license'] not in ('cc0', 'pdm') else ''}"
        out.append({"src": f"openverse/{r.get('source')}", "title": r.get("title") or "", "licence": licence,
                    "author": r.get("creator") or "unknown", "licence_url": r.get("license_url"),
                    "page": r.get("foreign_landing_url"), "url": r.get("url"), "thumb": r.get("thumbnail") or r.get("url"),
                    "width": r.get("width"), "height": r.get("height")})
    return out


def openfoodfacts(query, n):
    """Real packaged products, photographed by Open Food Facts contributors, with their nutrition label photos.
    Licence CC BY-SA 3.0 (credit "Open Food Facts contributors"). US products first."""
    fields = "code,product_name,brands,countries_tags,image_front_url,image_nutrition_url,serving_size,nutriments,images"
    url = "https://search.openfoodfacts.org/search?" + urllib.parse.urlencode({
        "q": f'{query} countries_tags:"en:united-states"', "page_size": n * 2, "fields": fields})
    out = []
    for r in json.loads(get(url)).get("hits", []):
        if not r.get("image_front_url"):
            continue
        nut = r.get("nutriments") or {}
        per = (f"{nut.get('energy-kcal_serving'):g} cal, {nut.get('proteins_serving', 0):g} g protein per {r.get('serving_size')}"
               if isinstance(nut.get("energy-kcal_serving"), (int, float)) else None)
        images = r.get("images") if isinstance(r.get("images"), dict) else {}
        front = next((v for k, v in images.items() if k.startswith("front") and isinstance(v, dict)), {})
        full = (front.get("sizes") or {}).get("full") or {}
        name = " ".join(x for x in [", ".join(r.get("brands") or []) if isinstance(r.get("brands"), list) else r.get("brands"),
                                    r.get("product_name")] if x)
        out.append({"src": "openfoodfacts", "title": name, "licence": "CC BY-SA 3.0", "author": "Open Food Facts contributors",
                    "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/",
                    "page": f"https://world.openfoodfacts.org/product/{r['code']}", "label_says": per,
                    "url": re.sub(r"\.\d+\.jpg$", ".full.jpg", r["image_front_url"]), "thumb": r["image_front_url"],
                    "label": r.get("image_nutrition_url"), "width": full.get("w"), "height": full.get("h")})
    return out[:n]


def sheet(cands, path, tw=300, th=300, cols=4):
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.load_default(size=17)
    except TypeError:
        font = ImageFont.load_default()
    rows = (len(cands) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * (tw + 10), rows * (th + 52)), "white")
    draw = ImageDraw.Draw(canvas)
    for k, c in enumerate(cands):
        x, y = (k % cols) * (tw + 10), (k // cols) * (th + 52)
        try:
            im = Image.open(io.BytesIO(get(c["thumb"]))).convert("RGB")
            im.thumbnail((tw, th))
            canvas.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        except Exception as e:
            draw.text((x + 8, y + 8), f"no preview: {type(e).__name__}", fill="red", font=font)
        size = f" · {c['width']}x{c['height']}" if c.get("width") else ""
        draw.text((x + 4, y + th + 4), f"{k + 1}. {c['licence']}{size}", fill="black", font=font)
        draw.text((x + 4, y + th + 26), (c.get("label_says") or c["title"])[:34], fill="#555", font=font)
    canvas.save(path, quality=85)


def search(args):
    folder = Path(args.post) / "photo-search"
    folder.mkdir(parents=True, exist_ok=True)
    cands = []
    for src in args.src.split(","):
        try:
            cands += {"commons": commons, "openverse": openverse, "openfoodfacts": openfoodfacts}[src.strip()](args.query, args.n)
        except Exception as e:
            print(f"{src}: {type(e).__name__}: {e}", file=sys.stderr)
    if not cands:
        raise SystemExit("Nothing found with a usable licence; try other words (what it looks like, not what it's called)")
    (folder / f"{args.key}.json").write_text(json.dumps({"query": args.query, "candidates": cands}, indent=1))
    sheet(cands, folder / f"{args.key}.jpg")
    print(f"{len(cands)} candidates -> {folder / (args.key + '.jpg')} (look at it, then: get {args.post} --key {args.key} <n>)")
    for k, c in enumerate(cands, 1):
        print(f"{k:2}. [{c['licence']}] {c['title'][:70]} · {c.get('label_says') or c['author'][:40]}")


def fetch(args):
    post = Path(args.post)
    cands = json.loads((post / "photo-search" / f"{args.key}.json").read_text())["candidates"]
    c = cands[args.n - 1]
    from PIL import Image
    im = Image.open(io.BytesIO(get(c["url"], timeout=120))).convert("RGB")
    im.thumbnail((2000, 2000))
    (post / "photos").mkdir(exist_ok=True)
    im.save(post / "photos" / f"{args.key}.jpg", quality=90)
    credits = post / "photos" / "SOURCES.md"
    rows = credits.read_text().splitlines() if credits.exists() else [
        "# Photo sources", "", "| Spot | Photo | Author | Licence | Page | Checked |", "| --- | --- | --- | --- | --- | --- |"]
    rows = [r for r in rows if not r.startswith(f"| {args.key} |")]
    rows.append(f"| {args.key} | {c['title'][:60]} | {c['author'][:60]} | {c['licence']} | {c['page']} | "
                f"{datetime.date.today()} |")
    credits.write_text("\n".join(rows) + "\n")
    need = "credit needed" if re.search(r"\bBY\b", c["licence"], re.I) else "no credit needed"
    if max(im.size) < 800:
        print(f"warning: only {im.width}x{im.height}, it will look soft on a slide; pick a bigger one if there is one")
    print(f"photos/{args.key}.jpg <- {c['title']} ({c['licence']}, {need}) {im.width}×{im.height}")


def label(args):
    """Download a product's nutrition label photo (Open Food Facts) to check the slide's numbers against it."""
    post = Path(args.post)
    c = json.loads((post / "photo-search" / f"{args.key}.json").read_text())["candidates"][args.n - 1]
    if not c.get("label"):
        raise SystemExit("No label photo for this one; check its page: " + c["page"])
    path = post / "photo-search" / f"{args.key}-{args.n}-label.jpg"
    path.write_bytes(get(re.sub(r"\.\d+\.jpg$", ".full.jpg", c["label"])))
    print(f"{path} ({c['title']}; its data says {c.get('label_says')}, read the photo, not the data)")


def collage(args):
    """A photo made of photos already in photos/ (e.g. a cover from the post's own products): rows of cells, each
    photo cropped to fill its cell. Every piece is a real photo with its own credit."""
    from PIL import Image, ImageOps
    post = Path(args.post)
    w, h, gap = args.width, args.height, 8
    keys = args.keys
    rows = [keys[i:i + args.cols] for i in range(0, len(keys), args.cols)]
    canvas = Image.new("RGB", (w, h), "white")
    rh = (h - gap * (len(rows) - 1)) // len(rows)
    for r, row in enumerate(rows):
        cw = (w - gap * (len(row) - 1)) // len(row)
        for c, key in enumerate(row):
            im = Image.open(post / "photos" / f"{key}.jpg").convert("RGB")
            canvas.paste(ImageOps.fit(im, (cw, rh)), (c * (cw + gap), r * (rh + gap)))
    canvas.save(post / "photos" / f"{args.key}.jpg", quality=90)
    credits = post / "photos" / "SOURCES.md"
    if credits.exists():
        rows_md = [r for r in credits.read_text().splitlines() if not r.startswith(f"| {args.key} |")]
        rows_md.append(f"| {args.key} | collage of {', '.join(keys)} (their credits above) | | | | {datetime.date.today()} |")
        credits.write_text("\n".join(rows_md) + "\n")
    print(f"photos/{args.key}.jpg <- collage of {', '.join(keys)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("post")
    p.add_argument("--key", required=True)
    p.add_argument("--src", default="commons")
    p.add_argument("--n", type=int, default=12)
    p.set_defaults(fn=search)
    p = sub.add_parser("get")
    p.add_argument("post")
    p.add_argument("--key", required=True)
    p.add_argument("n", type=int)
    p.set_defaults(fn=fetch)
    p = sub.add_parser("label")
    p.add_argument("post")
    p.add_argument("--key", required=True)
    p.add_argument("n", type=int)
    p.set_defaults(fn=label)
    p = sub.add_parser("collage")
    p.add_argument("post")
    p.add_argument("--key", required=True, help="the photo key to write, e.g. cover")
    p.add_argument("--cols", type=int, default=2)
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1440)
    p.add_argument("keys", nargs="+", help="photo keys already in photos/")
    p.set_defaults(fn=collage)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
