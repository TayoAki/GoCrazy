# Outlier Research app

Finds viral **outliers** in a niche with the ScrapeCreators API and pre-annotates each one with the 17-element teardown
card from [`AGENT_PLAYBOOK.md`](../AGENT_PLAYBOOK.md) (Phase 3), so it can be templatized next.

## Run it

```bash
pip install -r requirements.txt
echo "SCRAPECREATORS_API_KEY=your_key" >> .env     # or export it; .env is gitignored
python -m research_app                             # then open http://127.0.0.1:8000
```

You also need **ffmpeg** for hook frames and cut counts (`brew install ffmpeg` / `apt install ffmpeg`). Without it, everything
else still works. Data lives in `data/` (SQLite database, covers, frames), which is gitignored.

## How the research works

1. **Search.** Each keyword runs through ScrapeCreators' reel search (about 12 s and 1 credit per page). Paid partnerships
   and ads are skipped. The creators behind the results are collected.
2. **Size check.** Each creator's follower count comes from their profile (1 credit, or free if cached in the last
   30 days). Creators outside the follower range (default 1K–500K) are skipped.
3. **Scan.** Each remaining creator's recent reels are pulled (12 per page, 1 credit per page, default 2 pages). The
   creators found by the most keywords go first.
4. **Outliers.** Any reel with `views ÷ followers ≥ 5` (default) posted in the last 365 days is saved, and its cover is
   downloaded.
5. **Budget.** Every run has a hard credit cap (default 300). The run stops cleanly when it's reached, or when you press Stop.

## Teardown (annotation)

Select an outlier and press **Tear down** (about 2 credits). The app fetches the post details and transcript, downloads the video,
pulls 6 frames from the first 3 seconds plus one every 2 seconds, counts hard cuts, then **deletes the video** (frames
stay on your machine for review only).

Every field on the card shows where its value came from:

| Badge | Meaning |
|---|---|
| `api` / `auto` | Read straight from the data: stats, the spoken hook, word count, cuts, CTA keyword |
| `heuristic` | A pattern match: hook pattern, video type, series, easy/complex, audio, fast-cut format. Check it |
| `needs review` | Needs eyes or judgement: written hook, visual hook, angle, delivery, story type, format, beats, takeaway |
| `human` | You set it. Re-running the teardown never overwrites these |

Transcripts are only fetched for reels up to 2 minutes unless you turn on long transcription in the project's
settings (10 credits per started minute). AI annotation of the review fields (OpenRouter) isn't built yet.

## Screen layout

Built from the wireframe: left rail (Home, Research, Activity, Bank, Settings) · sidebar (New research + projects) ·
tabs (Outliers / Creators / Teardowns) · main content (outlier grid, patterns summary, run card) · right sidebar
(selected outlier and its editable teardown card) · bottom bar (API status, credits, live run progress).

**Bank → Export** downloads your saved outliers and their teardowns as JSON for the templatizing step.

## API notes (checked against live responses, October 2026)

- Reel search returns creators **without** follower counts, so a profile lookup per creator is required.
- `/v1/instagram/post?trim=true` returns the media at the top level (`xdt_shortcode_media`), not under `data`.
- The credit balance endpoint answers `{"creditCount": N}`.
- Transcripts over 120 s are rejected with HTTP 400 (not charged) unless `allow_long_transcription=true`.
