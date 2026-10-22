"""Thin ScrapeCreators client. Response shapes were checked against live calls, not just the docs."""

import threading
import time

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

    def post(self, url):
        body = self.get("/v1/instagram/post", url=url, trim="true", cache_max_age="30d")
        # trim=true puts the media at the top level; the untrimmed shape nests it under data.
        return body.get("xdt_shortcode_media") or (body.get("data") or {}).get("xdt_shortcode_media") or {}

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
