"""How far a post reached. Reels and TikTok slideshows show their views; Instagram hides a carousel's views, so its views are
estimated from its likes at the niche's own likes-per-view rate (and every ratio built on that is marked as estimated)."""

import statistics

# Median likes per view of 10,448 reels across six niches: the estimate until a project has 100 reels of its own.
LIKES_PER_VIEW = 0.0192
KINDS = (("reel", "reels"), ("carousel", "carousels"), ("slideshow", "slideshows"))  # (kind, the setting that turns it on)


def enabled_kinds(settings):
    return [kind for kind, key in KINDS if settings.get(key)]


def likes_per_view(conn, project_id):
    """The niche's own likes-per-view rate, from its reels that show both counts."""
    rows = conn.execute("""SELECT r.likes * 1.0 / r.views FROM reels r
                           JOIN project_creators pc ON pc.username = r.username AND pc.project_id = ?
                           WHERE r.kind = 'reel' AND r.views > 0 AND r.likes IS NOT NULL""", (project_id,)).fetchall()
    return round(statistics.median(x[0] for x in rows), 4) if len(rows) >= 100 else LIKES_PER_VIEW


def views(post, lpv=LIKES_PER_VIEW):
    """Views as shown, or for an Instagram carousel its likes at the likes-per-view rate. post needs kind, views, likes."""
    if post["kind"] == "carousel":
        return round(post["likes"] / lpv) if post["likes"] and lpv else None
    return post["views"]
