"""Send a rendered post to TikTok as a photo draft through Outstand (outstand.so). Drafts only: the post lands in the
account's TikTok inbox, and nothing is public until someone opens it in the TikTok app and posts it.

    python3 send-drafts.py accounts                                   # the accounts connected to your Outstand key
    python3 send-drafts.py send <post folder> --account <id> --caption "<text>"   # or --caption-file caption.txt

The key comes from OUTSTAND_API_KEY in the repo's .env (or the environment); never paste it into a command. The slides
(out/slide_*.png) are converted to JPEG, because TikTok photo posts take JPEG or WebP only, then uploaded to Outstand
(kept 60 days) and sent as one photo post in TikTok's MEDIA_UPLOAD mode, Outstand's default, which is a draft in the
creator's inbox. The result is saved to <post>/out/drafts.json.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.outstand.so"
UA = "Mozilla/5.0 (X11; Linux x86_64) SlideshowContentSkill/1.0"  # Outstand's Cloudflare refuses Python's default


def key():
    if os.environ.get("OUTSTAND_API_KEY"):
        return os.environ["OUTSTAND_API_KEY"]
    for d in [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]:
        env = d / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("OUTSTAND_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("No OUTSTAND_API_KEY: add it to the repo's .env (OUTSTAND_API_KEY=...)")


def call(method, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": f"Bearer {key()}", "User-Agent": UA, "Accept": "application/json"}
    if data:
        headers["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(API + path, data=data, method=method, headers=headers),
                                    timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Outstand {method} {path}: {e.code} {e.read().decode(errors='replace')[:400]}")


def accounts(_args=None):
    found = call("GET", "/v1/social-accounts").get("data", [])
    for a in found:
        print(f"{a['id']}  {a['network']:<10} {a.get('username') or ''}  ({a.get('nickname')})"
              + ("" if a.get("isActive") else "  INACTIVE"))
    return found


def upload(path):
    """Outstand's three steps: ask for an upload URL, PUT the bytes, confirm. Returns the public URL."""
    slot = call("POST", "/v1/media/upload", {"filename": path.name, "content_type": "image/jpeg"})["data"]
    req = urllib.request.Request(slot["upload_url"], data=path.read_bytes(), method="PUT",
                                 headers={"Content-Type": "image/jpeg", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        if resp.status >= 300:
            raise SystemExit(f"Upload of {path.name} failed: {resp.status}")
    done = call("POST", f"/v1/media/{slot['id']}/confirm", {"size": path.stat().st_size})["data"]
    return done["url"]


def send(args):
    post = Path(args.post)
    slides = sorted((post / "out").glob("slide_*.png"))
    if not slides:
        raise SystemExit(f"No slides in {post / 'out'}; run render.py first")
    if not 1 <= len(slides) <= 35:
        raise SystemExit(f"TikTok photo posts take 1 to 35 images, this post has {len(slides)}")
    account = next((a for a in call("GET", "/v1/social-accounts").get("data", [])
                    if args.account in (a["id"], a.get("username"))), None)
    if not account:
        raise SystemExit(f"No connected account {args.account!r}; see: python3 {Path(__file__).name} accounts")
    if account["network"] != "tiktok":
        raise SystemExit(f"{args.account} is a {account['network']} account. This script only makes TikTok drafts; "
                         "other networks would publish for real.")
    caption = Path(args.caption_file).read_text().strip() if args.caption_file else (args.caption or "").strip()
    if not caption:
        raise SystemExit("Give the post a caption (--caption or --caption-file)")

    from PIL import Image
    jpg_dir = post / "out" / "jpg"
    jpg_dir.mkdir(exist_ok=True)
    media = []
    for png in slides:
        jpg = jpg_dir / (png.stem + ".jpg")
        Image.open(png).convert("RGB").save(jpg, quality=92)
        print(f"uploading {jpg.name}", flush=True)
        media.append({"url": upload(jpg), "filename": jpg.name})

    body = {"containers": [{"content": caption, "media": media}], "accounts": [account["id"]],
            "tiktok": {"postMode": "MEDIA_UPLOAD"}}
    result = call("POST", "/v1/posts/", body, timeout=180)
    (post / "out" / "drafts.json").write_text(json.dumps({"request": body, "response": result}, indent=1))
    post_info = result.get("post") or result.get("data") or result
    print(json.dumps(post_info, indent=1)[:1500])
    print(f"\nSent {len(media)} slides to @{account.get('username')} as a TikTok draft (inbox). "
          "Open TikTok, check the inbox or drafts, add the sound, and post it from there.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("accounts").set_defaults(fn=accounts)
    p = sub.add_parser("send")
    p.add_argument("post")
    p.add_argument("--account", required=True, help="the account's id or username, from: accounts")
    p.add_argument("--caption")
    p.add_argument("--caption-file")
    p.set_defaults(fn=send)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
