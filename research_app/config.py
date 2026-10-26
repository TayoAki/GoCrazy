import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# On Railway the data lives on the attached volume; locally in ./data.
DATA = Path(os.environ.get("DATA_DIR") or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or ROOT / "data")
MEDIA = DATA / "media"
DB_PATH = DATA / "research.db"

# Defaults for a new research project; each project can override them.
DEFAULT_SETTINGS = {
    "min_ratio": 5.0,          # views / creator followers needed to count as an outlier
    "min_followers": 1000,     # below this, ratios are noise
    "max_followers": 500000,   # "small to mid-size" creators only
    "max_age_days": 365,
    "date_posted": "last-year",
    "search_pages": 2,         # reel-search pages per keyword (~12 s and 1 credit each)
    "account_search": True,    # also run Instagram account search per keyword (1 credit, includes follower counts)
    "reel_pages": 2,           # pages of a creator's reels to scan (12 reels, 1 credit each)
    "max_creators": 30,        # per platform
    "study_accounts": [],      # handles always scanned (deeper, whatever their size), e.g. an account you want to copy
    "double_down_max_followers": 5000000,  # bigger creators are still scanned, only to spot doubled-down templates
    "reels": True,             # Instagram reels
    "carousels": False,        # Instagram carousels: read from each creator's posts feed (Instagram has no carousel search)
    "post_pages": 2,           # pages of a creator's posts feed to scan for carousels (12 posts, 1 credit each)
    "slideshows": False,       # TikTok photo slideshows: TikTok's Top search per keyword, then each creator's feed
    "tiktok_search_pages": 2,  # Top-search pages per keyword (about 30 results, 1 credit each)
    "tiktok_pages": 2,         # pages of a TikTok creator's feed to scan (1 credit each)
    "youtube_videos": False,   # YouTube long videos: video search per keyword, then each channel's latest videos
    "youtube_shorts": False,   # YouTube Shorts: each channel's latest Shorts, plus the channels behind each keyword's top Shorts
    "youtube_search_pages": 1, # pages of video search per keyword and sort (relevance and popular, ~20 videos, 1 credit each)
    "youtube_short_lookups": 4,  # per keyword: look up the channel of the top Shorts in Shorts search (1 credit each)
    "youtube_pages": 2,        # pages of a channel's long videos to scan (30 videos, 1 credit each)
    "youtube_min_ratio": 3.0,  # views / the channel's median views for that kind (subscribers predict little on YouTube)
    "youtube_max_subscribers": 2000000,  # bigger channels are left out; min_followers is the floor
    "credit_budget": 300,      # hard stop for one research run
    "allow_long_transcription": False,  # >120 s reels cost 10 credits per started minute
    "ai_annotation": True,     # run the OpenRouter vision pass at the end of every teardown
    "ai_model": "anthropic/claude-sonnet-5.5",
}


def load_env():
    """Load KEY=value lines from the repo's .env without overriding real environment variables."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        name, sep, value = line.partition("=")
        name = name.strip()
        if sep and name and not name.startswith("#") and name not in os.environ:
            os.environ[name] = value.strip().strip("\"'")


def scrapecreators_key():
    return os.environ.get("SCRAPECREATORS_API_KEY")


def openrouter_key():
    return os.environ.get("OPENROUTER_API_KEY")


def openshorts_url():
    """The OpenShorts server that renders clip plans: OPENSHORTS_API_URL, else the hosted API when OPENSHORTS_API_KEY is
    set, else a self-hosted one on this machine. Its Docker setup serves the dashboard on port 5175, which passes /api and
    /videos through to the backend (the backend's own port, 8000, is this app's default too)."""
    url = os.environ.get("OPENSHORTS_API_URL") or ("https://api.openshorts.app" if openshorts_key() else "http://localhost:5175")
    return url.rstrip("/")


def openshorts_key():
    return os.environ.get("OPENSHORTS_API_KEY")


def has_ffmpeg():
    return shutil.which("ffmpeg") is not None
