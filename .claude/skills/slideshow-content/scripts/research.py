"""Drive this repo's research app (research_app/) over its local HTTP API: start it, create a project, run the outlier
search, and tear down the slideshow and carousel outliers.

    python3 research.py serve                                   # start the app if it isn't answering (port 8000)
    python3 research.py projects                                # list projects (id, name, keywords, outliers)
    python3 research.py new --name "Weight Class" --niche "calorie tracking app" \\
        --keywords "calorie deficit, high protein snacks, food swaps" --study "calai.app, myfitnesspal" --budget 400
    python3 research.py kinds <project id> --kinds slideshows   # switch post types on an existing project
    python3 research.py run <project id>                        # search; prints progress until it finishes
    python3 research.py teardown <project id> [--kinds slideshow,carousel] [--parallel 3] [--limit 40]

Everything goes through HTTP on purpose. Importing research_app.server in another process runs its start-up, which marks
any run, plan or render in progress as failed, so never import it while the app is working.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path



def find_repo():
    """The checkout holding research_app/: $RESEARCH_REPO, else the working folder or a parent, else this skill's repo."""
    starts = [Path(os.environ["RESEARCH_REPO"])] if os.environ.get("RESEARCH_REPO") else []
    starts += [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]
    return next((d for d in starts if (d / "research_app" / "server.py").exists()), Path.cwd())


REPO = find_repo()
BASE = os.environ.get("RESEARCH_APP_URL", "http://127.0.0.1:8000")


def call(method, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except ValueError:
            pass
        raise SystemExit(f"{method} {path}: {e.code} {detail}")


def healthy():
    try:
        call("GET", "/api/health", timeout=3)
        return True
    except (SystemExit, OSError):
        return False


def serve(_args=None):
    if healthy():
        print(f"research app is up at {BASE}")
        return
    log = REPO / "data" / "server.log"
    log.parent.mkdir(exist_ok=True)
    subprocess.Popen([sys.executable, "-m", "research_app"], cwd=REPO, stdout=open(log, "a"), stderr=subprocess.STDOUT,
                     start_new_session=True)
    for _ in range(60):
        time.sleep(1)
        if healthy():
            status = call("GET", "/api/status")
            print(f"research app started at {BASE} (log: {log})")
            print(f"ScrapeCreators key: {'yes' if status['scrapecreators'] else 'MISSING'} · credits left: "
                  f"{status.get('credits')} · AI provider: {status.get('ai_provider')} · ffmpeg: {status.get('ffmpeg')}")
            return
    raise SystemExit(f"The app didn't start; see {log}")


def projects(_args):
    for p in call("GET", "/api/projects"):
        kinds = [k for k in ("reels", "carousels", "slideshows", "youtube_videos", "youtube_shorts") if p["settings"].get(k)]
        print(f"#{p['id']} {p['name']} · {p['outliers']} outliers · {', '.join(kinds)}\n   keywords: {', '.join(p['keywords'])}")


def split(value):
    return [x.strip().lstrip("@") for x in (value or "").replace("\n", ",").split(",") if x.strip()]


def kind_settings(kinds):
    kinds = set(split(kinds))
    unknown = kinds - {"reels", "carousels", "slideshows"}
    if unknown:
        raise SystemExit(f"Unknown post type {', '.join(sorted(unknown))}: use slideshows, carousels, reels")
    return {"reels": "reels" in kinds, "carousels": "carousels" in kinds, "slideshows": "slideshows" in kinds}


def new(args):
    settings = {**kind_settings(args.kinds), "credit_budget": args.budget, "max_creators": args.max_creators}
    if args.study:
        settings["study_accounts"] = split(args.study)
        if not (settings["reels"] or settings["carousels"]):
            print("note: study accounts are Instagram handles and are only scanned when reels or carousels are on")
    project = call("POST", "/api/projects", {"name": args.name, "niche": args.niche, "keywords": split(args.keywords),
                                             "settings": settings})
    print(f"project #{project['id']} created: {project['name']} · {len(project['keywords'])} keywords · "
          f"budget {settings['credit_budget']} credits")


def kinds(args):
    settings = kind_settings(args.kinds)
    if args.budget:
        settings["credit_budget"] = args.budget
    project = call("PATCH", f"/api/projects/{args.project}", {"settings": settings})
    on = [k for k in ("reels", "carousels", "slideshows") if project["settings"].get(k)]
    print(f"project #{project['id']}: {', '.join(on)} · budget {project['settings'].get('credit_budget')} credits")


def run(args):
    run_id = call("POST", f"/api/projects/{args.project}/runs")["run_id"]
    print(f"run #{run_id} started", flush=True)
    last = None
    while True:
        r = call("GET", f"/api/runs/{run_id}")
        line = f"[{r['status']}] {r.get('phase') or ''} {round(100 * (r.get('progress') or 0))}% · " \
               f"{r.get('credits_used') or 0} credits · {r.get('message') or ''}"
        if line != last:
            print(line, flush=True)
            last = line
        if r["status"] not in ("running", "queued"):
            break
        time.sleep(10)
    counts = {}
    for o in call("GET", f"/api/projects/{args.project}/outliers"):
        counts[o["kind"]] = counts.get(o["kind"], 0) + 1
    print("outliers by kind:", counts)


def teardown(args):
    kinds = set(split(args.kinds))
    outliers = [o for o in call("GET", f"/api/projects/{args.project}/outliers")
                if o["kind"] in kinds and o.get("teardown_status") not in ("done", "running", "queued")
                and o["ratio"] >= args.min_ratio]
    todo = [o["shortcode"] for o in outliers][: args.limit or None]
    print(f"to tear down: {len(todo)} ({', '.join(sorted(kinds))})", flush=True)
    running, done, failed = [], 0, 0
    while todo or running:
        while todo and len(running) < args.parallel:
            sc = todo.pop(0)
            try:
                call("POST", f"/api/teardowns/{sc}?project_id={args.project}")
                running.append(sc)
            except SystemExit as e:
                print(f"could not start {sc}: {e}", flush=True)
        time.sleep(5)
        for sc in list(running):
            td = call("GET", f"/api/teardowns/{sc}")
            if td.get("status") in ("done", "failed"):
                running.remove(sc)
                done += 1
                failed += td["status"] == "failed"
                print(f"{done}: {sc} {td['status']} {(td.get('error') or '')[:120]}", flush=True)
    print(f"finished: {done - failed} torn down, {failed} failed")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve").set_defaults(fn=serve)
    sub.add_parser("projects").set_defaults(fn=projects)
    p = sub.add_parser("new")
    p.add_argument("--name", required=True)
    p.add_argument("--niche", default="")
    p.add_argument("--keywords", required=True, help="comma-separated")
    p.add_argument("--study", help="comma-separated handles to scan deeper, e.g. competitors' accounts")
    p.add_argument("--kinds", default="slideshows,carousels", help="slideshows, carousels, reels")
    p.add_argument("--budget", type=int, default=400, help="ScrapeCreators credit cap for one run")
    p.add_argument("--max-creators", type=int, default=40)
    p.set_defaults(fn=new)
    p = sub.add_parser("kinds")
    p.add_argument("project", type=int)
    p.add_argument("--kinds", required=True, help="slideshows, carousels, reels (the ones not named are switched off)")
    p.add_argument("--budget", type=int)
    p.set_defaults(fn=kinds)
    p = sub.add_parser("run")
    p.add_argument("project", type=int)
    p.set_defaults(fn=run)
    p = sub.add_parser("teardown")
    p.add_argument("project", type=int)
    p.add_argument("--kinds", default="slideshow,carousel")
    p.add_argument("--parallel", type=int, default=3)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--min-ratio", type=float, default=0)
    p.set_defaults(fn=teardown)
    args = ap.parse_args()
    if args.cmd != "serve" and not healthy():
        raise SystemExit(f"The research app isn't answering at {BASE}. Start it: python3 {Path(__file__).name} serve")
    args.fn(args)


if __name__ == "__main__":
    main()
