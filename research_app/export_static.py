"""Export a read-only snapshot of the app (UI + data + media) as a static site, e.g. for Vercel.

    python -m research_app.export_static --out site                 # everything
    python -m research_app.export_static --out site --no-transcripts  # leave out other creators' words

The snapshot answers the same GET routes the UI calls, from a bundled snapshot.js, and hides every action.
"""

import argparse
import base64
import json
import re
import shutil
from pathlib import Path

from . import server
from .config import MEDIA


def collect(project_ids=None, transcripts=True):
    routes = {"/api/vocab": server.vocab(), "/api/events": server.events(limit=60),
              "/api/status": {"scrapecreators": True, "openrouter": True, "ffmpeg": True, "credits": None}}
    projects = [p for p in server.list_projects() if not project_ids or p["id"] in project_ids]
    routes["/api/projects"] = projects
    for p in projects:
        base = f"/api/projects/{p['id']}"
        outliers = server.list_outliers(p["id"], status="all", sort="ratio")
        routes[base + "/outliers"] = outliers
        routes[base + "/creators"] = server.list_creators(p["id"])
        routes[base + "/patterns"] = server.patterns(p["id"])
        routes[base + "/runs"] = server.list_runs(p["id"])
        routes[base + "/rates"] = server.rates(p["id"])
        routes[base + "/plans"] = [{**plan, "input": {k: v for k, v in plan["input"].items() if k != "about"}}
                                   for plan in server.list_plans(p["id"]) if plan["status"] == "done"]
        for o in outliers:
            td = server.read_teardown(o["shortcode"])
            if td.get("data") and not transcripts:
                td["data"]["transcript"] = None
                td["data"]["caption"] = None
            routes[f"/api/teardowns/{o['shortcode']}"] = td
    return routes


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="site")
    ap.add_argument("--project", type=int, action="append", help="only these project ids (repeatable)")
    ap.add_argument("--no-transcripts", action="store_true", help="drop transcripts and captions")
    ap.add_argument("--inline-media", action="store_true", help="embed images in snapshot.js instead of copying files")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "static").mkdir(parents=True)
    routes = collect(args.project, transcripts=not args.no_transcripts)
    text = json.dumps({"generated_at": server.db.now(), "routes": routes}, ensure_ascii=False)

    used = sorted(set(re.findall(r'/media/([A-Za-z0-9_-]+/[A-Za-z0-9_.-]+\.jpg)', text)))
    if args.inline_media:
        for rel in used:
            data = base64.b64encode((MEDIA / rel).read_bytes()).decode() if (MEDIA / rel).exists() else ""
            text = text.replace(f'"/media/{rel}"', json.dumps(f"data:image/jpeg;base64,{data}" if data else ""))
    else:
        for rel in used:
            src = MEDIA / rel
            if src.exists():
                (out / "media" / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out / "media" / rel)
        text = text.replace('"/media/', '"media/')

    (out / "snapshot.js").write_text("window.SNAPSHOT = " + text + ";\n")
    static = Path(server.STATIC)
    shutil.copy2(static / "styles.css", out / "static" / "styles.css")
    shutil.copy2(static / "app.js", out / "static" / "app.js")
    html = (static / "index.html").read_text()
    html = html.replace('href="/static/styles.css"', 'href="static/styles.css"')
    html = html.replace('<script src="/static/app.js"></script>', '<script src="snapshot.js"></script>\n  <script src="static/app.js"></script>')
    (out / "index.html").write_text(html)
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"Wrote {out}/ · {len(used)} images · {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
