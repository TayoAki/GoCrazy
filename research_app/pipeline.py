"""Research run: keyword search -> creators -> their posts -> outliers (views / followers >= min_ratio).

Instagram reels and carousels come from the same creators (found by reel and account search); TikTok slideshows come
from TikTok's Top search and then each slideshow creator's feed. Instagram shows no views for carousels, so a carousel's
views are estimated from its likes at the niche's own likes-per-view rate, and its outlier is marked as estimated.
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from . import db, doubledown, media, reach
from .config import scrapecreators_key
from .scrapecreators import (ScrapeCreators, ScrapeError, carousel_from_post_item, is_slideshow, reel_from_post_item,
                             reel_from_user_item, slideshow_from_tiktok_item)

_stop_flags = {}


class Stopped(Exception):
    pass


class BudgetReached(Exception):
    pass


def start_run(project_id):
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM runs WHERE project_id=? AND status='running'", (project_id,)).fetchone():
            raise RuntimeError("A research run is already in progress for this project.")
        cur = conn.execute(
            "INSERT INTO runs (project_id, status, phase, progress, message, started_at) VALUES (?, 'running', 'search', 0, 'Starting', ?)",
            (project_id, db.now()))
        run_id = cur.lastrowid
    stop = threading.Event()
    _stop_flags[run_id] = stop
    threading.Thread(target=_run, args=(run_id, project_id, stop), daemon=True).start()
    return run_id


def stop_run(run_id):
    if run_id in _stop_flags:
        _stop_flags[run_id].set()


def age_days(iso):
    if not iso:
        return None
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - then).days


def _update(run_id, **fields):
    cols = ", ".join(f"{k}=?" for k in fields)
    with db.connect() as conn:
        conn.execute(f"UPDATE runs SET {cols} WHERE id=?", (*fields.values(), run_id))


def upsert_reel(conn, reel, username):
    """Save a reel, carousel or slideshow (the reels table holds every kind of post)."""
    row = {"platform": "instagram", "kind": "reel", "saves": None, "shares": None, "slides": None, "music": None,
           **reel, "username": username, "fetched_at": db.now()}
    row["slides"] = json.dumps(row["slides"]) if row["slides"] else None
    row["music"] = json.dumps(row["music"]) if row["music"] else None
    conn.execute("""
        INSERT INTO reels (shortcode, username, url, views, likes, comments, taken_at, caption, thumb_url, duration, fetched_at,
                           platform, kind, saves, shares, slides, music)
        VALUES (:shortcode, :username, :url, :views, :likes, :comments, :taken_at, :caption, :thumb_url, :duration, :fetched_at,
                :platform, :kind, :saves, :shares, :slides, :music)
        ON CONFLICT(shortcode) DO UPDATE SET
            views=COALESCE(excluded.views, reels.views), likes=COALESCE(excluded.likes, reels.likes),
            comments=COALESCE(excluded.comments, reels.comments), taken_at=COALESCE(excluded.taken_at, reels.taken_at),
            caption=COALESCE(NULLIF(excluded.caption, ''), reels.caption), thumb_url=COALESCE(excluded.thumb_url, reels.thumb_url),
            duration=COALESCE(excluded.duration, reels.duration), fetched_at=excluded.fetched_at,
            saves=COALESCE(excluded.saves, reels.saves), shares=COALESCE(excluded.shares, reels.shares),
            slides=COALESCE(excluded.slides, reels.slides), music=COALESCE(excluded.music, reels.music)""", row)


def save_creator(conn, username, full_name, followers, is_verified):
    conn.execute("""INSERT INTO creators (username, full_name, followers, is_verified, profile_fetched_at) VALUES (?,?,?,?,?)
                    ON CONFLICT(username) DO UPDATE SET full_name=COALESCE(excluded.full_name, creators.full_name),
                    followers=excluded.followers, is_verified=excluded.is_verified, profile_fetched_at=excluded.profile_fetched_at""",
                 (username, full_name, followers, int(bool(is_verified)), db.now()))


def save_project_creators(conn, project_id, found):
    for username, entry in found.items():
        row = conn.execute("SELECT keywords FROM project_creators WHERE project_id=? AND username=?",
                           (project_id, username)).fetchone()
        kws = sorted(set(json.loads(row["keywords"])) | entry["keywords"]) if row else sorted(entry["keywords"])
        conn.execute("""INSERT INTO project_creators (project_id, username, keywords, status) VALUES (?,?,?,'found')
                        ON CONFLICT(project_id, username) DO UPDATE SET keywords=excluded.keywords""",
                     (project_id, username, json.dumps(kws)))


def mark_outliers(conn, project_id, username, followers, settings, keyword, lpv):
    """Every post of the creator's that passes the outlier test, for the kinds the project researches. Returns the new count."""
    kinds = reach.enabled_kinds(settings)
    if not kinds:
        return 0
    new = 0
    rows = conn.execute(f"SELECT shortcode, kind, views, likes, taken_at FROM reels WHERE username=? AND kind IN "
                        f"({','.join('?' * len(kinds))})", (username, *kinds)).fetchall()
    for post in rows:
        views = reach.views(post, lpv)
        if not views:
            continue
        age = age_days(post["taken_at"])
        ratio = round(views / followers, 1)
        if ratio >= settings["min_ratio"] and (age is None or age <= settings["max_age_days"]):
            existed = conn.execute("SELECT 1 FROM outliers WHERE project_id=? AND shortcode=?",
                                   (project_id, post["shortcode"])).fetchone()
            conn.execute("""INSERT INTO outliers (project_id, shortcode, ratio, keyword, measure, created_at) VALUES (?,?,?,?,?,?)
                            ON CONFLICT(project_id, shortcode) DO UPDATE SET ratio=excluded.ratio, measure=excluded.measure""",
                         (project_id, post["shortcode"], ratio, keyword, "likes" if post["kind"] == "carousel" else "views", db.now()))
            new += not existed
    return new


def _run(run_id, project_id, stop):
    client = ScrapeCreators(scrapecreators_key())
    with db.connect() as conn:
        project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    settings = db.project_settings(project)
    keywords = json.loads(project["keywords"])
    stats = {"searches": 0, "creators_found": 0, "creators_scanned": 0, "reels_checked": 0, "new_outliers": 0}

    def check():
        if stop.is_set():
            raise Stopped()
        if client.credits_used >= settings["credit_budget"]:
            raise BudgetReached()

    status, message = "done", None
    instagram = settings["reels"] or settings["carousels"]
    # Share of the progress bar each platform gets.
    split = (0.6 if settings["slideshows"] else 0.9) if instagram else 0.0
    try:
        if instagram:
            found = _search_phase(run_id, project_id, client, keywords, settings, stats, check, split / 0.9)
            with db.connect() as conn:
                lpv = reach.likes_per_view(conn, project_id)
            _scan_phase(run_id, project_id, client, found, settings, stats, check, stop, split / 0.9, lpv)
        if settings["slideshows"]:
            _tiktok_phase(run_id, project_id, client, keywords, settings, stats, check, stop, split, 0.9)
    except Stopped:
        status, message = "stopped", "Stopped by you"
    except BudgetReached:
        message = f"Stopped at the credit budget ({settings['credit_budget']})"
    except ScrapeError as e:
        status, message = "failed", ("Out of ScrapeCreators credits" if e.out_of_credits else str(e))
    except Exception as e:  # keep the run row truthful instead of leaving it "running"
        status, message = "failed", f"{type(e).__name__}: {e}"

    _update(run_id, phase="covers", progress=0.95, message="Downloading covers", credits_used=client.credits_used)
    media.download_missing_covers(project_id)
    with db.connect() as conn:
        media.download_covers({sc for a in doubledown.project_accounts(conn, project_id) for t in a["templates"] for sc in t["examples"]})

    with db.connect() as conn:
        stats["outliers_total"] = conn.execute("SELECT COUNT(*) FROM outliers WHERE project_id=?", (project_id,)).fetchone()[0]
    summary = (f"{stats['new_outliers']} new outliers from {stats['reels_checked']} reels across "
               f"{stats['creators_scanned']} creators · {client.credits_used} credits")
    _update(run_id, status=status, phase="finished", progress=1, credits_used=client.credits_used,
            message=message or summary, stats=json.dumps(stats), finished_at=db.now())
    level = {"done": "success", "stopped": "warning", "failed": "error"}[status]
    db.log(project_id, level, f"Research run #{run_id}: {message + ' · ' if message else ''}{summary}")
    _stop_flags.pop(run_id, None)


def _search_phase(run_id, project_id, client, keywords, settings, stats, check, scale=1.0):
    found = {h: {"keywords": set(), "full_name": None, "is_verified": None, "study": True}
             for h in settings.get("study_accounts") or []}
    jobs = [(kw, page) for kw in keywords for page in range(1, settings["search_pages"] + 1)]
    exhausted = set()
    for i, (kw, page) in enumerate(jobs):
        if kw in exhausted:
            continue
        check()
        _update(run_id, phase="search", progress=scale * 0.2 * i / max(len(jobs), 1),
                message=f'Searching "{kw}" (page {page})', credits_used=client.credits_used)
        try:
            reels = client.search_reels(kw, page, settings["date_posted"])
        except ScrapeError as e:
            if e.out_of_credits:
                raise
            db.log(project_id, "warning", f'Search failed for "{kw}" page {page}: {e}')
            continue
        stats["searches"] += 1
        if len(reels) < 10:
            exhausted.add(kw)
        with db.connect() as conn:
            for r in reels:
                owner = r.get("owner") or {}
                username = owner.get("username")
                if not username or r.get("is_paid_partnership") or r.get("is_ad"):
                    continue
                entry = found.setdefault(username, {"keywords": set(), "full_name": owner.get("full_name"),
                                                    "is_verified": owner.get("is_verified")})
                entry["keywords"].add(kw)
                caption = r.get("caption")
                upsert_reel(conn, {
                    "shortcode": r.get("shortcode"), "url": r.get("url"), "views": r.get("video_view_count"),
                    "likes": r.get("like_count"), "comments": r.get("comment_count"), "taken_at": r.get("taken_at"),
                    "caption": caption if isinstance(caption, str) else "", "duration": r.get("video_duration"),
                    "thumb_url": r.get("thumbnail_src") or r.get("display_url"),
                }, username)
    if settings["account_search"]:
        for i, kw in enumerate(keywords):
            check()
            _update(run_id, phase="search", progress=scale * (0.2 + 0.1 * i / max(len(keywords), 1)),
                    message=f'Searching accounts for "{kw}"', credits_used=client.credits_used)
            try:
                profiles = client.search_profiles(kw)
            except ScrapeError as e:
                if e.out_of_credits:
                    raise
                db.log(project_id, "warning", f'Account search failed for "{kw}": {e}')
                continue
            stats["searches"] += 1
            with db.connect() as conn:
                for prof in profiles:
                    username = prof.get("username")
                    if not username or prof.get("is_private"):
                        continue
                    found.setdefault(username, {"keywords": set(), "full_name": prof.get("full_name"),
                                                "is_verified": prof.get("is_verified")})["keywords"].add(kw)
                    if prof.get("follower_count") is not None:
                        # Cache the count so the scan phase skips a paid profile lookup.
                        save_creator(conn, username, prof.get("full_name"), prof["follower_count"], prof.get("is_verified"))
    with db.connect() as conn:
        save_project_creators(conn, project_id, found)
    stats["creators_found"] = len(found)
    return found


def _scan_phase(run_id, project_id, client, found, settings, stats, check, stop, scale=1.0, lpv=reach.LIKES_PER_VIEW):
    # Creators surfaced by more keywords are more central to the niche, so scan them first.
    # Accounts you named go first and don't count against max_creators.
    study = [kv for kv in found.items() if kv[1].get("study")]
    others = [kv for kv in found.items() if not kv[1].get("study")]
    ranked = study + sorted(others, key=lambda kv: (-len(kv[1]["keywords"]), kv[0]))[: settings["max_creators"]]
    if not ranked:
        return
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_scan_creator, client, project_id, username, info, settings, check, lpv)
                   for username, info in ranked]
        try:
            for done, fut in enumerate(as_completed(futures), 1):
                result = fut.result()
                with lock:
                    stats["creators_scanned"] += result["scanned"]
                    stats["reels_checked"] += result["reels"]
                    stats["new_outliers"] += result["new_outliers"]
                _update(run_id, phase="creators", progress=scale * (0.3 + 0.6 * done / len(futures)),
                        message=f"Scanned {done}/{len(futures)} creators · {stats['new_outliers']} new outliers",
                        credits_used=client.credits_used)
        except (Stopped, BudgetReached, ScrapeError):
            stop.set()  # tells the other workers to stop at their next check
            pool.shutdown(cancel_futures=True)
            raise


def _scan_creator(client, project_id, username, info, settings, check, lpv=reach.LIKES_PER_VIEW):
    result = {"scanned": 0, "reels": 0, "new_outliers": 0}

    def set_status(status):
        with db.connect() as conn:
            conn.execute("UPDATE project_creators SET status=? WHERE project_id=? AND username=?", (status, project_id, username))

    with db.connect() as conn:
        row = conn.execute("SELECT * FROM creators WHERE username=?", (username,)).fetchone()
    fetched_age = age_days(row["profile_fetched_at"]) if row else None
    followers = row["followers"] if fetched_age is not None and fetched_age < 30 else None
    if followers is None:
        check()
        try:
            user = client.profile(username)
        except ScrapeError as e:
            if e.out_of_credits:
                raise
            set_status("error")
            return result
        if user.get("is_private"):
            set_status("private")
            return result
        followers = (user.get("edge_followed_by") or {}).get("count")
        with db.connect() as conn:
            save_creator(conn, username, user.get("full_name") or info.get("full_name"), followers, user.get("is_verified"))
    if not followers:
        set_status("error")
        return result
    # Inside the follower range a creator's reels can be outliers. Bigger creators (up to double_down_max_followers) are
    # still scanned, but only so the Doubled down tab can spot their templates. An account you named is always scanned.
    in_range = info.get("study") or settings["min_followers"] <= followers <= settings["max_followers"]
    if not info.get("study"):
        if followers < settings["min_followers"]:
            set_status("too_small")
            return result
        if followers > settings.get("double_down_max_followers", settings["max_followers"]):
            set_status("too_big")
            return result

    deep = lambda pages: max(pages, 8) if info.get("study") else pages
    if settings["reels"]:
        result["reels"] += _pages(check, lambda max_id: client.user_reels(username, max_id), deep(settings["reel_pages"]),
                                  lambda item: reel_from_user_item(item), username)
    if settings["carousels"]:
        def from_feed(item):  # the posts feed mixes reels, carousels and photos; photos are left out
            if item.get("media_type") == 8 and not item.get("is_paid_partnership"):
                post = carousel_from_post_item(item)
                return {**post, "likes": None} if item.get("like_and_view_counts_disabled") else post
            return reel_from_post_item(item) if item.get("media_type") == 2 and item.get("play_count") else None
        result["reels"] += _pages(check, lambda max_id: client.user_posts(username, max_id), deep(settings["post_pages"]),
                                  from_feed, username)

    keyword = f"@{username}" if info.get("study") else sorted(info["keywords"])[0] if info.get("keywords") else None
    with db.connect() as conn:
        conn.execute("UPDATE creators SET reels_fetched_at=? WHERE username=?", (db.now(), username))
        if in_range:
            result["new_outliers"] += mark_outliers(conn, project_id, username, followers, settings, keyword, lpv)
    set_status("scanned")
    result["scanned"] = 1
    return result


def _pages(check, fetch, pages, normalize, username):
    """Fetch up to `pages` pages of a creator's feed and save each post `normalize` keeps. Returns how many were saved."""
    saved, cursor = 0, None
    for _ in range(pages):
        check()
        try:
            items, cursor = fetch(cursor)
        except ScrapeError as e:
            if e.out_of_credits:
                raise
            break
        with db.connect() as conn:
            for item in items:
                post = normalize(item)
                if post and post["shortcode"]:
                    upsert_reel(conn, post, username)
                    saved += 1
        if not items or not cursor:
            break
    return saved


# ---------- TikTok slideshows ----------

def _tiktok_phase(run_id, project_id, client, keywords, settings, stats, check, stop, start, end):
    """Top search per keyword (the only TikTok search that returns slideshows), then each slideshow creator's feed."""
    publish_time = "last-6-months" if settings["max_age_days"] <= 183 else None
    found, cursors = {}, {}
    jobs = [(kw, page) for page in range(settings["tiktok_search_pages"]) for kw in keywords]
    for i, (kw, page) in enumerate(jobs):
        if page and not cursors.get(kw):
            continue  # that keyword has no more results
        check()
        _update(run_id, phase="tiktok", progress=start + (end - start) * 0.3 * i / max(len(jobs), 1),
                message=f'Searching TikTok slideshows for "{kw}" (page {page + 1})', credits_used=client.credits_used)
        try:
            items, cursors[kw] = client.tiktok_top(kw, cursors.get(kw), publish_time)
        except ScrapeError as e:
            if e.out_of_credits:
                raise
            db.log(project_id, "warning", f'TikTok search failed for "{kw}" page {page + 1}: {e}')
            cursors[kw] = None
            continue
        stats["searches"] += 1
        with db.connect() as conn:
            for item in items:
                _save_tiktok_item(conn, item, found, kw)
    with db.connect() as conn:
        save_project_creators(conn, project_id, found)
    stats["creators_found"] += len(found)
    ranked = sorted(found.items(), key=lambda kv: (-len(kv[1]["keywords"]), kv[0]))
    with db.connect() as conn:
        # Search results already carry follower counts, so the slideshows found there are tested even for creators
        # whose feeds aren't scanned.
        for username, info in ranked[settings["max_creators"]:]:
            _tiktok_outliers(conn, project_id, username, info, settings)
    ranked = ranked[: settings["max_creators"]]
    if not ranked:
        return
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_scan_tiktok_creator, client, project_id, username, info, settings, check)
                   for username, info in ranked]
        try:
            for done, fut in enumerate(as_completed(futures), 1):
                result = fut.result()
                with lock:
                    stats["creators_scanned"] += result["scanned"]
                    stats["reels_checked"] += result["reels"]
                    stats["new_outliers"] += result["new_outliers"]
                _update(run_id, phase="tiktok", progress=start + (end - start) * (0.3 + 0.7 * done / len(futures)),
                        message=f"Scanned {done}/{len(futures)} TikTok creators · {stats['new_outliers']} new outliers",
                        credits_used=client.credits_used)
        except (Stopped, BudgetReached, ScrapeError):
            stop.set()
            pool.shutdown(cancel_futures=True)
            raise


def _save_tiktok_item(conn, item, found=None, keyword=None):
    """Save one TikTok post if it is a slideshow, with its creator's follower count. Returns the "tt:" username or None."""
    author = item.get("author") or {}
    if not is_slideshow(item) or not author.get("unique_id") or item.get("is_ad") or item.get("is_paid_partnership"):
        return None
    username = "tt:" + author["unique_id"]
    if author.get("follower_count") is not None:
        save_creator(conn, username, author.get("nickname"), author["follower_count"], author.get("verification_type") == 1)
    upsert_reel(conn, slideshow_from_tiktok_item(item), username)
    if found is not None:
        found.setdefault(username, {"keywords": set()})["keywords"].add(keyword)
    return username


def _tiktok_outliers(conn, project_id, username, info, settings, scanned=False):
    """Set the creator's status from their follower count and mark their outlier slideshows. Returns (status, new outliers)."""
    row = conn.execute("SELECT followers FROM creators WHERE username=?", (username,)).fetchone()
    followers = row["followers"] if row else None
    status = ("error" if not followers else "too_small" if followers < settings["min_followers"] else
              "too_big" if followers > settings.get("double_down_max_followers", settings["max_followers"]) else
              "scanned" if scanned else "found")
    conn.execute("UPDATE project_creators SET status=? WHERE project_id=? AND username=?", (status, project_id, username))
    new = 0
    if followers and settings["min_followers"] <= followers <= settings["max_followers"]:
        keyword = sorted(info["keywords"])[0] if info.get("keywords") else None
        new = mark_outliers(conn, project_id, username, followers, settings, keyword, reach.LIKES_PER_VIEW)
    return status, new


def _scan_tiktok_creator(client, project_id, username, info, settings, check):
    result = {"scanned": 0, "reels": 0, "new_outliers": 0}
    with db.connect() as conn:
        row = conn.execute("SELECT followers FROM creators WHERE username=?", (username,)).fetchone()
    followers = row["followers"] if row else None
    if followers and not settings["min_followers"] <= followers <= settings.get("double_down_max_followers", settings["max_followers"]):
        with db.connect() as conn:  # out of range: its feed isn't worth the credits
            _tiktok_outliers(conn, project_id, username, info, settings)
        return result
    cursor = None
    for _ in range(settings["tiktok_pages"]):
        check()
        try:
            items, cursor = client.tiktok_videos(username[3:], cursor)
        except ScrapeError as e:
            if e.out_of_credits:
                raise
            break
        with db.connect() as conn:
            result["reels"] += sum(bool(_save_tiktok_item(conn, item)) for item in items)
        if not items or not cursor:
            break
    with db.connect() as conn:
        conn.execute("UPDATE creators SET reels_fetched_at=? WHERE username=?", (db.now(), username))
        status, result["new_outliers"] = _tiktok_outliers(conn, project_id, username, info, settings, scanned=True)
    result["scanned"] = int(status == "scanned")
    return result
