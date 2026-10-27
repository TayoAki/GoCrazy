"""Get an iPhone app's real name, price, icon and screenshots from its App Store listing, for the post's brand tag and
its app slide.

    python3 app-store.py fetch <app id or apps.apple.com link> <post folder> [--country us]
    python3 app-store.py crop <post folder>/assets/appstore/01-home.jpg <post folder>/assets/app-home.jpg \\
        --box 0.086,0.252,0.914,1                      # cut the phone out of a store screenshot (fractions x1,y1,x2,y2)

fetch writes assets/app-icon.png and assets/appstore/<NN-name>.jpg (full size) into the post folder, plus a numbered
sheet assets/appstore/sheet.jpg to choose from, and prints the "brand" block to put in post.json. Store screenshots
usually wrap the phone in a headline; crop the phone out for the app slide, and choose one that shows the app's name.
These are the app's own marketing images, so use them only for that app's own posts.
"""

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) SlideshowContentSkill/1.0"}


def get(url, tries=4):
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def fetch(args):
    app_id = re.search(r"(?:id)?(\d{6,})", args.app)
    if not app_id:
        raise SystemExit("Give the app's numeric id or its apps.apple.com link")
    found = json.loads(get(f"https://itunes.apple.com/lookup?id={app_id.group(1)}&country={args.country}"))
    if not found.get("resultCount"):
        raise SystemExit(f"No App Store app {app_id.group(1)} in country {args.country}")
    app = found["results"][0]
    assets = Path(args.post) / "assets"
    shots = assets / "appstore"
    shots.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    import io
    icon = Image.open(io.BytesIO(get(re.sub(r"/\d+x\d+bb\.\w+$", "/1024x1024bb.png", app["artworkUrl512"]))))
    icon.convert("RGB").resize((256, 256)).save(assets / "app-icon.png")
    saved = []
    for k, url in enumerate(app.get("screenshotUrls") or [], 1):
        name = re.search(r"/([^/]+?)\.(?:png|jpg|jpeg)/[^/]+$", url)
        stem = re.sub(r"[^a-z0-9-]+", "-", (name.group(1) if name else f"{k:02d}").lower()).strip("-")
        full = re.sub(r"/\d+x\d+bb\.\w+$", "/1290x2796bb.jpg", url)
        path = shots / f"{k:02d}-{stem}.jpg" if not stem[:2].isdigit() else shots / f"{stem}.jpg"
        path.write_bytes(get(full))
        saved.append(path)
    if saved:
        thumbs = [Image.open(p).convert("RGB") for p in saved]
        tw = 260
        thumbs = [im.resize((tw, round(im.height * tw / im.width))) for im in thumbs]
        sheet = Image.new("RGB", (len(thumbs) * (tw + 10), max(t.height for t in thumbs)), "white")
        for k, t in enumerate(thumbs):
            sheet.paste(t, (k * (tw + 10), 0))
        sheet.save(shots / "sheet.jpg", quality=85)
    price = app.get("formattedPrice") or "?"
    print(f"{app['trackName']} by {app.get('sellerName')} · {price} · version {app.get('version')} · "
          f"released {str(app.get('releaseDate'))[:10]}")
    print(f"icon -> {assets / 'app-icon.png'}; {len(saved)} screenshots -> {shots} (look at sheet.jpg)")
    where = "Free on the App Store" if price.lower() == "free" else "On the App Store"
    print("\nAdd to post.json:")
    print(json.dumps({"brand": {"name": app["trackName"], "icon": "assets/app-icon.png", "where": where}}, indent=1))


def crop(args):
    from PIL import Image
    im = Image.open(args.src).convert("RGB")
    x1, y1, x2, y2 = (float(v) for v in args.box.split(","))
    out = im.crop((round(x1 * im.width), round(y1 * im.height), round(x2 * im.width), round(y2 * im.height)))
    out.save(args.dst, quality=92)
    print(f"{args.dst} ({out.width}x{out.height})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fetch")
    p.add_argument("app")
    p.add_argument("post")
    p.add_argument("--country", default="us")
    p.set_defaults(fn=fetch)
    p = sub.add_parser("crop")
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--box", required=True, help="x1,y1,x2,y2 as fractions of the image")
    p.set_defaults(fn=crop)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
