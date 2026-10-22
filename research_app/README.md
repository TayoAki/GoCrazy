# Outlier Research app

Finds viral **outliers** in a niche with the ScrapeCreators API, tears each one down into the 17-element card from
[`AGENT_PLAYBOOK.md`](../AGENT_PLAYBOOK.md) (Phase 3), and plans a week of content from what the outliers have in common,
with the odds of each post going viral.

## Run it

```bash
pip install -r requirements.txt
echo "SCRAPECREATORS_API_KEY=your_key" >> .env     # or export it; .env is gitignored
echo "OPENROUTER_API_KEY=your_key" >> .env         # optional: AI teardowns and week plans
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
pulls 6 frames from the first 3 seconds plus about 15 frames across the whole video, counts hard cuts, then **deletes the
video** (frames stay on your machine for review only).

With an OpenRouter key, an AI pass then fills the fields that need eyes (written and visual hook, angle, delivery,
format, beats, takeaway) from the frames, transcript, caption and Instagram's audio facts. It costs about 2 cents per reel
with the default model, and you can re-run it on its own from the teardown page. It never overwrites a field you edited.

Every field on the card shows where its value came from:

| Badge | Meaning |
|---|---|
| `api` / `auto` | Read straight from the data: stats, the spoken hook, word count, cuts, CTA keyword |
| `heuristic` | A pattern match: hook pattern, video type, series, easy/complex, audio, fast-cut format. Check it |
| `needs review` | Needs eyes or judgement: written hook, visual hook, angle, delivery, story type, format, beats, takeaway |
| `ai` | Filled by the AI pass. Check it |
| `human` | You set it. Re-running the teardown never overwrites these |

Transcripts are only fetched for reels up to 2 minutes unless you turn on long transcription in the project's
settings (10 credits per started minute). Music-only reels keep no transcript, since it would only be song lyrics.

## Week plan and odds of virality

**Plan** tab: describe the client (who they are, what they sell, real stories and results), give their follower count
and a start date, and press **Plan my week** (needs at least 3 teardowns; about 25 cents with the default model).

1. The week's shape comes from the playbook: the funnel slots (TOFU / MOFU / BOFU) and CTA types for the client's follower tier.
2. The AI outlines 7 posts, each borrowing the **structure** of named outliers (hook pattern, format, angle, beats), never
   their content, and never using the same format or angle more than twice.
3. Each post is then written out in full: hook (spoken, on-screen and visual), beat-by-beat script, CTA, caption,
   what to film, and what the client still needs to supply. Anything the client must fill in shows as a `[[placeholder]]`,
   never an invented fact.

The **odds** are computed in code, not guessed by the AI:

- **Base rate:** the share of all scanned reels from in-range creators that beat 1×, 2×, 5× and 10× the creator's
  follower count.
- **Evidence multiplier:** `1 + 2 × (average share of torn-down outliers using the same hook pattern, format, angle, video type,
  complexity and delivery)`, plus 0.25 if the source outliers' median ratio is 10× or more.
- **Funnel factor:** TOFU 1.15, MOFU 0.9, BOFU 0.8 (authority posts × 0.75), because sales posts reach fewer people.
- The multiplier is clamped to 0.5–3 and each probability is capped at 60%. Bands: strong (≥ 1.75), good (≥ 1.2),
  average (≥ 0.9), below average. Confidence is "medium" with at least 15 teardowns and 500 scanned reels, otherwise "low".

Every post shows its odds ladder, the factors behind it and the outliers it borrows from, so you can check the reasoning.

## Screen layout

Built from the wireframe: left rail (Home, Research, Activity, Bank, Settings) · sidebar (New research + projects) ·
tabs (Outliers / Creators / Teardowns / Plan) · main content (outlier grid, full-page teardown, week plan) · right sidebar
(context for the current view: patterns, the selected outlier, or the plan's method) · bottom bar (API status, credits,
live progress).

The UI was polished with the [impeccable](https://github.com/pbakaus/impeccable) design skill: one type scale and spacing
scale, themed light and dark mode, 4.5:1 text contrast, visible keyboard focus, and skeletons instead of spinners. Its
detector reports no findings on `static/`.

**Bank → Export** downloads your saved outliers and their teardowns as JSON for the templatizing step.

## Read-only snapshot (e.g. for Vercel)

The full app can't run on a static host (long background jobs, ffmpeg, SQLite), but you can publish a read-only copy of
your research and plans:

```bash
python -m research_app.export_static --out site                    # UI + data + images
python -m research_app.export_static --out site --no-transcripts   # leave out other creators' words
npx vercel deploy site --yes                                       # needs a Vercel login or VERCEL_TOKEN
```

The snapshot answers the same routes from a bundled `snapshot.js` and hides every action. The client descriptions you
typed into plans are left out. It does include other creators' covers, frames, and (unless `--no-transcripts`) transcripts,
so keep the deployment private, for example with Vercel's Deployment Protection. `site/` is gitignored.

## API notes (checked against live responses, October 2026)

- Reel search returns creators **without** follower counts, so a profile lookup per creator is required.
- `/v1/instagram/post?trim=true` returns the media at the top level (`xdt_shortcode_media`), not under `data`.
- The credit balance endpoint answers `{"creditCount": N}`.
- Transcripts over 120 s are rejected with HTTP 400 (not charged) unless `allow_long_transcription=true`.
