#!/usr/bin/env python3
"""Fetch every video on a YouTube channel and save its transcript using the Supadata API.

Usage:
    export SUPADATA_API_KEY=sd_...      # or put it in a .env file next to this script
    python supadata_transcripts.py https://www.youtube.com/@SomeChannel

For each video this writes, into the output directory (default: transcripts/):
    <title> [<id>].txt   readable transcript, one timestamped caption per line
    <id>.json            video metadata plus the raw transcript chunks
and an index.json summarising the whole run.

Re-running is safe: videos that already have a transcript on disk are skipped,
so no credits are spent on them again (use --force to refetch).
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

API_BASE = "https://api.supadata.ai/v1"
# The `details` value Supadata sends with a 429 once the monthly credits are gone;
# other 429s are per-second rate limits and are worth retrying.
QUOTA_EXHAUSTED = "Plan usage limit was exceeded."


class SupadataError(Exception):
    def __init__(self, status, body):
        body = body if isinstance(body, dict) else {}
        self.status = status
        self.code = body.get("error", "unknown-error")
        self.details = body.get("details", "")
        message = body.get("message", "")
        super().__init__(f"HTTP {status} {self.code}: {message} {self.details}".strip())

    @property
    def quota_exhausted(self):
        return self.details == QUOTA_EXHAUSTED


class Supadata:
    def __init__(self, api_key, max_retries=5):
        self.session = requests.Session()
        self.session.headers["x-api-key"] = api_key
        self.max_retries = max_retries

    def get(self, path, **params):
        """GET an endpoint and return its JSON body, retrying rate limits and server errors."""
        for attempt in range(self.max_retries + 1):
            resp = self.session.get(f"{API_BASE}{path}", params=params, timeout=120)
            body = _json(resp)
            retryable = resp.status_code == 429 or resp.status_code >= 500
            if retryable and attempt < self.max_retries and body.get("details") != QUOTA_EXHAUSTED:
                delay = _retry_after(resp, default=2 ** attempt)
                print(f"    {resp.status_code} from {path}, retrying in {delay:.0f}s", file=sys.stderr)
                time.sleep(delay)
                continue
            # 206 is how Supadata reports "transcript unavailable".
            if resp.status_code >= 400 or resp.status_code == 206:
                raise SupadataError(resp.status_code, body)
            return body

    def account(self):
        return self.get("/me")

    def channel_video_ids(self, channel, limit, video_type):
        ids = self.get("/youtube/channel/videos", id=channel, limit=limit, type=video_type)
        # Regular videos first, then Shorts, then live streams; drop any duplicates.
        return list(dict.fromkeys(ids["videoIds"] + ids["shortIds"] + ids["liveIds"]))

    def video(self, video_id):
        return self.get("/youtube/video", id=video_id)

    def transcript(self, url, lang=None, mode="native", poll_interval=5, timeout=900):
        """Return the transcript for a video, waiting on the async job if Supadata starts one."""
        params = {"url": url, "mode": mode, "text": "false"}
        if lang:
            params["lang"] = lang
        body = self.get("/transcript", **params)
        if "jobId" not in body:
            return body

        job_id = body["jobId"]
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(poll_interval)
            job = self.get(f"/transcript/{job_id}")
            if job["status"] == "completed":
                return job
            if job["status"] == "failed":
                raise SupadataError(200, job.get("error"))
        raise TimeoutError(f"transcript job {job_id} did not finish within {timeout}s")


def _json(resp):
    try:
        body = resp.json()
    except ValueError:
        return {"message": resp.text[:200]}
    return body if isinstance(body, dict) else {"content": body}


def _retry_after(resp, default):
    try:
        return max(float(resp.headers["Retry-After"]), 1.0)
    except (KeyError, ValueError):
        return default


def load_api_key():
    key = os.environ.get("SUPADATA_API_KEY")
    if key:
        return key
    env_file = Path(__file__).with_name(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "SUPADATA_API_KEY":
                return value.strip().strip("\"'")
    return None


def safe_filename(text, max_length=80):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", text)
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    return text[:max_length].rstrip()


def timestamp(ms):
    seconds = int(ms // 1000)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def transcript_text(record):
    meta = record.get("metadata") or {}
    transcript = record["transcript"]
    header = [
        f"Title: {meta.get('title', record['id'])}",
        f"URL: {record['url']}",
    ]
    if meta.get("uploadDate"):
        header.append(f"Uploaded: {meta['uploadDate'][:10]}")
    if meta.get("duration"):
        header.append(f"Duration: {timestamp(meta['duration'] * 1000)}")
    header.append(f"Transcript language: {transcript.get('lang', 'unknown')}")

    content = transcript["content"]
    if isinstance(content, str):
        body = content
    else:
        body = "\n".join(f"[{timestamp(c['offset'])}] {c['text'].strip()}" for c in content)
    return "\n".join(header) + "\n\n" + body + "\n"


def text_path(out_dir, record):
    title = safe_filename((record.get("metadata") or {}).get("title", ""))
    name = f"{title} [{record['id']}].txt" if title else f"{record['id']}.txt"
    return out_dir / name


def fetch_video(client, video_id, args, metadata=None):
    url = f"https://www.youtube.com/watch?v={video_id}"
    record = {"id": video_id, "url": url}

    if metadata:
        record["metadata"] = metadata
    elif not args.no_metadata:
        try:
            record["metadata"] = client.video(video_id)
        except SupadataError as e:
            if e.quota_exhausted:
                raise
            record["metadataError"] = str(e)

    try:
        t = client.transcript(url, lang=args.lang, mode=args.mode)
        record["transcript"] = {
            "lang": t.get("lang"),
            "availableLangs": t.get("availableLangs", []),
            "content": t["content"],
        }
    except SupadataError as e:
        if e.quota_exhausted:
            raise
        record["transcriptError"] = str(e)
    except TimeoutError as e:
        record["transcriptError"] = str(e)
    return record


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download transcripts for every video on a YouTube channel via Supadata."
    )
    parser.add_argument("channel", help="channel URL, @handle or channel ID")
    parser.add_argument("-o", "--out", default="transcripts", help="output directory (default: %(default)s)")
    parser.add_argument("--limit", type=int, default=500, help="max videos to fetch (default: %(default)s)")
    parser.add_argument(
        "--type", default="all", choices=["all", "video", "short", "live"],
        help="which kinds of uploads to include (default: %(default)s)",
    )
    parser.add_argument("--lang", help="preferred transcript language, e.g. en (default: first available)")
    parser.add_argument(
        "--mode", default="native", choices=["native", "auto", "generate"],
        help="native = existing captions only (1 credit each); auto/generate may fall back to AI "
             "transcription, which costs more credits (default: %(default)s)",
    )
    parser.add_argument("--no-metadata", action="store_true", help="skip the per-video metadata call (saves 1 credit per video)")
    parser.add_argument("--force", action="store_true", help="refetch videos that already have a transcript on disk")
    return parser.parse_args()


def main():
    args = parse_args()
    api_key = load_api_key()
    if not api_key:
        sys.exit("Set SUPADATA_API_KEY in the environment or in a .env file next to this script.")

    client = Supadata(api_key)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    before = client.account()
    print(f"Supadata plan: {before['plan']}, credits used {before['usedCredits']}/{before['maxCredits']}")

    video_ids = client.channel_video_ids(args.channel, args.limit, args.type)
    print(f"Found {len(video_ids)} videos on {args.channel}")

    index = []
    for n, video_id in enumerate(video_ids, 1):
        json_path = out_dir / f"{video_id}.json"
        previous = {}
        if json_path.exists() and not args.force:
            previous = json.loads(json_path.read_text())
            if "transcript" in previous:
                print(f"[{n}/{len(video_ids)}] {video_id}: already downloaded, skipping")
                index.append(previous)
                continue

        print(f"[{n}/{len(video_ids)}] {video_id}: fetching...")
        try:
            # Reuse metadata from an earlier failed attempt rather than paying for it again.
            record = fetch_video(client, video_id, args, previous.get("metadata"))
        except SupadataError as e:
            print(f"Stopping: {e}", file=sys.stderr)
            break

        json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        title = (record.get("metadata") or {}).get("title", "")
        if "transcript" in record:
            path = text_path(out_dir, record)
            path.write_text(transcript_text(record))
            print(f"    saved {path.name}")
        else:
            print(f"    no transcript for {title or video_id}: {record['transcriptError']}")
        index.append(record)

    summary = [
        {
            "id": r["id"],
            "url": r["url"],
            "title": (r.get("metadata") or {}).get("title"),
            "uploadDate": (r.get("metadata") or {}).get("uploadDate"),
            "transcriptLang": (r.get("transcript") or {}).get("lang"),
            "transcriptFile": text_path(out_dir, r).name if "transcript" in r else None,
            "error": r.get("transcriptError"),
        }
        for r in index
    ]
    (out_dir / "index.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    done = sum(1 for r in index if "transcript" in r)
    after = client.account()
    print(f"\nTranscripts saved: {done}/{len(video_ids)} in {out_dir}/")
    print(f"Credits used this run: {after['usedCredits'] - before['usedCredits']} "
          f"({after['usedCredits']}/{after['maxCredits']} this period)")
    return 0 if done == len(video_ids) else 1


if __name__ == "__main__":
    sys.exit(main())
