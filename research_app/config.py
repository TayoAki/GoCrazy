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
    "max_creators": 30,
    "study_accounts": [],      # handles always scanned (deeper, whatever their size), e.g. an account you want to copy
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


def has_ffmpeg():
    return shutil.which("ffmpeg") is not None
