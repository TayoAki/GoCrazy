import base64
import json
import os
import re
import secrets
import shutil
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import annotate, backup, brief, config, db, doubledown, media, pipeline, planner, teardown
from .config import DATA, DEFAULT_SETTINGS, MEDIA
from .scrapecreators import ScrapeCreators, ScrapeError

config.load_env()
db.init()
MEDIA.mkdir(parents=True, exist_ok=True)
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Outlier Research")
APP_PASSWORD = os.environ.get("APP_PASSWORD") or None
DEPLOYED = bool(os.environ.get("RAILWAY_ENVIRONMENT"))


@app.middleware("http")
async def require_password(request: Request, call_next):
    """With APP_PASSWORD set, every page and API call needs it (browser sign-in box; any username)."""
    if request.url.path == "/api/health":
        return await call_next(request)
    if APP_PASSWORD:
        if not _password_ok(request.headers.get("authorization", "")):
            return Response("Password required", status_code=401, headers={"WWW-Authenticate": 'Basic realm="Outlier Research"'})
    elif DEPLOYED:  # never serve a deployed copy without a password: it can spend your API credits
        return Response("Set the APP_PASSWORD variable on this service to use the app.", status_code=503)
    return await call_next(request)


def _password_ok(header):
    if not header.startswith("Basic "):
        return False
    try:
        given = base64.b64decode(header[6:], validate=True).decode().partition(":")[2]
    except ValueError:  # bad base64 or bad UTF-8
        return False
    return secrets.compare_digest(given.encode(), APP_PASSWORD.encode())


@app.get("/api/health")
def health():
    return {"ok": True}
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/media", StaticFiles(directory=MEDIA), name="media")

_balance = {"value": None, "checked": 0.0, "error": None}


class ProjectIn(BaseModel):
    name: str
    niche: str = ""
    keywords: list[str]
    settings: dict[str, Any] = {}


class ProjectPatch(BaseModel):
    name: str | None = None
    niche: str | None = None
    keywords: list[str] | None = None
    settings: dict[str, Any] | None = None


class StatusPatch(BaseModel):
    status: str


class FieldsPatch(BaseModel):
    fields: dict[str, Any]


class PlanIn(BaseModel):
    about: str = ""
    followers: int | None = None
    start_date: str | None = None
    posts: int = 7


def clean_keywords(keywords):
    seen = []
    for kw in keywords:
        kw = " ".join(kw.split())
        if kw and kw.lower() not in (s.lower() for s in seen):
            seen.append(kw)
    return seen


def clean_settings(settings):
    out = {}
    for key, default in DEFAULT_SETTINGS.items():
        if key == "study_accounts" and key in settings:
            raw = settings[key] if isinstance(settings[key], list) else re.split(r"[\s,]+", str(settings[key] or ""))
            out[key] = list(dict.fromkeys(h.strip().lstrip("@").lower() for h in raw if str(h).strip().lstrip("@")))
        elif key in settings and settings[key] not in (None, ""):
            try:
                out[key] = type(default)(settings[key]) if not isinstance(default, bool) else bool(settings[key])
            except (TypeError, ValueError):
                raise HTTPException(400, f"Invalid value for {key}")
    return out


def get_project(conn, project_id):
    row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    return row


def project_dict(conn, row):
    counts = conn.execute("""SELECT COUNT(*) total, SUM(status='saved') saved, SUM(status='dismissed') dismissed
                             FROM outliers WHERE project_id=?""", (row["id"],)).fetchone()
    run = conn.execute("SELECT * FROM runs WHERE project_id=? ORDER BY id DESC LIMIT 1", (row["id"],)).fetchone()
    return {"id": row["id"], "name": row["name"], "niche": row["niche"], "keywords": json.loads(row["keywords"]),
            "settings": db.project_settings(row), "created_at": row["created_at"],
            "outliers": counts["total"] or 0, "saved": counts["saved"] or 0, "dismissed": counts["dismissed"] or 0,
            "last_run": run_dict(run) if run else None}


def run_dict(row):
    d = dict(row)
    d["stats"] = json.loads(d["stats"]) if d.get("stats") else None
    return d


def cover_url(shortcode):
    return f"/media/{shortcode}/cover.jpg" if (MEDIA / shortcode / "cover.jpg").exists() else None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status(refresh: bool = False):
    key = config.scrapecreators_key()
    if key and (refresh or time.time() - _balance["checked"] > 120):
        try:
            _balance.update(value=ScrapeCreators(key).balance(), error=None)
        except ScrapeError as e:
            _balance["error"] = str(e)
        _balance["checked"] = time.time()
    return {"scrapecreators": bool(key), "openrouter": bool(config.openrouter_key()), "ffmpeg": config.has_ffmpeg(),
            "credits": _balance["value"], "credits_error": _balance["error"]}


@app.get("/api/vocab")
def vocab():
    return {"vocab": annotate.VOCAB, "elements": annotate.ELEMENTS, "defaults": DEFAULT_SETTINGS}


@app.get("/api/projects")
def list_projects():
    with db.connect() as conn:
        return [project_dict(conn, r) for r in conn.execute("SELECT * FROM projects ORDER BY id DESC")]


@app.post("/api/projects")
def create_project(body: ProjectIn):
    keywords = clean_keywords(body.keywords)
    if not body.name.strip() or not keywords:
        raise HTTPException(400, "A name and at least one keyword are required")
    with db.connect() as conn:
        cur = conn.execute("INSERT INTO projects (name, niche, keywords, settings, created_at) VALUES (?,?,?,?,?)",
                           (body.name.strip(), body.niche.strip(), json.dumps(keywords),
                            json.dumps(clean_settings(body.settings)), db.now()))
        project_id = cur.lastrowid
    db.log(project_id, "info", f'Created project "{body.name.strip()}" with {len(keywords)} keywords')
    with db.connect() as conn:
        return project_dict(conn, get_project(conn, project_id))


@app.get("/api/projects/{project_id}")
def read_project(project_id: int):
    with db.connect() as conn:
        return project_dict(conn, get_project(conn, project_id))


@app.patch("/api/projects/{project_id}")
def update_project(project_id: int, body: ProjectPatch):
    with db.connect() as conn:
        row = get_project(conn, project_id)
        settings = {**json.loads(row["settings"]), **clean_settings(body.settings or {})}
        keywords = clean_keywords(body.keywords) if body.keywords is not None else json.loads(row["keywords"])
        if not keywords:
            raise HTTPException(400, "At least one keyword is required")
        conn.execute("UPDATE projects SET name=?, niche=?, keywords=?, settings=? WHERE id=?",
                     ((body.name or row["name"]).strip(), (body.niche if body.niche is not None else row["niche"]).strip(),
                      json.dumps(keywords), json.dumps(settings), project_id))
        return project_dict(conn, get_project(conn, project_id))


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int):
    with db.connect() as conn:
        get_project(conn, project_id)
        for table in ("outliers", "project_creators", "runs", "events"):
            conn.execute(f"DELETE FROM {table} WHERE project_id=?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    return {"ok": True}


@app.post("/api/projects/{project_id}/runs")
def start_run(project_id: int):
    if not config.scrapecreators_key():
        raise HTTPException(400, "SCRAPECREATORS_API_KEY is not set")
    with db.connect() as conn:
        get_project(conn, project_id)
    try:
        run_id = pipeline.start_run(project_id)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"run_id": run_id}


@app.get("/api/projects/{project_id}/runs")
def list_runs(project_id: int):
    with db.connect() as conn:
        return [run_dict(r) for r in conn.execute("SELECT * FROM runs WHERE project_id=? ORDER BY id DESC LIMIT 20", (project_id,))]


@app.get("/api/runs/{run_id}")
def read_run(run_id: int):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Run not found")
    return run_dict(row)


@app.post("/api/runs/{run_id}/stop")
def stop_run(run_id: int):
    pipeline.stop_run(run_id)
    return {"ok": True}


@app.get("/api/projects/{project_id}/outliers")
def list_outliers(project_id: int, status: str = "active", sort: str = "ratio"):
    order = {"ratio": "o.ratio DESC", "views": "r.views DESC", "newest": "r.taken_at DESC"}.get(sort, "o.ratio DESC")
    where = {"active": "o.status <> 'dismissed'", "saved": "o.status = 'saved'", "dismissed": "o.status = 'dismissed'",
             "all": "1=1"}.get(status, "o.status <> 'dismissed'")
    with db.connect() as conn:
        rows = conn.execute(f"""
            SELECT o.shortcode, o.ratio, o.keyword, o.status, o.basis, r.url, r.username, r.views, r.likes, r.comments, r.taken_at,
                   r.caption, r.duration, c.followers, c.full_name, c.is_verified, t.status AS teardown_status, t.data AS teardown
            FROM outliers o JOIN reels r ON r.shortcode = o.shortcode LEFT JOIN creators c ON c.username = r.username
            LEFT JOIN teardowns t ON t.shortcode = o.shortcode
            WHERE o.project_id=? AND {where} ORDER BY {order}""", (project_id,)).fetchall()
    items = []
    for r in rows:
        item = {k: r[k] for k in r.keys() if k != "teardown"}
        item["cover"] = cover_url(r["shortcode"])
        if r["teardown"]:
            data = json.loads(r["teardown"])
            f = data["fields"]
            value = lambda k: (f.get(k) or {}).get("value")
            item["td"] = {k: value(k) for k in ("verbal_hook", "written_hook", "hook_pattern", "angle", "video_type", "format",
                                                 "delivery", "complexity", "cta_mechanic", "is_series", "content_type", "funnel")}
            item["td"]["review"] = sum(1 for v in f.values() if v.get("source") == "needs_review")
            item["td"]["ai"] = sum(1 for v in f.values() if v.get("source") == "ai")
            item["sponsored"] = any("Sponsored" in n for n in data.get("notes", []))
        items.append(item)
    return items


@app.patch("/api/projects/{project_id}/outliers/{shortcode}")
def update_outlier(project_id: int, shortcode: str, body: StatusPatch):
    if body.status not in ("new", "saved", "dismissed"):
        raise HTTPException(400, "Status must be new, saved or dismissed")
    with db.connect() as conn:
        conn.execute("UPDATE outliers SET status=? WHERE project_id=? AND shortcode=?", (body.status, project_id, shortcode))
    return {"ok": True}


@app.get("/api/projects/{project_id}/creators")
def list_creators(project_id: int):
    with db.connect() as conn:
        rows = conn.execute("""SELECT pc.username, pc.keywords, pc.status, c.followers, c.full_name, c.is_verified
                               FROM project_creators pc LEFT JOIN creators c ON c.username = pc.username
                               WHERE pc.project_id=?""", (project_id,)).fetchall()
        out = []
        for r in rows:
            views = [v[0] for v in conn.execute("SELECT views FROM reels WHERE username=? AND views IS NOT NULL", (r["username"],))]
            outliers = conn.execute("SELECT COUNT(*), MAX(ratio) FROM outliers WHERE project_id=? AND shortcode IN "
                                    "(SELECT shortcode FROM reels WHERE username=?)", (project_id, r["username"])).fetchone()
            out.append({"username": r["username"], "full_name": r["full_name"], "followers": r["followers"],
                        "is_verified": bool(r["is_verified"]), "status": r["status"], "keywords": json.loads(r["keywords"]),
                        "reels": len(views), "median_views": int(statistics.median(views)) if views else None,
                        "outliers": outliers[0], "best_ratio": outliers[1]})
    order = {"scanned": 0, "found": 1, "too_big": 2, "too_small": 3, "private": 4, "error": 5}
    return sorted(out, key=lambda c: (order.get(c["status"], 9), -(c["best_ratio"] or 0), -(c["followers"] or 0)))


@app.get("/api/projects/{project_id}/doubled-down")
def doubled_down(project_id: int):
    """Creators who keep posting one template that works, with example reels for each template."""
    with db.connect() as conn:
        study = set(db.project_settings(get_project(conn, project_id)).get("study_accounts") or [])
        accounts = doubledown.project_accounts(conn, project_id)
        for a in accounts:
            a["study"] = a["username"] in study
            for t in a["templates"]:
                examples = []
                for sc in t["examples"]:
                    r = conn.execute("""SELECT r.shortcode, r.url, r.views, r.caption, r.taken_at, o.status AS outlier_status,
                                               td.status AS teardown_status FROM reels r
                                        LEFT JOIN outliers o ON o.shortcode = r.shortcode AND o.project_id = ?
                                        LEFT JOIN teardowns td ON td.shortcode = r.shortcode WHERE r.shortcode = ?""",
                                     (project_id, sc)).fetchone()
                    examples.append({**dict(r), "title": doubledown.title(r["caption"]), "cover": cover_url(sc),
                                     "ratio": round(r["views"] / a["followers"], 1)})
                t["examples"] = examples
    return accounts


class TemplateIn(BaseModel):
    shortcode: str


@app.post("/api/projects/{project_id}/outliers")
def add_template_reel(project_id: int, body: TemplateIn):
    """Add a doubled-down template's example reel to the project's outliers so it can be torn down and planned from."""
    with db.connect() as conn:
        get_project(conn, project_id)
        reel = conn.execute("""SELECT r.shortcode, r.views, r.caption, c.username, c.followers FROM reels r
                               JOIN creators c ON c.username = r.username WHERE r.shortcode = ?""", (body.shortcode,)).fetchone()
        if not reel or not reel["views"] or not reel["followers"]:
            raise HTTPException(404, "Unknown reel")
        phrase = next((p for p in doubledown.phrases(reel["caption"])), None)
        conn.execute("""INSERT INTO outliers (project_id, shortcode, ratio, keyword, basis, created_at) VALUES (?,?,?,?, 'template', ?)
                        ON CONFLICT(project_id, shortcode) DO UPDATE SET status = CASE WHEN status = 'dismissed' THEN 'new' ELSE status END""",
                     (project_id, body.shortcode, round(reel["views"] / reel["followers"], 1), f"@{reel['username']} template", db.now()))
    media.download_covers({body.shortcode})
    return {"ok": True}


@app.get("/api/projects/{project_id}/patterns")
def patterns(project_id: int):
    with db.connect() as conn:
        rows = conn.execute("""SELECT t.data FROM teardowns t JOIN outliers o ON o.shortcode = t.shortcode
                               WHERE o.project_id=? AND o.status <> 'dismissed' AND t.status='done'""", (project_id,)).fetchall()
    counters = {k: Counter() for k in ("hook_pattern", "format", "video_type", "complexity", "cta_mechanic", "angle", "delivery")}
    series = 0
    for row in rows:
        fields = json.loads(row["data"])["fields"]
        for key, counter in counters.items():
            value = fields.get(key, {}).get("value")
            if value and value not in ("none", "unknown"):
                counter[value] += 1
        series += bool(fields.get("is_series", {}).get("value"))
    return {"teardowns": len(rows), "series": series, **{k: c.most_common(5) for k, c in counters.items()}}


@app.post("/api/teardowns/{shortcode}")
def start_teardown(shortcode: str, project_id: int):
    if not config.scrapecreators_key():
        raise HTTPException(400, "SCRAPECREATORS_API_KEY is not set")
    try:
        teardown.start_teardown(shortcode, project_id)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


@app.post("/api/teardowns/{shortcode}/scenes")
def break_down_scenes(shortcode: str, project_id: int):
    if not config.openrouter_key():
        raise HTTPException(400, "OPENROUTER_API_KEY is not set")
    try:
        teardown.start_scenes(shortcode, project_id)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


@app.post("/api/teardowns/{shortcode}/ai")
def rerun_ai(shortcode: str, project_id: int):
    if not config.openrouter_key():
        raise HTTPException(400, "OPENROUTER_API_KEY is not set")
    try:
        teardown.start_ai(shortcode, project_id)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


@app.get("/api/teardowns/{shortcode}")
def read_teardown(shortcode: str):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM teardowns WHERE shortcode=?", (shortcode,)).fetchone()
    if not row:
        return {"status": "none"}
    return {"status": row["status"], "error": row["error"], "updated_at": row["updated_at"],
            "data": json.loads(row["data"]) if row["data"] else None}


@app.put("/api/teardowns/{shortcode}")
def edit_teardown(shortcode: str, body: FieldsPatch):
    with db.connect() as conn:
        row = conn.execute("SELECT data FROM teardowns WHERE shortcode=? AND status='done'", (shortcode,)).fetchone()
        if not row:
            raise HTTPException(404, "No finished teardown to edit")
        data = json.loads(row["data"])
        for key, value in body.fields.items():
            if key not in data["fields"] or key == "stats":
                raise HTTPException(400, f"Unknown or read-only field: {key}")
            data["fields"][key] = {"value": value, "source": "human", "note": None}
        conn.execute("UPDATE teardowns SET data=?, updated_at=? WHERE shortcode=?", (json.dumps(data), db.now(), shortcode))
    return data


@app.post("/api/projects/{project_id}/plans")
def create_plan(project_id: int, body: PlanIn):
    if not config.openrouter_key():
        raise HTTPException(400, "OPENROUTER_API_KEY is not set")
    with db.connect() as conn:
        settings = db.project_settings(get_project(conn, project_id))
    try:
        plan_id = planner.start(project_id, body.about[:4000], body.followers, body.start_date,
                                max(1, min(7, body.posts)), settings["ai_model"])
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"plan_id": plan_id}


@app.get("/api/projects/{project_id}/plans")
def list_plans(project_id: int):
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM plans WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()
    plans = []
    for r in rows:
        data = json.loads(r["data"]) if r["data"] else None
        plans.append({"id": r["id"], "status": r["status"], "error": r["error"], "created_at": r["created_at"],
                      "input": json.loads(r["input"] or "{}"), "data": data,
                      "export": brief.plan_exports(project_id, data) if r["status"] == "done" and data else None})
    return plans


@app.get("/api/plans/{plan_id}/export.md")
def export_plan(plan_id: int, post: int | None = None):
    """The week (or one post) as a Markdown brief: the content idea and the script."""
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
    if not row or row["status"] != "done":
        raise HTTPException(404, "No finished plan with that id")
    exports = brief.plan_exports(row["project_id"], json.loads(row["data"]))
    item = exports["week"] if post is None else exports["posts"].get(post)
    if not item:
        raise HTTPException(404, f"Plan {plan_id} has no post {post}")
    return Response(item["markdown"], media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{item["filename"]}"'})


@app.delete("/api/plans/{plan_id}")
def delete_plan(plan_id: int):
    with db.connect() as conn:
        conn.execute("DELETE FROM plans WHERE id=?", (plan_id,))
    return {"ok": True}


@app.get("/api/backup")
def download_backup():
    """The database and media as one .tar.gz, to move your research to another machine."""
    folder, archive = backup.make_backup()
    return FileResponse(archive, media_type="application/gzip", filename=archive.name,
                        background=BackgroundTask(shutil.rmtree, folder, ignore_errors=True))


@app.post("/api/restore")
async def restore_backup(request: Request, upload: str, part: int = 0, parts: int = 1):
    """Replace all data with a backup, sent as raw bytes in one or more parts (in order) so no proxy limit gets in the way."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,40}", upload) or not 0 <= part < parts <= 10000:
        raise HTTPException(400, "Bad upload id or part number")
    staging = DATA / f"_upload_{upload}.tar.gz"
    with open(staging, "wb" if part == 0 else "ab") as f:
        async for chunk in request.stream():
            f.write(chunk)
    if part < parts - 1:
        return {"received": part + 1, "of": parts}
    try:
        counts = backup.restore(staging)
    except (RuntimeError, OSError, ValueError) as e:
        raise HTTPException(409 if "progress" in str(e) or "being generated" in str(e) else 400, str(e))
    finally:
        staging.unlink(missing_ok=True)
    db.log(None, "success", f"Restored a backup: {counts['projects']} projects, {counts['outliers']} outliers, "
                            f"{counts['teardowns']} teardowns, {counts['plans']} plans")
    return {"restored": counts}


@app.get("/api/projects/{project_id}/rates")
def rates(project_id: int):
    return planner.base_rates(project_id)


@app.get("/api/events")
def events(limit: int = 50):
    with db.connect() as conn:
        rows = conn.execute("""SELECT e.*, p.name AS project FROM events e LEFT JOIN projects p ON p.id = e.project_id
                               ORDER BY e.id DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/projects/{project_id}/export")
def export(project_id: int):
    """Saved outliers with their teardowns, in the shape the templatizing step (playbook Phase 4) reads."""
    with db.connect() as conn:
        project = project_dict(conn, get_project(conn, project_id))
        rows = conn.execute("""SELECT o.shortcode, o.ratio, o.keyword, r.url, r.username, r.views, r.taken_at, c.followers, t.data
                               FROM outliers o JOIN reels r ON r.shortcode = o.shortcode
                               LEFT JOIN creators c ON c.username = r.username LEFT JOIN teardowns t ON t.shortcode = o.shortcode
                               WHERE o.project_id=? AND o.status='saved' ORDER BY o.ratio DESC""", (project_id,)).fetchall()
    outliers = []
    for i, r in enumerate(rows, 1):
        td = json.loads(r["data"]) if r["data"] else None
        outliers.append({
            "id": f"O{i:03d}", "url": r["url"], "creator_handle": "@" + r["username"], "views": r["views"],
            "creator_followers": r["followers"], "outlier_ratio": r["ratio"], "posted_date": (r["taken_at"] or "")[:10],
            "found_via_keyword": r["keyword"],
            "teardown": {k: v["value"] for k, v in td["fields"].items()} if td else None,
            "transcript": td["transcript"]["text"] if td and td.get("transcript") else None,
        })
    return {"project": {k: project[k] for k in ("name", "niche", "keywords")}, "exported_at": db.now(), "outliers": outliers}
