# Outlier Research app

Finds viral **outliers** in a niche with the ScrapeCreators API, tears each one down into the 17-element card from
[`AGENT_PLAYBOOK.md`](../AGENT_PLAYBOOK.md) (Phase 3), and plans a week of content from what the outliers have in common,
with the odds of each post going viral.

## Run it

```bash
pip install -r requirements.txt
echo "SCRAPECREATORS_API_KEY=your_key" >> .env     # or export it; .env is gitignored
python -m research_app                             # then open http://127.0.0.1:8000
```

You also need **ffmpeg** for hook frames and cut counts (`brew install ffmpeg` / `apt install ffmpeg`). Without it, everything
else still works. Data lives in `data/` (SQLite database, covers, frames), which is gitignored.

### The AI provider

AI teardowns, scene breakdowns, madlibs and week plans need one of:

| Provider | How | Cost |
|---|---|---|
| **Claude Code** (default when installed) | The `claude` command on this machine, logged in to your Claude plan | Your plan's usage, no per-call charge |
| **OpenRouter** | `OPENROUTER_API_KEY` in `.env`; the model is the project's AI model setting | Per call (shown in the app) |

With Claude Code, each request runs `claude -p` from an empty folder with no project settings, hooks or MCP servers, no
saved session, and only its Read tool, allowed only on the media folder (that's how it looks at the frames). Set
`AI_PROVIDER=openrouter` or `AI_PROVIDER=claude-code` to force one, and `CLAUDE_CODE_AI_MODEL` to pick Claude Code's model.
The bottom bar shows which one is in use.

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

**Accounts to study.** Name accounts you want to learn from (e.g. one that grew fast in the niche). They're scanned first,
8 pages deep (about 96 reels), whatever their size, with the same 5× test; their outliers show "found via @handle". The
odds' base rates still only use creators inside the follower range, so one huge account can't skew them.

## Carousels and TikTok slideshows

Turn on **Instagram carousels** and **TikTok slideshows** under a project's post types (Settings, or New research). They
are researched the same way as reels: search, size check, scan, the same 5× outlier test, doubled-down templates, a
teardown, a madlib and plans.

- **Instagram carousels.** Instagram has no carousel search, so carousels come from the same creators the reel and account
  searches find: each creator's posts feed (`/v2/instagram/user/posts`, 12 posts a page, 1 credit, default 2 pages; 8
  for accounts you study). Reels on those pages are saved too. Instagram shows **no views** for carousels, so a carousel's
  views are estimated from its likes at the niche's own likes-per-view rate (the median of its reels, 1.7–2.5% across
  six niches; 1.92% until a project has 100 reels). Its ratio is marked ≈ everywhere, and its odds use carousel base
  rates estimated the same way. Carousels mostly reach followers, so treat a carousel's ratio as a ranking, not a count.
- **TikTok slideshows.** TikTok's keyword search returns videos only; its **Top** search (`/v1/tiktok/search/top`)
  returns photo slideshows too, with real play counts and the author's follower count, so no profile lookup is needed.
  Each keyword runs `tiktok_search_pages` pages (about 30 results, 1 credit each); then each slideshow creator's feed
  (`/v3/tiktok/profile/videos`, `tiktok_pages` pages) is scanned for more slideshows and doubled-down templates. Only
  slideshows are kept, not TikTok videos. TikTok accounts are stored as `tt:<handle>` so they never mix with an
  Instagram account of the same name; the app shows them as @handle with a TikTok badge.
- **Teardown, slide by slide.** Every slide is saved (`slide_NN.jpg`, up to 20). Slide 1 is the hook: its largest text
  is the written hook and its image the visual hook. The AI fills the card from the slides (plus a **carousel type**:
  tutorial, do vs don't, tips, storytelling, transformation, problem/solution, list or types), describes each slide in
  SEALCaM with its text measured, and makes a madlib of the slides' text, one line per slide. The post's sound (a
  TikTok song, or an Instagram carousel's music) is recorded; nothing is transcribed.
- **Plans.** A post built from a slide teardown is a slide post of the same kind: its cover slide, then each slide's
  text (filled from the source's madlib), image and design, a SEALCaM slide list that recreates the reference slides,
  the caption and the sound. The plan form can plan one post type only.

## YouTube videos and Shorts

Turn on **YouTube videos** and **YouTube Shorts** under a project's post types. Channels are stored as `yt:<handle>`
and videos as `yt-<video id>`, so neither ever mixes with an Instagram or TikTok namesake.

- **Search.** Each keyword runs YouTube video search twice, sorted by relevance and by popularity, both limited to this
  year (`/v1/youtube/search`, about 20 videos, 1 credit each, `youtube_search_pages` pages). Shorts search hides each
  Short's channel and date, so the top `youtube_short_lookups` Shorts per keyword are looked up (`/v1/youtube/video`,
  1 credit each) to learn whose they are. Their channels then join the scan like any other.
- **Scan.** Channels surfaced by the most keywords, then by the most search hits, are scanned first (`max_creators`).
  Each one costs a channel lookup (subscribers, cached 30 days), `youtube_pages` pages of its latest long videos (30 a
  page; the dates are YouTube's "4 months ago", so they are approximate) and one page of its latest Shorts (about 26,
  with exact dates). Channels under `min_followers` or over `youtube_max_subscribers` subscribers (default 2M) aren't
  scanned.
- **The outlier test.** Subscriber counts predict views poorly on YouTube, so a YouTube outlier is measured against its
  own channel: views ÷ the channel's median views for that kind, with long videos and Shorts measured separately. It
  counts at `youtube_min_ratio` (default 3×), posted within `max_age_days` and at least a week ago, since a newer
  video's views are still climbing. The median uses the channel's videos of that kind from the research window that are
  at least a week old (all of them when it posted fewer than 5), and needs at least 5. These outliers are stored with
  `measure = "median"` and the median they were compared with (`typical`). Base rates for planning are measured the same
  way: the share of a niche's videos that beat their channel's median 1×, 2×, 5× and 10×.
- **Teardown, without the video.** ScrapeCreators doesn't download YouTube videos, so a teardown (3 credits: details,
  transcript, comments) works from what YouTube shows:
  - the thumbnail, which is the hook of a long video (a Short's comes in its own 9:16, from `oardefault`)
  - the three frames YouTube samples from every video
  - the title, description, keywords and chapters
  - the timed transcript (from the captions)
  - the peaks of YouTube's own "most replayed" graph, with the words spoken there
  - the top comments

  The AI fills the usual card, plus the title's formula, the thumbnail's text, what the intro does and when the main
  content starts, what keeps people watching, why people rewatch the peaks, any sponsor or plug, and what the
  comments react to. The chapters (or, without them, eight even slices of the transcript) become the video's
  **sections**, each with a beat and a summary; a Short has none. The madlib templates the title, the thumbnail and its
  text, the spoken intro (a Short's whole script), the description's first line and the section outline.
- **Plans.** A Short is written like a reel (a vertical video, with a shot list). A long video gets its packaging (title,
  thumbnail and its text, filled from the source's madlibs), its intro written word for word, and a section outline,
  each section with what it covers, the device that carries the viewer into the next one and its length. It gets no
  shot list.

## Clips from a long video (with OpenShorts)

The **Clips** tab cuts one long YouTube video into Shorts, reels and TikToks, and writes each clip's hook from what
wins in the niche. Paste a link (any long video in the project is in the list, and a long video's teardown has a
**Plan clips** button). Use your own videos, or ones whose creator agreed to clipping.

- **The moments** come from what YouTube shows about the video: the timed transcript, the whole "most replayed" graph
  (100 slices), the chapters and the top comments. It costs 1–3 credits: the details every time (for the graph), plus
  the transcript and comments when the video has no teardown yet.
- **The hooks** come from the niche's short-form winners in this project and in every project sharing at least half its
  keywords, so a YouTube project borrows from the same niche's Instagram and TikTok project. That means up to 18 reels
  and Shorts (their first spoken line) and up to 10 slideshows and carousels (their cover text). Each group is ranked on
  its own, because slide posts beat their creators' follower counts by far more than videos do.
- **Who posts** is the "About you" of the newest week plan (from this project or a sibling), unless you write one.
- **Each clip** gets:
  - its segments: one, or a cold open (its strongest line first, then the setup played through)
  - the spoken hook and the last line, quoted from the transcript
  - the on-screen hook (at most 8 words), modelled on a named winner
  - a Shorts title and a TikTok/Instagram caption
  - why it should work (how much more it was replayed than the video's average, the comments)
  - what to check before posting (claims, missing context, sponsor or competitor mentions, permission)

  The cuts are aligned in code. Each word gets a time, spread evenly across its caption line, since auto-captions
  overlap. The first segment starts on the first word of the quoted hook and the last ends on the last word of the
  quoted closing line. The edges between segments widen to whole sentences. Clips that overlap a better one, or run
  outside 15–90 s, are dropped.
- **The brief** (Copy brief / Download .md) lists every clip: the cut, the hook said and on screen, the winner it is
  modelled on, the closing line, the title, the caption, why, what to check, and everything said.
- **Rendering** goes through [OpenShorts](https://github.com/mutonby/openshorts): vertical crop with face tracking,
  burned captions and the hook text. Each clip is one OpenShorts job over a stretch of at least a minute around it,
  because that's OpenShorts' shortest range. Only that stretch is transcribed, reframed and, on the hosted service,
  billed.
  - A YouTube link is sent with the stretch as `source_start`/`source_end`.
  - A video file on this computer (the render panel's optional path) is cut to the stretch with ffmpeg and uploaded.
  - When the job is done, its clip is re-cut to the plan's exact segments (`/api/clip/rerender`, in seconds from the
    stretch's start, snapped to OpenShorts' own word timings) and the hook goes on (`/api/hook`). The file is saved to
    `data/media/clips/<plan id>/` and plays in the tab.
  - OpenShorts asks you to confirm you own the video or have the rights to clip it, so the render panel has a box to
    tick. It is sent only when ticked.

### Setting up OpenShorts

| Setup | What to put in `.env` | Notes |
|---|---|---|
| Self-hosted (free) | nothing, or `OPENSHORTS_API_URL` | Run OpenShorts with Docker (its README). This app talks to its dashboard on `http://localhost:5175`, which passes the API through. OpenShorts' backend also takes port 8000, this app's default, so start this app on another port while it runs: `PORT=8001 python -m research_app`. OpenShorts needs a Gemini key: its own `GEMINI_API_KEY`, or this app's (sent as `X-Gemini-Key`), or a local LLM (`LLM_BASE_URL`) |
| Hosted ([openshorts.app](https://www.openshorts.app/)) | `OPENSHORTS_API_KEY=osk_...` | Uses `https://api.openshorts.app`; paid plans from $12/month, free plan 20 minutes a month with a watermark |

The bottom of the Clips tab says whether OpenShorts answers. YouTube sometimes blocks downloads from servers. If a link
fails, render from the video file instead.

## Teardown (annotation)

Select an outlier and press **Tear down** (about 2 credits). The app fetches the post details and transcript, downloads the video,
pulls 6 frames from the first 3 seconds, about 15 frames across the whole video and one or two frames from every scene,
finds the hard cuts, then **deletes the video** (frames stay on your machine for review only).

With an AI provider, an AI pass then fills the fields that need eyes (written and visual hook, angle, delivery,
format, beats, takeaway) from the frames, transcript, caption and Instagram's audio facts. On OpenRouter it costs about 2 cents per reel
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

## Scenes (SEALCaM)

Each teardown also breaks the video down scene by scene. A scene starts at a hard cut; flash cuts under 0.3 s merge into
their neighbour, and holds longer than 6 s split into ~5 s segments of the same shot (a green-screen background swap or a
speaker changing sides rarely registers as a cut). For every scene the AI writes:

| | Field | In terms of |
|---|---|---|
| S | Subject | primary and secondary subject, foreground and background elements |
| E | Environment | location type, set design, spatial depth, background treatment |
| A | Action | subject movement, camera movement, environmental motion |
| L | Lighting | key, fill, rim, practicals, contrast ratio, exposure, colour temperature |
| Ca | Camera | camera type, lens and focal length, framing and angle, camera motion |
| M | Metatokens | realism, texture and grain, motion cadence, capture quality, platform cues |

plus the scene's beat, its on-screen text and the words spoken during it. On OpenRouter it costs 1–9 cents per reel.
Teardowns made before this existed get a **Break down scenes** button (it fetches the video again; the post lookup is cached).

**On-screen text, measured.** For each block of text in a scene the AI gives the exact words (case, punctuation and emoji
as shown), where the block sits, a look-alike font, weight, case, letter colour, highlighted words, outline, shadow,
background box, alignment and animation. The app then measures the frame's pixels inside that box: the letters' actual
colour, the number of lines, the line height (as % of the frame and as pixels on a 1080×1920 reel) and the block's
position. A brief can then say "2 lines, each 3.1% of the frame height (≈60 px), white (measured #F6F1ED), from 18% to 26%
down the frame" instead of "big white text".

## Madlibs

**Make madlib** on a teardown turns the reel's words into a fill-in-the-blank template (playbook Phase 4): the hooks,
every spoken line, every on-screen text and the caption, with the frame words kept and each blank a named, typed slot
(`{{PRODUCT:ITEM}}`, `{{N:NUMBER}}`) with a rule for filling it. Lists become `[REPEAT {{N:NUMBER}} times]…[/REPEAT]`.

The app lines each template up against the reel's own words, so the teardown shows **the original variables** (what the
creator put in each blank) next to an editor for **your version**: change a value and every line that uses it is
rewritten. Plans fill these same madlibs, so a planned post keeps the reference's structure with new content.

## Doubled down

An outlier is one reel that beat its creator's follower count. A **doubled-down** account found a template and keeps
posting it: the same caption headline (e.g. "Colour combinations…") in at least 4 of their scanned reels, whose typical
reel reaches at least 10% of their followers, and that is either a habit (20% or more of their reels) or a proven winner
(its typical reel beats the follower count). The **Doubled down** tab lists them with their template's reels; any of
those reels can be added as an outlier for a teardown.

**Copied across creators.** A format that several creators copy is stronger evidence than one account's habit: it works
for different audiences. The tab's first section lists them. A format is a phrase (from caption headlines, plus the
cover or hook text of torn-down posts) or a hook frame (a torn-down hook's madlib with its blanks removed, e.g. "how to
be a ___") that:

- 3 or more creators use, in the same post kind (reel, carousel or slideshow);
- most of them win with: at least 2, and at least half, get 2× or more their own typical post of that kind with it (for
  a creator with fewer than 5 posts of that kind, beating the follower count counts as a win);
- has a typical lift of 2× or more across those creators;
- isn't the niche itself: phrases inside a project keyword, or holding a one-word keyword ("learning mahjong"), are skipped.

A format whose posts are mostly another's (e.g. "body workout" inside "full body") is merged into it. Each format shows
one example per creator, and any of them can be added as an outlier ("Copied format") to tear down. Plans prefer
teardowns of a copied format above everything else, briefs say which format a reference belongs to, and the odds add
+0.25 to the evidence when a source belongs to one.

## Week plan and odds of virality

**Plan** tab: describe the client (who they are, what they sell, real stories and results), give their follower count
and a start date, and press **Plan my week** (needs at least 3 teardowns; about $1 with the default model, most
of it the shot lists).

1. The week's shape comes from the playbook: the funnel slots (TOFU / MOFU / BOFU) and CTA types for the client's follower tier.
2. The AI outlines 7 posts, each copying the **template** of named outliers (format, set, visuals, hook pattern, beats),
   never their content, and never using the same format or angle more than twice. A post must keep its sources' format;
   the code checks this and fixes it if the AI drifts.
3. Each post is then written out in full: hook (spoken, on-screen and visual), beat-by-beat script, CTA, caption,
   what to film, and what the client still needs to supply. The script fills the source outlier's madlib. Anything the
   client must fill in shows as a `[[placeholder]]`, never an invented fact.
4. Each post gets a **shot list** in SEALCaM, one shot per setup or cut. Each shot recreates a named scene of the source
   outliers (same set, framing, movement, lighting and pace) and says what it keeps and what it changes. Its on-screen
   text copies the reference's text style (font, case, colours, measured size and position).

**Checks in code** after the AI writes:

- **No copying.** The reference's own specific content (numbers of 3+ digits and names: capitalised words it never
  writes in lowercase, outside headlines) is collected per outlier. A post that reuses any of those numbers, or two or more
  of its names, is rewritten once with those words banned; if it still reuses them it's flagged. Words from the client's
  own description don't count.
- **No copied value.** The AI then compares each post with its references: the template, hook and topic may match, but
  the specific tips, rules, examples and jokes must be new. A post that repeats them is rewritten (up to twice); what's still
  repeated is flagged.
- **Same text format.** Each shot's on-screen text gets the reference's case and the spacing around symbols such as `+`.
  Then it must fit the reference's on-screen madlib (one text block or a run of them), and its line count, punctuation
  and emoji must match the reference. Shots that differ get one AI fix pass; anything still different is flagged on the
  shot ("Check the text").

The **odds** are computed in code, not guessed by the AI:

- **Base rate:** the share of all scanned reels from in-range creators that beat 1×, 2×, 5× and 10× the creator's
  follower count.
- **Evidence multiplier:** `1 + 2 × (average share of torn-down outliers using the same hook pattern, format, angle, video type,
  complexity and delivery)`, plus 0.25 if the source outliers' median ratio is 10× or more.
- **Funnel factor:** TOFU 1.15, MOFU 0.9, BOFU 0.8 (authority posts × 0.75), because sales posts reach fewer people.
- The multiplier is clamped to 0.5–3 and each probability is capped at 60%. Bands: strong (≥ 1.75), good (≥ 1.2),
  average (≥ 0.9), below average. Confidence is "medium" with at least 15 teardowns and 500 scanned reels, otherwise "low".

Every post shows its odds ladder, the factors behind it and the outliers it borrows from, so you can check the reasoning.

### Export: the brief

The research ends at a brief that anything downstream can take: a human editor, an AI video tool, or an editing skill.
**Copy brief** / **Download .md** on a post, or **Export week** for all of them. Each brief is Markdown with:

- **The idea:** topic, angle, hook pattern, odds, why it should work, the outliers it borrows from (with links), the risk
- **Before you film:** every `[[placeholder]]` to replace with real facts
- **Script:** the hook (say, on screen, show) and each beat (say, film, edit), with the madlib line each one fills, the
  call to action, caption and hashtags
- **Shot list (SEALCaM):** one entry per shot, with the words said during it, the reference scene it recreates, what it
  keeps and changes, and the exact text spec to match
- **Teleprompter:** just the words, in order
- **Reference breakdown:** each source outlier's card, its madlib with a table of its original variables (and a column for
  yours), and every scene in SEALCaM with its measured text

Also available at `GET /api/plans/{id}/export.md` (the week) and `?post=N` (one post).

## Screen layout

Built from the wireframe: left rail (Home, Research, Activity, Bank, Settings) · sidebar (New research + projects) ·
tabs (Outliers / Doubled down / Creators / Teardowns / Plan) · main content (outlier grid, full-page teardown, week plan) · right sidebar
(context for the current view: patterns, the selected outlier, or the plan's method) · bottom bar (API status, credits,
live progress).

The UI was polished with the [impeccable](https://github.com/pbakaus/impeccable) design skill: one type scale and spacing
scale, themed light and dark mode, 4.5:1 text contrast, visible keyboard focus, and skeletons instead of spinners. Its
detector reports no findings on `static/`.

**Bank → Export** downloads your saved outliers and their teardowns as JSON for the templatizing step.

## Deploy to Railway

The full app runs on Railway (long research runs, ffmpeg, SQLite) from the `Dockerfile` in the repo root:

1. New project → deploy this GitHub repo. Railway builds the Dockerfile.
2. Add a **volume** mounted at `/data`. The app keeps its database and frames there (it reads `RAILWAY_VOLUME_MOUNT_PATH`,
   or `DATA_DIR`).
3. Set variables: `SCRAPECREATORS_API_KEY`, `OPENROUTER_API_KEY`, and `APP_PASSWORD`. The image doesn't include
   Claude Code, so the deployed copy uses OpenRouter. (To use your Claude plan there instead, the image would need the
   `claude` CLI and a `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`.) Every page and API call then
   needs that password (the browser asks; any username). On Railway the app refuses to run without one, because an open
   copy could spend your credits.
4. Healthcheck path `/api/health`, then generate a domain.

**Moving your research there:** Settings → **Download backup** on your local copy, then Settings → **Restore from a
backup…** on the deployed one. A backup is one `.tar.gz` of the database and media; restore uploads it in 8 MB parts and
replaces everything on that copy (`GET /api/backup`, `POST /api/restore`).

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
- `/v2/instagram/user/posts` mixes reels (`media_type` 2, with `play_count`), carousels (`media_type` 8,
  `carousel_media[].image_versions2`) and photos. Carousels carry `like_count` but no view count; slide alt text is only
  "Photo by …", so slide text has to be read from the images. Pages continue with `next_max_id`.
- `/v1/tiktok/search/top` items have `content_type` (`multi_photo` for a slideshow), `images` (a list of links),
  `statistics.play_count`, `collect_count` (saves) and `author.follower_count`. Profile feeds put the slides under
  `image_post_info.images[].display_image.url_list`. TikTok slide links expire after a few weeks; the teardown fetches
  fresh ones (`/v2/tiktok/video`, 1 credit) when a download fails.
- `/v1/youtube/search` puts video results under `videos` (with `channel.handle`, `viewCountInt`, `publishedTime`,
  `lengthSeconds`) and Shorts under `shorts`. Shorts results carry only the id, title and views, and come back empty when
  filtered by `uploadDate` or sorted. `/v1/youtube/search/hashtag` is the same.
- `/v1/youtube/channel-videos` gives 30 long videos a page (`continuationToken`) with dates computed from "4 months
  ago". `/v1/youtube/channel/shorts` gives about the 26 latest Shorts in one page, with exact `publishDate`, likes and
  comments.
- `/v1/youtube/video` has `chapters`, `keywords`, `durationMs`, `isPaidPromotion` and `most_replayed.markers` (100
  buckets, each with `intensityScoreNormalized`), but no transcript text and no downloadable video (`downloadOptions`
  is empty). The transcript is its own call (`/v1/youtube/video/transcript`: `transcript[]` with `startMs`/`endMs`).
- Every video has `i.ytimg.com/vi/<id>/` images: `maxresdefault.jpg` (the thumbnail), `oardefault.jpg` (a Short's 9:16
  thumbnail) and `hq720_1.jpg`–`hq720_3.jpg` (three frames YouTube samples from the video).
