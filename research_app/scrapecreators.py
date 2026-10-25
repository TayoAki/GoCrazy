"""Thin ScrapeCreators client. Response shapes were checked against live calls, not just the docs."""

import re
import threading
import time
from datetime import datetime, timezone

import requests

BASE = "https://api.scrapecreators.com"


class ScrapeError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(f"HTTP {status}: {message}")

    @property
    def out_of_credits(self):
        return self.status == 402


class ScrapeCreators:
    def __init__(self, api_key, max_retries=4):
        self.session = requests.Session()
        self.session.headers["x-api-key"] = api_key
        self.max_retries = max_retries
        self.credits_used = 0
        self.credits_remaining = None
        self._lock = threading.Lock()

    def get(self, path, **params):
        params = {k: v for k, v in params.items() if v is not None}
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.get(BASE + path, params=params, timeout=90)
            except requests.RequestException as e:
                if attempt == self.max_retries:
                    raise ScrapeError(0, str(e)) from e
                time.sleep(2 ** attempt)
                continue
            try:
                body = resp.json()
            except ValueError:
                body = {"message": resp.text[:200]}
            if (resp.status_code == 429 or resp.status_code >= 500) and attempt < self.max_retries:
                time.sleep(2 ** attempt)
                continue
            with self._lock:
                self.credits_used += body.get("credits_charged") or 0
                if body.get("credits_remaining") is not None:
                    self.credits_remaining = body["credits_remaining"]
            if resp.status_code >= 400 or body.get("success") is False:
                raise ScrapeError(resp.status_code, body.get("message") or body.get("error") or "request failed")
            return body

    def balance(self):
        body = self.get("/v1/account/credit-balance")
        # The live API answers {"creditCount": N}; the docs show credits_remaining.
        return body.get("creditCount", body.get("credits_remaining"))

    def search_reels(self, query, page=1, date_posted="last-year"):
        return self.get("/v2/instagram/reels/search", query=query, page=page, date_posted=date_posted).get("reels") or []

    def search_profiles(self, query):
        """Account search ("Accounts tab"). Live results carry follower_count, so no profile lookup is needed."""
        return self.get("/v1/instagram/search/profiles", query=query).get("profiles") or []

    def user_reels(self, handle, max_id=None):
        body = self.get("/v1/instagram/user/reels", handle=handle, max_id=max_id, trim="true")
        return body.get("items") or [], body.get("max_id")

    def profile(self, handle):
        body = self.get("/v1/instagram/profile", handle=handle, trim="true", cache_max_age="30d")
        return (body.get("data") or {}).get("user") or {}

    def post(self, url, fresh=False):
        """Post details. Cached lookups are free but can hold an expired video link; fresh=True skips the cache."""
        body = self.get("/v1/instagram/post", url=url, trim="true", **({} if fresh else {"cache_max_age": "30d"}))
        # trim=true puts the media at the top level; the untrimmed shape nests it under data.
        return body.get("xdt_shortcode_media") or (body.get("data") or {}).get("xdt_shortcode_media") or {}

    def user_posts(self, handle, max_id=None):
        """Every kind of post (reels, carousels, photos), 12 a page. The only place Instagram carousels show up."""
        body = self.get("/v2/instagram/user/posts", handle=handle, next_max_id=max_id)
        return body.get("items") or [], body.get("next_max_id") if body.get("more_available") is not False else None

    def tiktok_top(self, query, cursor=None, publish_time=None):
        """TikTok's "Top" search: the only search that returns photo slideshows (keyword search returns videos only)."""
        body = self.get("/v1/tiktok/search/top", query=query, cursor=cursor, publish_time=publish_time)
        return body.get("items") or [], body.get("cursor")

    def tiktok_videos(self, handle, cursor=None):
        body = self.get("/v3/tiktok/profile/videos", handle=handle, max_cursor=cursor)
        return body.get("aweme_list") or [], body.get("max_cursor") if body.get("has_more") else None

    def tiktok_post(self, url):
        body = self.get("/v2/tiktok/video", url=url)
        return body.get("aweme_detail") or body.get("data") or {}

    def transcript(self, url, allow_long=False):
        body = self.get("/v2/instagram/media/transcript", url=url, cache_max_age="30d",
                        allow_long_transcription="true" if allow_long else None)
        return (body.get("transcripts") or [None])[0]


def reel_from_user_item(item):
    """Normalize one item from /v1/instagram/user/reels."""
    caption = item.get("caption")
    if isinstance(caption, dict):
        caption = caption.get("text")
    thumb = item.get("display_uri")
    if not thumb:
        candidates = (item.get("image_versions2") or {}).get("candidates") or []
        thumb = candidates[0].get("url") if candidates else None
    return {
        "shortcode": item.get("code"),
        "url": item.get("url") or f"https://www.instagram.com/reel/{item.get('code')}/",
        "views": item.get("play_count") or item.get("ig_play_count"),
        "likes": item.get("like_count"),
        "comments": item.get("comment_count"),
        "taken_at": item.get("created_at"),
        "caption": caption or "",
        "thumb_url": thumb,
        "duration": item.get("video_duration"),
    }


def _caption_text(caption):
    return (caption.get("text") if isinstance(caption, dict) else caption) or ""


def carousel_from_post_item(item):
    """Normalize one carousel (media_type 8) from /v2/instagram/user/posts. Instagram shows no views for carousels."""
    slides = []
    for s in item.get("carousel_media") or []:
        candidates = (s.get("image_versions2") or {}).get("candidates") or []
        best = max(candidates, key=lambda c: (c.get("width") or 0) * (c.get("height") or 0), default=None)
        url = (best or {}).get("url") or s.get("display_uri")
        if url:
            slides.append({"url": url, "video": s.get("media_type") == 2})
    music = item.get("music_metadata") or {}
    song = (music.get("music_info") or {}).get("music_asset_info") or {}
    return {
        "shortcode": item.get("code"), "url": item.get("url") or f"https://www.instagram.com/p/{item.get('code')}/",
        "views": None, "likes": item.get("like_count"), "comments": item.get("comment_count"), "taken_at": item.get("created_at"),
        "caption": _caption_text(item.get("caption")), "thumb_url": slides[0]["url"] if slides else item.get("display_uri"),
        "duration": None, "platform": "instagram", "kind": "carousel", "saves": None, "shares": None, "slides": slides,
        "music": {"title": song.get("title"), "artist": song.get("display_artist")} if song.get("title") else None,
    }


def reel_from_post_item(item):
    """A reel from the posts feed (media_type 2 with a play count), so the carousel scan doesn't waste the reels it sees."""
    return {**reel_from_user_item(item), "url": f"https://www.instagram.com/reel/{item.get('code')}/"}


def _readable(urls):
    """The first link in a format Pillow can open: TikTok often lists a HEIC copy first and a JPEG or WebP one after it."""
    return next((u for u in urls if not re.search(r"\.heic(\?|$)", u)), None)


def _tiktok_images(item):
    """Slide links from either shape: search results carry a plain list, profile feeds carry image_post_info."""
    if item.get("images"):
        return [{"url": u, "video": False} for u in item["images"] if isinstance(u, str)]
    out = []
    for img in (item.get("image_post_info") or {}).get("images") or []:
        url = _readable((img.get("display_image") or {}).get("url_list") or []) or \
            _readable((img.get("thumbnail") or {}).get("url_list") or [])
        if url:
            out.append({"url": url, "video": False})
    return out


def is_slideshow(item):
    return item.get("content_type") == "multi_photo" or bool((item.get("image_post_info") or {}).get("images"))


def slideshow_from_tiktok_item(item):
    """Normalize a TikTok photo slideshow from Top search or a profile feed. Its username is stored as "tt:<handle>"."""
    st = item.get("statistics") or {}
    author = item.get("author") or {}
    aweme_id = str(item.get("aweme_id") or item.get("id"))
    created = item.get("create_time_utc") or item.get("create_time")
    if isinstance(created, (int, float)):
        created = datetime.fromtimestamp(created, timezone.utc).isoformat(timespec="seconds")
    slides = _tiktok_images(item)
    music = item.get("music") or {}
    return {
        "shortcode": aweme_id, "url": f"https://www.tiktok.com/@{author.get('unique_id')}/photo/{aweme_id}",
        "views": st.get("play_count"), "likes": st.get("digg_count"), "comments": st.get("comment_count"),
        "taken_at": created, "caption": item.get("desc") or "", "thumb_url": slides[0]["url"] if slides else None,
        "duration": None, "platform": "tiktok", "kind": "slideshow", "saves": st.get("collect_count"),
        "shares": st.get("share_count"), "slides": slides,
        "music": {"title": music.get("title"), "artist": music.get("author")} if music.get("title") else None,
    }
