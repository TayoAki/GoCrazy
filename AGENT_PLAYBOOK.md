# Short-Form Content Agent Playbook

**You are an AI agent. This document is your complete operating manual.** Follow it in order, exactly as written.
It turns one client's expertise into a month of short-form video scripts (Instagram Reels; also usable for TikTok
and YouTube Shorts) by:

1. **Researching** proven viral videos ("outliers") in the client's niche
2. **Extracting** the elements that made each one work
3. **Templatizing** those elements into fill-in-the-blank "madlibs"
4. **Filling** the madlibs with the client's own knowledge, stories and proof, in the client's own words
5. *(Optional)* **Producing** approved scripts as videos

**Tool stack:**

- **ScrapeCreators** finds outliers: reel search, creator follower counts, reel view counts, transcripts.
- **OpenRouter** runs the language-model steps: templatizing, filling and QA.
- **Hypit** turns approved scripts into edited videos.
- **Supadata** is the fallback for transcripts and YouTube research.

See [Tools and access](#tools-and-access).

The method comes from the 13 videos on [@PersonalBrandLaunch](https://www.youtube.com/@PersonalBrandLaunch)
(see the [source map](#appendix-e-source-map)). Where the videos don't give an exact number, this playbook sets one
so you never have to guess. Those numbers are marked **(playbook default)**. A human may override them in the
client profile.

---

## Contents

- [How to read this document](#how-to-read-this-document)
- [The 13 hard rules](#the-13-hard-rules)
- [Glossary](#glossary)
- [Tools and access](#tools-and-access)
- [Output folder layout](#output-folder-layout)
- [Phase 0: Intake (client profile and Client Bank)](#phase-0-intake)
- [Phase 1: Plan the month](#phase-1-plan-the-month)
- [Phase 2: Research outliers](#phase-2-research-outliers)
- [Phase 3: Extract elements](#phase-3-extract-elements)
- [Phase 4: Templatize (build the madlibs)](#phase-4-templatize)
- [Phase 5: Fill (write the scripts)](#phase-5-fill)
- [Phase 6: Quality gate](#phase-6-quality-gate)
- [Phase 7: Monthly review and doubling down](#phase-7-monthly-review-and-doubling-down)
- [Phase 8: Produce videos with Hypit (optional)](#phase-8-produce-videos-with-hypit-optional)
- [Appendix A: Closed vocabularies](#appendix-a-closed-vocabularies)
- [Appendix B: Prompts for sub-tasks](#appendix-b-prompts-for-sub-tasks)
- [Appendix C: Worked example, start to finish](#appendix-c-worked-example)
- [Appendix D: Run checklist](#appendix-d-run-checklist)
- [Appendix E: Source map](#appendix-e-source-map)

---

## How to read this document

- **MUST / MUST NOT** are mandatory. **SHOULD** is the default unless the client profile says otherwise.
- Do the phases **in order: 0 → 1 → 2 → 3 → 4 → 5 → 6**. Phase 7 runs only when performance data exists.
- Every phase ends with a **Gate**, a checklist. You MUST NOT start the next phase until every box in the gate is
  true. If a box can't be made true, follow [When you are blocked](#when-you-are-blocked).
- Every phase writes its output to a **named file with a fixed format** (see [Output folder layout](#output-folder-layout)).
  Never rename fields. Never add values outside the [closed vocabularies](#appendix-a-closed-vocabularies).
- When a step says "record", write it into that phase's output file immediately. Don't keep it in memory.
- If this document and your own judgement disagree, **follow this document**.

### When you are blocked

Stop and write `BLOCKED.md` in the month folder. It must contain:

1. The phase and step number where you stopped
2. Exactly what is missing (an input, access, credits, or a decision)
3. The exact question the human needs to answer, with options if there are any
4. What you've already completed

Don't improvise around a block. Don't invent data to get past a gate.

---

## The 13 hard rules

These override everything else in this document.

1. **Never invent facts about the client.** Every personal story, result, number, credential, client win and
   opinion in a script MUST come from the Client Bank and be cited by its ID (e.g. `S3`, `P1`). If you need a fact
   that isn't in the bank, write `[[NEEDS CLIENT INPUT: <what is needed>]]` in the script and keep going.
2. **Borrow structure, never content.** You may reuse a source video's *hook pattern* and *script structure*. You
   MUST NOT reuse its *value* (its facts, tips, stories or examples). The body of a filled script MUST NOT share any
   run of **6 or more consecutive words** with any source transcript (see the [overlap check](#check-q5-overlap)).
3. **Only borrow from proven outliers.** A source video MUST pass the [5x test](#the-5x-test) and MUST be
   **12 months old or newer** (playbook default; newer is better).
4. **Every hook stack has three hooks**: verbal, written and visual. They MUST come from **at least 2 different
   source videos** (3 is better), so no script is a copy of one creator.
5. **The value must be measurable.** Every script MUST teach or show something specific a viewer could act on or
   picture. See the [measurable value test](#the-measurable-value-test).
6. **No fluff.** MUST NOT write trends, memes, dances, "aesthetic" clips or anything without a takeaway, even if
   it would get views.
7. **Credit outside sources.** If a fact comes from a study, article or another expert (not the client), the
   script MUST say so out loud ("according to…", "a study from…").
8. **Never name or imitate another creator.** Don't use their name, brand, catchphrase or signature format name.
9. **Use only the closed vocabularies** in [Appendix A](#appendix-a-closed-vocabularies) for every labeled field.
10. **Record every source URL.** Every outlier, hook and template MUST trace back to a URL.
11. **Drafts only.** MUST NOT post, publish, message, comment or DM anyone. Your deliverables are drafts for a human to review.
12. **Protect credentials.** Read API keys from environment variables (`SCRAPECREATORS_API_KEY`,
    `OPENROUTER_API_KEY`, `SUPADATA_API_KEY`). Never print, log or write a key into an output file.
13. **When producing video, replicate the production pattern, never the source itself.** A source video may be used
    as a *reference* for pacing, shot rhythm, caption style and edit structure only. The finished video MUST use the
    client's script, the client's own footage, voice and likeness (or properly licensed or generated assets), and its
    own music choice. It MUST NOT contain any of the source's footage, audio, voice, face, on-screen text or captions.

---

## Glossary

Use these words exactly as defined.

| Term | Exact meaning |
|---|---|
| **Client** | The person or business you're making content for. |
| **Client Bank** | The client's own material: knowledge, stories, proof, offers, FAQs and opinions. It's the only source of value and facts. Built in Phase 0. |
| **Niche** | The client's one broad industry (e.g. fitness, real estate, dog training). |
| **Sub-niche** | One of 5 to 7 narrower topics inside the niche that the client posts about. |
| **Outlier** | A short-form video from a small or mid-size creator that massively beat that creator's normal performance. Measured with the 5x test. |
| **Outlier ratio** | `views ÷ creator_followers` for another creator's video. On the client's own page: `views ÷ client_average_views`. |
| **5x test** | Outlier ratio ≥ 5.0 for another creator's video. |
| **Hook** | The first 3 seconds of a video. There are three kinds: **verbal** (what you *hear*), **written** (on-screen text you *read*) and **visual** (what you *see* happening). |
| **Hook stack** | The three hooks (verbal + written + visual) planned for one video. |
| **Topic** | What the video is about. Always one sub-niche. |
| **Value** | The specific takeaway: the "meat" of the video. |
| **Angle** | The direction the video takes. One of 7 (tutorial, comparison, myth bust, do vs don't, tip/hack, transformation, challenge). |
| **Delivery** | Whether the angle is told as **educational** content or as a **storytelling** narrative. |
| **Script structure** | The ordered sequence of beats a script follows, independent of niche. |
| **Beat** | One functional unit of a script (e.g. HOOK, STEP, PROOF, CTA). See [beats](#a8-beat-labels). |
| **Madlib / template** | A hook or script structure with all niche-specific content replaced by labeled slots. |
| **Slot** | A labeled blank in a template: `{{NAME:TYPE}}`. |
| **Frame words** | The words a template keeps because they create the pattern (e.g. "Is it possible to", "Here's the", "Step one:"). |
| **Format** | How the video is filmed (clone, voiceover, setting change, etc.). |
| **CTA** | The call to action at the end (follow, freebie, paid offer, engagement, none). |
| **Content type** | **Educational** (builds authority through knowledge), **storytelling** (builds connection), or **authority** (shows results and proof, builds trust and leads). |
| **Funnel stage** | **TOFU** (top: broad and simple, for views), **MOFU** (middle: personal connection, for followers), **BOFU** (bottom: in-depth, proof and offers, for leads). |
| **Bucket** | Why a slot exists this month: **proven** (built from niche outliers), **double_down** (a remake of the client's own outlier), **experiment** (the client's own original idea). |
| **Double down** | Remaking one of the client's own outliers with a deliberate change. |
| **Easy structure** | A repetitive, obvious pattern: the same sentence shape repeated 3 or more times with only the nouns or numbers changing (rankings, "if X then Y" lists). It gets views but few followers. |
| **Complex structure** | Anything that isn't an easy structure: narrative or hyper-educational, not obviously templated. It gets fewer views sometimes but better follower conversion. |

### The 5x test

```
outlier_ratio = views / creator_followers
PASS if outlier_ratio >= 5.0
      AND creator_followers <= 500,000          (playbook default: "small to mid-size")
      AND post_age_days <= 365                  (playbook default)
      AND the post is not marked Sponsored / Paid partnership
      AND views is a real number you observed (not estimated)
```

Example: a creator with 18,000 followers and a reel with 126,000 views has a ratio of 126,000 ÷ 18,000 = 7.0, so it **PASSES**.
A creator with 2,000,000 followers fails the size rule no matter how many views the reel got.

### The measurable value test

The value passes only if **all three** are true:

1. It contains at least one **specific element**: a number, a named step, a named method, a concrete example, a
   before/after, or an exact instruction.
2. A viewer could **do it, check it or picture it** within a day of watching.
3. It answers "**so what do I do?**" with an action, not a feeling.

| Fluffy: FAIL | Measurable: PASS |
|---|---|
| "Be consistent with your puppy." | "Feed every meal inside the crate with the door open for 3 days." |
| "Save more money." | "Move 10% of each paycheck on payday, before you pay any bill." |
| "Post better hooks." | "Put the result in the first 5 words: 'I lost 50 lbs as a broke college kid.'" |

---

## Tools and access

Find out which of these you have **before Phase 2**. Your research mode depends on it.

| Capability | Used for | If you don't have it |
|---|---|---|
| **ScrapeCreators API** (`SCRAPECREATORS_API_KEY`) | **Research Mode S (preferred).** Instagram reel search, creator follower counts, reel view counts, single-reel stats, Instagram transcripts | Use Mode A, B or C |
| **OpenRouter API** (`OPENROUTER_API_KEY`) | Running the [Appendix B](#appendix-b-prompts-for-sub-tasks) prompts (templatize, fill, QA) as model calls | Do those steps yourself, following the same prompts |
| **Hypit** (Node.js ≥ 22.15) | [Phase 8](#phase-8-produce-videos-with-hypit-optional): rendering approved scripts into edited videos | Skip Phase 8; hand over scripts only |
| Web browser logged in to an Instagram **research account** (a separate "dummy" account) | Research Mode A | Use Mode S, B or C |
| A list of reel URLs supplied by a human | Research Mode B | Ask for it (BLOCKED.md) or use Mode S or C |
| Supadata API (`SUPADATA_API_KEY`) | Fallback transcripts for any platform; YouTube Shorts research (Mode C) | Use ScrapeCreators, or ask the human to transcribe manually |
| Ability to view images | Reading on-screen text (the written hook) from cover thumbnails or frames | Mark `written_hook.confidence = "unknown"` |
| File write access | All outputs | Required. If missing, you're blocked |

### ScrapeCreators quick reference (preferred for Instagram)

Base URL `https://api.scrapecreators.com`. Header `x-api-key: $SCRAPECREATORS_API_KEY`. All requests are `GET`.
Every response includes `credits_charged` and `credits_remaining`. **Add `credits_charged` to your running total after
every call.**

| Purpose | Request | Fields you use |
|---|---|---|
| Credit balance | `/v1/account/credit-balance` | `credits_remaining` |
| Search reels by keyword | `/v2/instagram/reels/search?query=<kw>&date_posted=last-year&page=<1-11>` | `reels[].url`, `.shortcode`, `.owner.username`, `.owner.follower_count`, `.taken_at`, `.video_duration`, `.is_paid_partnership`, `.is_ad`, `.thumbnail_src`. **No view count here**, so get it in the next step |
| A creator's reels, with view counts | `/v1/instagram/user/reels?handle=<username>&trim=true` (next page: add `&max_id=<max_id from previous response>`) | `items[].url`, `.code`, `.play_count` (if missing, use `.ig_play_count`), `.created_at` |
| Creator follower count | `/v1/instagram/profile?handle=<username>&cache_max_age=30d` | `data.user.edge_followed_by.count`, `data.user.id` |
| One reel's stats (views + followers in one call) | `/v1/instagram/post?url=<reel URL>&trim=true&cache_max_age=30d` | `data.xdt_shortcode_media.video_play_count`, `.video_duration`, `.taken_at_timestamp`, `.is_paid_partnership`, `.is_ad`, `.owner.username`, `.owner.edge_followed_by.count`, `.thumbnail_src` |
| Instagram transcript | `/v2/instagram/media/transcript?url=<reel URL>&cache_max_age=30d` | `transcripts[0].text`, `transcripts[0].transcript_with_timestamp` (list of `{start, end, text}` in **seconds**, or `null`) |

ScrapeCreators rules (MUST):

- Always add `cache_max_age=30d` where it's supported. Cached answers cost 0 credits.
- Transcripts cost 1 credit for reels up to **120 seconds**. MUST NOT set `allow_long_transcription=true`, which is a paid
  opt-in, unless the client profile allows it.
- MUST NOT set `download_media=true` (10 credits) except in Phase 8, and only with approval.
- HTTP 402 means you're out of credits: **stop** and write BLOCKED.md.
- On 429 or 5xx, retry up to 5 times with waits of 1 s, 2 s, 4 s, 8 s and 16 s.
- Keep total spend within `credit_budget.scrapecreators` from the client profile.

### OpenRouter quick reference

```
POST https://openrouter.ai/api/v1/chat/completions
Authorization: Bearer $OPENROUTER_API_KEY
Content-Type: application/json

{"model": "<openrouter_model from the client profile>",
 "temperature": <see below>,
 "messages": [{"role": "system", "content": "<Appendix B prompt>"},
              {"role": "user",   "content": "<the inputs, as JSON>"}]}
```

- The answer is in `choices[0].message.content`.
- **Model:** use `openrouter_model` from the client profile. Before the first call, confirm the ID exists in
  `GET https://openrouter.ai/api/v1/models` (look for it in `data[].id`). Never guess a model ID. If it's missing,
  write BLOCKED.md.
- **Temperature:** 0.2 for templatize (B1), 0.7 for fill (B2), 0 for QA (B3).
- **Output checking:** parse the reply. If a JSON answer doesn't parse or doesn't match the schema, re-send it once with
  "Your last reply was not valid JSON for the schema. Reply with only the corrected JSON." If it fails twice, do the step
  yourself and note that in the run log.
- **Never** send API keys or other credentials inside a prompt. Send only the client data that the step needs.

### Supadata quick reference

Base URL `https://api.supadata.ai/v1`. Header `x-api-key: $SUPADATA_API_KEY`.

| Purpose | Request | Fields you use |
|---|---|---|
| Check the credit balance (free) | `GET /me` | `usedCredits`, `maxCredits` |
| Transcript of any video URL | `GET /transcript?url=<URL>&mode=auto&text=false` | `content[]` (`text`, `offset` in ms), `lang`. A response with `jobId` → poll `GET /transcript/<jobId>` every 5 s until `status` is `completed` or `failed` |
| Metadata of any post | `GET /metadata?url=<URL>` | `stats.views`, `stats.likes`, `stats.comments`, `author.username`, `media.duration`, `media.thumbnailUrl`, `description` |
| YouTube Shorts search (Mode C) | `GET /youtube/search?query=<kw>&type=video&duration=short&uploadDate=year&sortBy=views&limit=50` | `results[].id`, `.viewCount`, `.duration`, `.uploadDate`, `.channel.id`, `.title` |
| YouTube channel size (Mode C) | `GET /youtube/channel?id=<channelId>` | `subscriberCount` |

**Credit rules (MUST):**

- Call `GET /me` before your first paid call and record the balance in `02_research_log.md`.
- Never spend more than **50% of the remaining credits** in one run without written approval in the client profile
  (`credit_budget`) (playbook default).
- `mode=auto` falls back to AI transcription when a video has no captions, and that costs more than 1 credit.
  Instagram reels usually have no captions. After your **first** transcript call, call `GET /me` again, record the
  actual cost, and compute how many more transcripts you can afford before continuing.
- **Instagram follower counts aren't available from Supadata.** Get them from the creator's profile page (Mode A) or
  from the human (Mode B).
- On HTTP 429 with `details` = "Plan usage limit was exceeded.", **stop**. You're out of credits, so write BLOCKED.md.
  On any other 429 or 5xx, wait and retry up to 5 times, doubling the wait each time (1 s, 2 s, 4 s, 8 s, 16 s).

---

## Output folder layout

Create this structure. `<client>` is a lowercase-hyphenated client name, and `<YYYY-MM>` is the month being planned.

```
work/<client>/
  00_client_profile.json            Phase 0  (persists across months)
  <YYYY-MM>/
    01_month_plan.json              Phase 1
    02_keywords.json                Phase 2
    02_outliers.json                Phase 2
    02_research_log.md              Phase 2  (credits, mode, notes)
    03_elements/<outlier_id>.json   Phase 3  (one file per outlier)
    04_hook_templates.json          Phase 4
    04_structure_templates.json     Phase 4
    05_scripts/<slot_id>.md         Phase 5  (one file per video)
    05_ideation.csv                 Phase 5  (one row per video)
    06_qa_report.md                 Phase 6
    07_review.json                  Phase 7  (only when analytics exist)
    08_production/<slot_id>/        Phase 8  (only if producing videos)
    BLOCKED.md                      only if blocked
```

ID formats (MUST):

| Thing | Format | Example |
|---|---|---|
| Outlier | `O` + 3 digits | `O007` |
| Hook template | `H` + 3 digits | `H012` |
| Structure template | `T` + 3 digits | `T004` |
| Month slot (video) | `V` + 2 digits | `V09` |
| Client Bank items | `K` knowledge, `S` story, `P` proof, `F` FAQ, `M` myth/opinion, `X` offer + number | `K3`, `S1`, `P2`, `F4`, `M1`, `X1` |

---

## Phase 0: Intake

**Goal:** a complete `00_client_profile.json`, including the Client Bank.
**Input:** whatever the human gave you (notes, website, past posts, an interview).

### Steps

1. Create `00_client_profile.json` from the schema below.
2. Fill in every field you can from the materials you were given. Copy facts exactly. Don't embellish.
3. For every field that's still empty, ask the human the matching [intake question](#intake-questions). Ask all
   missing questions in one message.
4. Write the client's **voice notes**: 5 to 10 words or phrases they actually use, 3 to 5 they never use, and a
   reading level (e.g. "plain, 8th grade, short sentences"). If you have samples of their writing or speech, take these
   from the samples.
5. Check the profile against the gate.

### `00_client_profile.json` schema

```json
{
  "client_name": "Maya Ortiz",
  "handle": "@example",
  "platform": "instagram",
  "niche": "dog training",
  "sub_niches": ["crate training", "potty training", "leash walking", "puppy biting", "separation anxiety"],
  "occupation_title": "certified dog trainer",
  "city": "Austin, TX",
  "audience": "first-time puppy owners, ages 25-40",
  "primary_goal": "leads",
  "account_status": "new",
  "followers": 640,
  "average_views_last_20": 900,
  "posting_level": "moderate",
  "posts_per_week": null,
  "is_founder_building_in_public": false,
  "offers": [{"id": "X1", "name": "6-Week Puppy Foundations", "type": "paid_offer", "link": "https://example.com/program"}],
  "freebie": {"name": "Puppy's First 30 Days Checklist", "link": "https://example.com/checklist", "manychat_keyword": "PUPPY"},
  "voice": {"uses": ["here's the thing", "tiny wins", "pup"], "never_uses": ["fur baby", "hack"], "reading_level": "plain, short sentences"},
  "editing_style": {"colors": ["#1F3A5F", "#F4EBDD", "#E07A3F"], "primary_font": "Bold sans", "secondary_font": "Clean sans", "accent_font": "Handwritten", "visual_types": ["screen text callouts", "B-roll of dogs", "before/after clips"]},
  "credit_budget": {"scrapecreators": 300, "supadata": 20},
  "openrouter_model": "<an OpenRouter model id chosen by the human>",
  "allow_long_transcription": false,
  "produce_videos": false,
  "client_bank": {
    "knowledge": [{"id": "K1", "sub_niche": "crate training", "text": "3-step crate intro: meals in crate door open for 3 days; then close door 1 minute while eating; then leave room 5 minutes once calm."}],
    "stories":   [{"id": "S1", "story_type": "loss", "text": "First foster dog Biscuit chewed a door frame because I gave him the whole house on day one.", "assets": ["photo of chewed door frame"]}],
    "proof":     [{"id": "P1", "type": "client_result", "text": "Client Jess: puppy went from crying 2 hours in the crate to sleeping through the night in 9 days.", "permission_to_share": true}],
    "faqs":      [{"id": "F1", "text": "Should the crate be in my bedroom?"}],
    "myths":     [{"id": "M1", "text": "Myth: letting a puppy cry it out builds independence. Client's view: it builds panic."}]
  }
}
```

Field rules:

| Field | Rule |
|---|---|
| `sub_niches` | 5 to 7 items, each 1 to 4 words |
| `primary_goal` | one of `views`, `followers`, `leads` |
| `account_status` | `new` = has never had a video reach 5× its average views, or has fewer than 30 posts (playbook default). Otherwise `established` |
| `posting_level` | `easy` = 3/week, `moderate` = 5/week, `hard` = 7/week (playbook default; the videos name the levels but not the numbers). `posts_per_week` overrides it if set |
| `stories[].story_type` | from [A3](#a3-story-types) |
| `proof[].permission_to_share` | MUST be `true` to use a client's name or result. If `false`, describe the result without the name |
| `credit_budget` | max credits per service for this run. If a service's budget is missing, use 50% of its remaining balance |
| `openrouter_model` | set by the human. If it's missing and you need OpenRouter, ask. Don't pick one yourself |
| `produce_videos` | `true` only if the human wants Phase 8 (Hypit) |

### Intake questions

Ask these, in plain words, for anything that's missing:

1. What's your broad industry, and what 5 to 7 topics inside it do you want to be known for?
2. What's your job title, and your city if you serve people locally?
3. Who exactly do you help (age, situation, problem)?
4. What do you sell (name, price range, link)? Do you have a free resource to give away?
5. Is your main goal right now more views, more followers or more leads?
6. How many followers do you have, and roughly how many views does a normal video get?
7. How many videos a week can you realistically film: 3, 5 or 7?
8. List 10 things you know that your audience gets wrong or doesn't know. Be specific: steps, numbers, rules.
9. Tell me 5 stories: how you started, a big win, a painful mistake or loss, a lesson that changed how you work,
   and a before/after (yours or a client's).
10. What results can you prove (numbers, testimonials, screenshots)? Do you have permission to share client names?
11. What do people ask you all the time?
12. What common advice in your industry do you disagree with, and why?
13. Paste 2 or 3 captions, emails or transcripts written or spoken by you, so I can match your voice.

### Gate 0

- [ ] `niche`, 5 to 7 `sub_niches`, `occupation_title`, `audience`, `primary_goal`, `account_status`, `followers` and `posting_level` are all filled
- [ ] The Client Bank has **≥ 10 knowledge items, ≥ 5 stories (covering ≥ 3 story types) and ≥ 1 proof item** (playbook default)
- [ ] `voice` is filled
- [ ] Every bank item has an ID

If the bank minimums aren't met, you MAY continue with Phases 1 to 4 (they don't need the bank). In Phase 5, insert
`[[NEEDS CLIENT INPUT]]` markers instead of inventing anything, and list the gaps in `06_qa_report.md`.

---

## Phase 1: Plan the month

**Goal:** `01_month_plan.json`, a list of every video slot for the month, each labeled with its week, bucket,
funnel stage, content type and CTA type.

### Steps

1. **Count the videos.** `N = posts_per_week × number_of_posting_weeks_in_the_month` (use 4 weeks unless the human says otherwise).
2. **Pick the weekly pattern** from the follower tier. The counts come from the videos; the order is a playbook default,
   so that dropping slots from the end keeps the mix balanced.

   | Tier (`followers`) | Weekly pattern: use the first `posts_per_week` entries, in order |
   |---|---|
   | 0 to 999 | 1 `tofu/follow` · 2 `mofu/follow` · 3 `bofu/follow` · 4 `tofu/freebie` · 5 `mofu/follow` · 6 `tofu/follow` · 7 `bofu/follow` |
   | 1,000 to 9,999 | 1 `tofu/follow` · 2 `mofu/follow` · 3 `bofu/follow` · 4 `tofu/follow (double_down)` · 5 `bofu/paid_offer` · 6 `tofu/freebie` · 7 `bofu/follow` |
   | 10,000+ | 1 `tofu/follow` · 2 `mofu/follow` · 3 `bofu/paid_offer` · 4 `tofu/follow (double_down)` · 5 `bofu/paid_offer` · 6 `tofu/freebie` · 7 `bofu/follow` |

   - If `primary_goal` is `leads` and the tier's pattern has no freebie in the first `posts_per_week` entries, change the
     last `tofu/follow` CTA to `tofu/freebie`.
   - A slot marked `(double_down)` is only a double down if the account is `established`. Otherwise it becomes a normal slot.
3. **Assign the content type** to each slot:
   - `tofu` → `educational` (broad and simple; easy structures are allowed)
   - `mofu` → `storytelling`
   - `bofu` → alternate within the month: the first BOFU slot is `educational` (in-depth), the next is `authority`
     (proof or a transformation), then educational, and so on (playbook default)
4. **Assign buckets.**
   - `established`: `double_down = round(0.20 × N)` and `experiment = max(1, round(0.10 × N))`. The rest are `proven` (the **70/20/10** rule).
     Put double downs on the `(double_down)` slots first, then on other TOFU slots.
   - `new`: `experiment = max(1, round(0.10 × N))`. The rest are `proven` (the **90/10** rule).
   - Put experiments on the last slot of the weeks, starting with the last week.
5. **Founders building in public** (`is_founder_building_in_public: true`): additionally make sure **25 to 50% of slots are
   journey/documentation content** (series episodes, metric updates, cost breakdowns, "what I'd do differently"). Relabel
   `mofu` slots first, then `tofu`.
6. **Assign topics** so sub-niches rotate evenly: slot 1 gets sub-niche 1, slot 2 gets sub-niche 2, and so on, wrapping around.
7. Leave `angle`, `delivery` and `format` empty for now. Phase 5 fills them.
8. Write the file.

### `01_month_plan.json` schema

```json
{
  "month": "2026-11",
  "N": 20,
  "rule": "90/10",
  "slots": [
    {"slot_id": "V01", "week": 1, "post_day": "Mon", "bucket": "proven", "funnel": "tofu", "content_type": "educational",
     "cta_type": "follow", "topic": "crate training", "angle": null, "delivery": null, "format": null}
  ]
}
```

### Gate 1

- [ ] There are exactly `N` slots, with IDs `V01`…`VNN`
- [ ] Every week has at least one `tofu`, one `mofu` and one `bofu` slot (as long as `posts_per_week` ≥ 3)
- [ ] The bucket counts match the 70/20/10 or 90/10 math above
- [ ] The month contains educational, storytelling *and* authority slots
- [ ] Every value is from the closed vocabularies

---

## Phase 2: Research outliers

**Goal:** `02_outliers.json`, a bank of verified outliers large enough for the month.
**Quota (playbook default):** at least `2 × proven_slots` outliers in total, **and** at least 2 per sub-niche, **and** at
least 8 that clearly use a `storytelling` delivery (for the MOFU slots).

### Step 2.1: Build the keyword list → `02_keywords.json`

1. Add the niche, every sub-niche and the occupation title.
2. For each of those, add **2 variations** people would actually type (synonyms, plural/singular, the audience plus the
   problem). Example for "crate training": "crate training puppy", "puppy crying in crate".
3. You should end up with at least 15 keywords.

```json
{"keywords": [{"kw": "crate training", "source": "sub_niche"}, {"kw": "puppy crying in crate", "source": "variation"}]}
```

### Step 2.2: Choose the research mode, and record it in `02_research_log.md`

Instagram is the preferred platform: it's the hardest to go viral on, so outliers there are strong. Use the first mode
you have access to:

- **Mode S (preferred)**: `SCRAPECREATORS_API_KEY` is set. Fully automated Instagram research.
- **Mode A**: a browser logged in to an Instagram research account.
- **Mode B**: the human gives you reel URLs. Get each one's stats with ScrapeCreators `/v1/instagram/post` if you have
  a key; otherwise ask the human for views and follower counts.
- **Mode C**: no Instagram access. Research YouTube Shorts through the Supadata API. Record in the log: "Mode C used;
  outliers are from YouTube Shorts, not Instagram."

### Step 2.3, Mode S: ScrapeCreators (automated Instagram)

This is the automated version of "find creators in your niche, sort their reels by most viewed, and keep the 5x ones."

1. **Balance check:** `GET /v1/account/credit-balance`. Record `credits_remaining` in `02_research_log.md`.
2. **Find creators through keyword search.** For each keyword in `02_keywords.json`:
   1. Call `GET /v2/instagram/reels/search?query=<kw>&date_posted=last-year&page=1`. Fetch pages 2 and 3 as well if page 1
      returned 10 or more reels (playbook default: at most 3 pages per keyword).
   2. Keep a reel only if `is_paid_partnership` is false, `is_ad` is false, and `owner.follower_count` is between
      **1,000 and 500,000** (playbook default: below 1,000 the ratios are noise).
   3. Add each kept reel's `owner.username` and `owner.follower_count` to a **creator list**, de-duplicated by username.
      Record which keyword found them.
3. **Rank the creators.** Sort the creator list by how many keywords found them (most first), then by follower count
   (smallest first). Small accounts with big hits are what you want.
4. **Pull each creator's reels, the "sort by most viewed" step.** For each creator, in ranked order, until the quota is met
   or the budget runs out:
   1. Call `GET /v1/instagram/user/reels?handle=<username>&trim=true`. Fetch one more page with `max_id` (playbook default:
      2 pages per creator).
   2. For every reel: `views = play_count` (or `ig_play_count`), `creator_followers` = the creator's `follower_count`.
      If you don't have a follower count, call `GET /v1/instagram/profile?handle=<username>&cache_max_age=30d` and use
      `data.user.edge_followed_by.count`.
   3. Run every reel through the [candidate procedure](#candidate-procedure) with `found_via = "account"`.
5. **Reels from search results** also count. Run each kept search reel through `GET /v1/instagram/post?url=<url>&trim=true&cache_max_age=30d`
   to get `video_play_count`, but **only** if the quota isn't yet met after step 4, because this costs 1 credit per reel.
   Use `found_via = "keyword"`.
6. **Log credits** after every 25 calls: running total of `credits_charged`, plus the latest `credits_remaining`.

Budget math: a typical month (20 slots, 14 proven, quota 28 outliers) costs about 15 keywords × 1 to 3 search pages,
plus 20 to 40 creators × 2 reel pages, so **roughly 60 to 130 credits**, plus 1 credit per transcript in Phase 3
(playbook estimate; check the real cost against `credits_charged` as you go).

### Step 2.3, Mode A: Instagram research

Do these sub-steps in order. Each time you find a candidate video, run the [candidate procedure](#candidate-procedure).

1. **Reset the research account's algorithm** (only at the first run for a client): Profile → ☰ menu →
   Content preferences → Reset suggested content → Next → Reset suggested content → Reset suggested content.
2. **Keyword research.** For every keyword in `02_keywords.json`: Explore → search bar → type the keyword → open the
   Reels results → scroll until you've checked at least 30 reels or the results run out. Run each reel through the candidate procedure.
3. **Account research.** Collect niche accounts with these four methods. Keep an account only if its content is the kind the client would post:
   1. Search a keyword → **Accounts** tab → open the top accounts.
   2. From any good reel you found → tap the creator's profile picture.
   3. Open a kept account → tap **Follow** → browse **Suggested accounts**.
   4. Open a kept account → open its **Following** list → look for niche accounts.

   For each kept account: open the Reels tab → sort by **Most viewed** (on desktop, the Sort Feed Chrome extension:
   All items → Views → export CSV) → run the top 10 reels through the candidate procedure.
4. **Reels tab sweep.** After steps 2 and 3, the research account's feed is now trained on the niche. Open the **Reels**
   tab and scroll through at least 50 reels, running every in-niche reel through the candidate procedure. Don't skip this
   step: it surfaces outliers that searches miss.

### Step 2.3, Mode B: Human-supplied list

For every URL you're given, run the candidate procedure using the follower count supplied. If a follower count is
missing, ask for it. Don't guess.

### Step 2.3, Mode C: YouTube Shorts via Supadata

1. For each keyword: `GET /youtube/search?query=<kw>&type=video&duration=short&uploadDate=year&sortBy=views&limit=50`.
2. Keep results with `duration ≤ 180` seconds.
3. For each **distinct** `channel.id`: `GET /youtube/channel?id=<id>` → `subscriberCount`. Cache these, and never look up
   the same channel twice.
4. Run the candidate procedure with `views = viewCount` and `creator_followers = subscriberCount`.
5. Stop when the quota is met or the credit budget is reached.

### Candidate procedure

For each candidate video:

1. Record `url`, `creator_handle`, `views`, `creator_followers`, `posted_date` and `sponsored` (true/false).
2. Compute `outlier_ratio = views / creator_followers`, rounded to 1 decimal place.
3. Apply the [5x test](#the-5x-test). If it fails, discard the video (don't record it).
4. Decide `in_niche`: `true` if the topic belongs to the client's niche. `false` means it's a **cross-niche** candidate:
   keep it only if its hook or structure pattern clearly works in any niche (e.g. "Is it possible to…?", "Three levels of…",
   "Smart vs dumb…", good/better/best ladders, "[time] ago I…").
5. Write a one-line `why_saved`: which element looks reusable (hook, structure or both).
6. Add it to `02_outliers.json` with the next free `O###` ID.

```json
{"outliers": [{
  "id": "O001", "url": "https://www.instagram.com/reel/XXXX/", "platform": "instagram",
  "creator_handle": "@somecreator", "views": 126000, "creator_followers": 18000, "outlier_ratio": 7.0,
  "posted_date": "2026-08-14", "sponsored": false, "in_niche": true, "sub_niche": "crate training",
  "found_via": "keyword", "why_saved": "hook + structure", "transcribed": false
}]}
```

`found_via` is one of `keyword`, `account`, `suggested`, `following`, `reels_tab`, `human_list` or `youtube_search`.

### Gate 2

- [ ] The quota is met (total, per sub-niche and storytelling count), or BLOCKED.md explains the shortfall
- [ ] Every outlier passed the 5x test, and its ratio is recorded
- [ ] No duplicate URLs
- [ ] Credits used are recorded in `02_research_log.md`, and the budget hasn't been exceeded

---

## Phase 3: Extract elements

**Goal:** one `03_elements/<outlier_id>.json` per outlier you'll use, breaking the video into its seven factors.
**Which outliers to extract:** all of them if credits allow. Otherwise prioritize (1) storytelling outliers, (2) outliers
whose `why_saved` includes "structure", and (3) the highest `outlier_ratio`.

### Step 3.1: Get the raw material

1. **Transcript.** Use the first option that works, and record which one in `transcript_source`:
   - **Instagram + ScrapeCreators:** `GET /v2/instagram/media/transcript?url=<url>&cache_max_age=30d`. Save
     `transcripts[0].transcript_with_timestamp` as `transcript` (convert each `start` and `end` from seconds to
     milliseconds: `offset = start × 1000`, `duration = (end − start) × 1000`). If timestamps are `null`, save
     `transcripts[0].text` as a single chunk with `offset: 0` and set `timestamps: false`. Skip reels longer than 120 seconds.
     `transcript_source: "scrapecreators"`.
   - **Any platform + Supadata:** `GET /transcript?url=<url>&mode=auto&text=false`, then save the `content` array (text and
     millisecond offsets). `transcript_source: "supadata"`.
   - **Neither works:** ask the human to paste a transcript. `transcript_source: "human"`.
2. **Stats and cover.** In Mode S you already have the stats. Get the cover image from `thumbnail_src` (ScrapeCreators) or
   `media.thumbnailUrl` (Supadata `GET /metadata?url=<url>`). Keep the caption text too.
3. **Cover or first frame:** open the cover image (or watch the first 3 seconds if you can view video).

### Step 3.2: Fill in the seven factors, exactly as follows

| # | Field | How to fill it (no guessing) |
|---|---|---|
| 1 | `topic` | The sub-niche it maps to, or `cross_niche` |
| 2a | `verbal_hook` | Take every transcript chunk with `offset < 3000`. Then keep adding words until the end of that sentence. Copy them **exactly**. If `timestamps: false`, use the first sentence of the transcript, up to 25 words |
| 2b | `written_hook` | The on-screen text visible in the first 3 seconds, or the text on the cover image. Copy it exactly. If you can't see it, use `null` with `confidence: "unknown"`. Don't use the caption as a substitute |
| 2c | `visual_hook` | One sentence describing what *happens* on screen in the first 3 seconds (an action, prop, location or edit). If you can only see the cover, describe the cover and set `confidence: "cover_only"` |
| 3 | `value` | `summary`: one sentence on what the viewer learns or sees. `measurable`: true/false using the [measurable value test](#the-measurable-value-test). `source_type`: `personal_experience`, `outside_source` or `mixed` |
| 4 | `angle`, `delivery`, `story_type` | From [A1](#a1-angles), [A2](#a2-delivery) and [A3](#a3-story-types). `story_type` is only filled when `delivery = storytelling` |
| 4b | `beats` | Split the transcript into sentences. Label every sentence with **one** [beat label](#a8-beat-labels). Merge consecutive sentences that have the same label |
| 4c | `complexity` | `easy` if one sentence shape repeats **3 or more times** with only nouns or numbers changing. Otherwise `complex` |
| 5 | `cta` | `type` from [A6](#a6-cta-types-and-lines), plus the exact CTA words |
| 6 | `format` | From [A5](#a5-formats). If you can't see the video, use `unknown` |
| 7 | `editing_notes` | Up to 3 observations (e.g. "big yellow captions", "zoom on every step"). `null` if you can't see it |
| — | `content_type`, `funnel` | From [A4](#a4-content-types) and [A7](#a7-funnel-stages), using: broad and simple → `tofu`; personal story → `mofu`; in-depth teaching, proof or offer → `bofu` |

### `03_elements/O001.json` schema

```json
{
  "outlier_id": "O001",
  "transcript_source": "supadata",
  "duration_s": 41,
  "topic": "crate training",
  "verbal_hook": {"text": "<exact words>", "end_ms": 3400},
  "written_hook": {"text": "<exact on-screen text>", "confidence": "seen"},
  "visual_hook": {"text": "Creator stacks three glass containers on the counter.", "confidence": "seen"},
  "value": {"summary": "...", "measurable": true, "source_type": "personal_experience"},
  "angle": "tutorial", "delivery": "educational", "story_type": null,
  "beats": [{"label": "HOOK", "text": "..."}, {"label": "NAME_METHOD", "text": "..."}, {"label": "STEP", "text": "..."}],
  "complexity": "easy",
  "cta": {"type": "freebie", "text": "<exact words>"},
  "format": "visual_prop",
  "editing_notes": ["captions centered, two colors", "item labels pop in"],
  "content_type": "educational", "funnel": "tofu",
  "transcript": [{"text": "...", "offset": 0, "duration": 1800}]
}
```

`confidence` is one of `seen`, `cover_only` or `unknown`.

### Gate 3

- [ ] Every extracted outlier has all seven factors filled (or an explicit `null` or `unknown` with a confidence value)
- [ ] `verbal_hook.text` is copied exactly from the transcript
- [ ] Every sentence of the transcript is covered by exactly one beat
- [ ] Every label is from the closed vocabularies

---

## Phase 4: Templatize

**Goal:** two template banks: `04_hook_templates.json` (verbal, written and visual hook madlibs) and
`04_structure_templates.json` (full-script madlibs). A template MUST read like a fill-in-the-blank form that works in
**any** niche.

### Step 4.1: The templatizing procedure (use it for every hook and every structure)

1. **Copy** the exact source text (a hook, or the beat list for a structure).
2. **Mark the frame words.** Keep words that create the *pattern*: question openers ("Is it possible to"), time
   markers ("[N] days ago"), list markers ("Step one", "Number two"), contrast words ("but", "instead", "versus"), reveal
   phrases ("here's what happened", "here's the"), and the CTA mechanics ("comment", "follow").
3. **Mark the content words.** Everything specific to the source creator's niche or life: nouns, verbs of the activity,
   numbers that describe *their* result, names, brands, places, products and claims.
4. **Replace each run of content words with one slot** written as `{{NAME:TYPE}}`:
   - `NAME` is UPPER_SNAKE_CASE, describes the role, and is unique within the template (e.g. `{{GOAL:OUTCOME}}`, `{{STEP_1:STEP_ACTION}}`)
   - `TYPE` is one of the [slot types](#a9-slot-types)
5. **Keep structural numbers** that define the pattern ("three levels", "Step one/two/three") as frame words, or turn them
   into `{{N:NUMBER}}` if the count can change. Repeating parts become a block:
   `[REPEAT {{N:NUMBER}} times] … [/REPEAT]`.
6. **Write a fill rule for every slot**: what goes there, its length limit, and which Client Bank field it comes from
   (`knowledge`, `stories`, `proof`, `offers`, `freebie`, `profile` or `any`).
7. **Run the neutrality check.** Read the template with every slot hidden. It MUST NOT reveal the source niche, and it
   MUST NOT contain any content word from step 3. If it does, go back to step 4.
8. **Name the pattern** in plain words (e.g. "Costly habit → named rule → 3 steps → week example → recap → freebie").
9. **Record** the source outlier ID(s) and URL(s).

### Step 4.2: Hook templates → `04_hook_templates.json`

- Make **one verbal hook template per outlier** (from `verbal_hook`), **one written hook template** (from `written_hook`,
  if not null), and **one visual hook template** (from `visual_hook`).
- A visual hook template describes a filmable action with slots, e.g. "Pulls {{N:NUMBER}} {{ITEM:ITEM}}s out of a bag one at a time."
- Tag every hook template with the `angle` it suits.

```json
{"hook_templates": [{
  "id": "H001", "hook_type": "verbal", "angle": "tutorial", "source_outliers": ["O001"],
  "source_urls": ["https://www.instagram.com/reel/XXXX/"],
  "template": "I wasted {{COST:COST}} on {{BAD_HABIT:MISTAKE}} until I tried this.",
  "slots": [
    {"name": "COST", "type": "COST", "rule": "a real cost from the client bank: money, time or sleep, with a unit", "from": "stories"},
    {"name": "BAD_HABIT", "type": "MISTAKE", "rule": "the common costly habit the audience has, 2-6 words", "from": "knowledge"}
  ],
  "pattern": "Personal cost + 'until I tried this' curiosity gap",
  "max_words_filled": 15
}]}
```

Length limits for filled hooks (playbook default): **verbal ≤ 15 words** (about 3 seconds spoken), **written ≤ 7 words**,
**visual = one action that can be filmed in under 3 seconds**.

### Step 4.3: Structure templates → `04_structure_templates.json`

1. Take the outlier's `beats` list.
2. Templatize **each beat's text** with the procedure in 4.1.
3. Keep the beats in the same order. A template is the ordered list of beats, each with its templated line or lines.
4. Copy `delivery`, `angle`, `story_type`, `complexity` and the `cta.type` from the element file.
5. Add `target_words`: the source transcript's word count ±20%.

```json
{"structure_templates": [{
  "id": "T001", "source_outliers": ["O001"], "source_urls": ["https://www.instagram.com/reel/XXXX/"],
  "delivery": "educational", "angle": "tutorial", "story_type": null, "complexity": "easy",
  "pattern": "Costly habit → named rule → N steps → week example → recap → freebie",
  "target_words": [78, 118],
  "beats": [
    {"label": "HOOK", "line": "<<use a hook stack>>"},
    {"label": "NAME_METHOD", "line": "Here's the {{N:NUMBER}}-{{UNIT:ITEM}} rule."},
    {"label": "STEP", "line": "[REPEAT {{N}} times] {{UNIT}} {{ORDINAL}}: {{STEP_ACTION:STEP_ACTION}}, {{STEP_EXAMPLE:EXAMPLE}}. [/REPEAT]"},
    {"label": "EXAMPLE", "line": "{{SITUATION_1:EXAMPLE}}: {{APPLY_1:EXAMPLE}}. {{SITUATION_2:EXAMPLE}}: {{APPLY_2:EXAMPLE}}."},
    {"label": "RECAP", "line": "That's it: {{N}} {{UNIT}}s, {{TIME_COST:TIMEFRAME}}."},
    {"label": "CTA", "line": "<<use the slot's CTA>>"}
  ],
  "slots": [
    {"name": "STEP_ACTION", "type": "STEP_ACTION", "rule": "one concrete action, imperative, ≤ 14 words", "from": "knowledge"},
    {"name": "STEP_EXAMPLE", "type": "EXAMPLE", "rule": "first-person detail that shows the step, ≤ 12 words", "from": "knowledge|stories"}
  ]
}]}
```

Note: the HOOK and CTA beats are always placeholders. The hook comes from the hook stack and the CTA from the month
plan (Phase 5). This lets any structure combine with any hook stack.

### Step 4.4: Bank minimums (playbook default)

- Hook templates: at least `proven_slots` of each hook type (verbal, written, visual)
- Structure templates: at least 6, including **≥ 2 storytelling** and **≥ 2 complex**
- Every one of the 7 angles is covered by at least one hook template, if your outliers allow it

### Gate 4

- [ ] Every template passes the neutrality check (it doesn't reveal the source niche)
- [ ] Every slot has a `type`, a `rule` and a `from`
- [ ] Every template lists its source outliers and URLs
- [ ] Bank minimums are met, or the shortfall is noted in `06_qa_report.md`

---

## Phase 5: Fill

**Goal:** one finished script file per slot in `05_scripts/`, plus `05_ideation.csv`.
Do these steps **for each slot, in slot order**.

### Step 5.1: Choose the angle and delivery

- `content_type = storytelling` → `delivery = storytelling`, and pick a `story_type` that has a matching story in the bank.
  Rotate story types across the month.
- `content_type = authority` → `angle = transformation`, using a `proof` item.
- `content_type = educational` → rotate through the 7 angles so none repeats until all have been used, skipping
  angles that have no hook template.
- `bucket = double_down` → skip ahead to [Phase 7, step 7.3](#step-73-double-down-recipe).

### Step 5.2: Pick the Client Bank material (the value)

1. Filter the bank to items whose `sub_niche` matches the slot's `topic` (stories and proof can be any sub-niche).
2. Educational → pick 1 knowledge item. Storytelling → pick 1 story (plus knowledge for the lesson). Authority → pick
   1 proof item (plus knowledge for the "how").
3. Never reuse the same bank item as the **main** value twice in one month (playbook default).
4. Write a one-line `value_statement` and run the [measurable value test](#the-measurable-value-test). If it fails, pick
   a more specific item or add `[[NEEDS CLIENT INPUT: specific number/step for <topic>]]`.

### Step 5.3: Build the hook stack

1. Pick **one verbal, one written and one visual hook template** whose `angle` matches the slot. They MUST come from
   **at least 2 different source outliers**.
2. Fill each template's slots with this slot's topic and bank material, in the client's voice.
3. Check the length limits (verbal ≤ 15 words, written ≤ 7 words, visual = one filmable action).
4. All three hooks MUST promise the **same thing** the value delivers. If a hook promises something the script doesn't
   deliver, rewrite the hook.

### Step 5.4: Pick and fill the structure template

1. Pick a structure template with the matching `delivery`. Prefer a matching `angle` and `story_type`.
   - TOFU MAY use `easy` structures.
   - MOFU and BOFU SHOULD use `complex` structures (they convert better to followers and leads).
   - Don't use the same structure template more than 3 times in a month (playbook default).
2. Put the verbal hook into the HOOK beat.
3. Fill every slot, beat by beat, following each slot's `rule` and `from`:
   - Write in the client's voice (`voice.uses`). Never use `voice.never_uses`.
   - Use **only** facts from the bank items you picked, and note their IDs.
   - Fill `[REPEAT]` blocks with exactly `N` items.
   - Keep frame words exactly. You MAY change frame words only for grammar (tense, plural, a/an).
4. Write the CTA beat from the slot's `cta_type`, using the [CTA lines](#a6-cta-types-and-lines).
5. Count the words. They MUST be within the template's `target_words` range. If not, trim or expand the
   STEP/EXAMPLE beats, never the hook or CTA.

### Step 5.5: Choose the format

- Storytelling → `voiceover`, `shot_angle_change` or `audio_broll_text`.
- Series episodes → `shot_angle_change`, `visual_prop`, `voiceover` or `setting_change`.
- Comparison or do-vs-don't → prefer `clone` or `talking_back_forth`.
- Otherwise pick any format from [A5](#a5-formats) **except `talking_head`**, which is only allowed for `experiment` slots.
- If the format changes the script (`clone` and `talking_back_forth` need two voices), label each line with
  `A:` / `B:`. `reaction` must name the clip to react to.

### Step 5.6: Write the script file `05_scripts/<slot_id>.md`, using exactly this layout

```markdown
# V01: <working title>

| Field | Value |
|---|---|
| Week / day | 1 / Mon |
| Bucket | proven |
| Funnel / content type | tofu / educational |
| Topic | crate training |
| Angle / delivery / story type | tutorial / educational / — |
| Format | visual_prop |
| CTA | freebie, keyword PUPPY |
| Structure template | T001 (from O001) |
| Hook templates | verbal H001 (O001), written H014 (O006), visual H027 (O011) |
| Bank items used | K1, S2 |
| Word count | 117 (target 78–118) |

## Hook stack
- **Verbal (heard):** ...
- **Written (on screen, first 3 s):** ...
- **Visual (first 3 s):** ...

## Script
Each line has the words to say (LINE), what to film (SHOT, the "red" notes) and editor notes (EDIT, the "green" notes).

1. LINE: ...
   SHOT: ...
   EDIT: ...
2. LINE: ...
   SHOT: ...
   EDIT: ...

## Caption
<written hook>

<CTA line>

#<niche> #<audience> #<subtopic>

## Needs from client
- none   (or a list of every [[NEEDS CLIENT INPUT]] marker in this script)
```

Rules for the script section:

- **One LINE per sentence.**
- Give a SHOT whenever the picture changes, and on every line for the `shot_angle_change` and `setting_change` formats.
- Give an EDIT whenever text, a graphic, a past photo or clip, a zoom or a sound is needed. Storytelling scripts SHOULD
  use the client's real past photos or video from the time of the story (from `stories[].assets`). If there's none,
  add `[[NEEDS CLIENT INPUT: photo or clip from <moment>]]`.
- Storytelling: add `EDIT: emotional background music under the whole video` to line 1.
- Apply `editing_style` (colors, fonts, visual types) in the EDIT notes the first time each is used.

**Caption rules:** line 1 is the written hook, then a blank line, then the CTA line, then a blank line, then 3 to 5 hashtags
covering the niche, the target audience and the sub-topic. Hashtags work as keywords; don't promise reach.

### Step 5.7: Add a row to `05_ideation.csv`

Use exactly this header:

```
slot_id,week,day,bucket,funnel,content_type,topic,angle,delivery,story_type,format,cta_type,verbal_hook,written_hook,visual_hook,value_statement,structure_template,hook_templates,bank_items,word_count,needs_client_input
```

### Gate 5

- [ ] Every slot in `01_month_plan.json` has a script file and an ideation row
- [ ] Every script lists its template IDs, source outliers and bank items
- [ ] No script contains a fact that isn't traceable to a bank item or credited source

---

## Phase 6: Quality gate

**Goal:** `06_qa_report.md`. Every script MUST pass every check. If a script fails, fix it and re-check it, up to 3
attempts. If it still fails after that, mark it `FAILED` with the reason, and don't hand it over as ready.

| ID | Check | How to verify | Pass when |
|---|---|---|---|
| Q1 | Hook stack complete | Read the hook stack section | All three hooks are present and within the length limits |
| Q2 | Hook diversity | Look at the hook template sources | At least 2 different source outliers |
| Q3 | Hook ↔ value match | Compare the hooks with the value | Every hook promises what the body delivers |
| Q4 | Measurable value | [Measurable value test](#the-measurable-value-test) | All 3 conditions are true |
| <a id="check-q5-overlap"></a>Q5 | No copied content | Lowercase both texts, strip punctuation, split into words, then compare every 6-word sequence in the script body (all LINEs except line 1) against every 6-word sequence in each source transcript used | 0 shared 6-word sequences |
| Q6 | No invented facts | Check every claim about the client against the bank items listed | Every claim maps to a listed ID, or is a `[[NEEDS CLIENT INPUT]]` marker |
| Q7 | Sources credited | Look for facts from outside sources | Each one is credited out loud in a LINE |
| Q8 | CTA matches plan | Compare with the slot's `cta_type` | It matches, and a freebie CTA uses the client's ManyChat keyword |
| Q9 | Vocabulary | Every label | Every label is from Appendix A |
| Q10 | Length | Word count | Within the template's `target_words` |
| Q11 | Voice | Compare with `voice` | No `never_uses` words, and at least 1 `uses` phrase in the month's every-other script (playbook default) |
| Q12 | Integrity | Read it as the audience | No trend, meme or fluff; it isn't misleading; no other creator is named or imitated |
| Q13 | Month mix | Look across all scripts | All three content types are present, every week has TOFU, MOFU and BOFU, and the bucket counts match Phase 1 |

`06_qa_report.md` layout:

```markdown
# QA report: <client> <YYYY-MM>
Summary: 19/20 PASS, 1 FAILED
Credits used: 14 (balance before 35, after 21)

| Slot | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 | Q9 | Q10 | Q11 | Q12 | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V01 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PASS | |

## Needs from client (all scripts)
- V04: photo of the chewed door frame (S1)

## Month mix (Q13)
...
```

### Gate 6 (final)

- [ ] Every script is PASS, or FAILED with a reason
- [ ] Q13 passes
- [ ] Every `[[NEEDS CLIENT INPUT]]` marker is listed once in the report

When Gate 6 passes, the run is complete. Hand the month folder to the human.

---

## Phase 7: Monthly review and doubling down

Run this **only** if you have the client's post-level analytics (views per post). On Instagram, the Edits app shows
best- and worst-performing videos. Otherwise the human pastes the numbers.

### Step 7.1: Study the top 5 and bottom 5

1. Rank last month's posts by views and take the top 5 and bottom 5.
2. Break each into the seven factors (as in Phase 3, using the client's own scripts from `05_scripts/`).
3. For each factor, note what the top 5 share that the bottom 5 don't.
4. Write `07_review.json`:

```json
{"top": [{"slot_id": "V03", "views": 9100, "ratio_vs_avg": 10.1}], "bottom": [{"slot_id": "V11", "views": 300}],
 "patterns": [{"factor": "format", "finding": "4 of top 5 used clone; 0 of bottom 5"}],
 "own_outliers": ["V03", "V07"], "next_month_changes": ["Use clone format on 3 more TOFU slots"]}
```

### Step 7.2: Define the client's own outliers

`own_outlier` if `views ≥ 3 × average_views_last_20` (playbook default; the videos' example used about 10×: a 1K average
against 10K+). If any own outliers exist, set `account_status = established` for next month.

### Step 7.3: Double-down recipe

For every `double_down` slot next month, take one own outlier and apply **exactly one** variant:

| Variant | Keep | Change |
|---|---|---|
| **A** | Everything | Make one small change to the **value** (the next tip, a different example, a different step) |
| **B** | The **format and structure** | Everything else: new topic, new hooks, new value |
| **C** | Everything | **Only the format** (e.g. a talking piece becomes a clone or voiceover) |

Record the variant in the script header (`Bucket: double_down (V03, variant C)`). Rule 2 (no copying) doesn't apply to the
client's own past script. Rule 1 (no invented facts) still does.

### Step 7.4: Brand check

If the client's views swing wildly (the top post has more than 20× the median views; playbook default) **and** the month
had little storytelling or authority content, add 2 extra MOFU storytelling slots next month and note why in `07_review.json`.

---

## Phase 8: Produce videos with Hypit (optional)

Run this **only** if `produce_videos` is `true` **and** a human has approved the scripts (PASS in `06_qa_report.md`
plus a human sign-off). [Hypit](https://github.com/hypit-ai/hypit) is an open-source skill that lets coding agents
(Claude Code, Codex) build edited short-form videos from a script, a template or a reference clip. The setup below
comes from Hypit's README and hasn't been tested in this repo yet.

### Step 8.1: Set up once per machine

1. Check `node --version` is **22.15 or higher**.
2. Install the skill: `npx skills add hypit-ai/hypit -g`
3. Start a coding-agent session in `08_production/` and invoke `/hypit`. On first use it checks for its executable and
   asks for the model credentials the video needs. Captions and motion graphics can render locally with no paid model.
   AI footage, voice and images need a provider Hypit supports. Its README names HypiHub as the recommended hosted
   option, and you can bring your own keys.
4. Model costs are billed by whichever provider you connect. Record the provider and the cost per video in
   `02_research_log.md`. Ask the human before connecting any paid provider.

### Step 8.2: For each approved script

1. Create `08_production/<slot_id>/` and put in it:
   - `script.md`: a copy of `05_scripts/<slot_id>.md`
   - `assets/`: the client's own filmed clips, photos and voice recordings for that script (the SHOT and EDIT notes say
     what's needed)
   - `brand.json`: the `editing_style` block from the client profile
2. **Choose the input style:**
   - **Script-driven (default):** ask Hypit to build the video from `script.md`, the client's `assets/`, and the
     `brand.json` colors and fonts, following the LINE / SHOT / EDIT notes line by line.
   - **Reference-driven:** to match the *pacing and edit structure* of the structure template's source outlier, you may
     give Hypit the source reel as a **reference for production pattern only** (rule 13). Get it locally only with
     human approval (ScrapeCreators `download_media=true` costs 10 credits). Tell Hypit explicitly: "Use this clip only as
     a timing and editing reference. Do not use any of its footage, audio, voice, faces, music or text. All words come from
     script.md, and all visuals come from assets/ or newly generated material." Delete the reference clip after rendering.
3. **Variants (optional):** for A/B testing, render up to 3 variants that change **one** thing each: a different verbal
   hook from the hook stack, a different format, or a different editing treatment (playbook default: at most 3).
4. Check the render before handing it over:
   - [ ] The spoken words match `script.md` (minor ad-libs are fine)
   - [ ] The on-screen written hook appears within the first 3 seconds
   - [ ] Captions are spelled correctly and match the speech
   - [ ] Brand colors and fonts are used
   - [ ] No footage, audio or text from any source video appears (rule 13)
   - [ ] The CTA is on screen and spoken, and any keyword matches the ManyChat keyword
5. Save the final file as `08_production/<slot_id>/<slot_id>_final.mp4` (and `_vB`, `_vC` for variants). **Don't post it**
   (rule 11).

### Gate 8

- [ ] Every produced video passes the step 8.2.4 checks
- [ ] Reference clips (if any) are deleted
- [ ] The costs are logged

---

## Appendix A: Closed vocabularies

Use these exact lowercase IDs.

### A1. Angles
| ID | Meaning |
|---|---|
| `tutorial` | A step-by-step process, framework or acronym |
| `comparison` | Compares methods, actions or products for the same result |
| `myth_bust` | Debunks a common belief or common mistake |
| `do_dont` | Right vs wrong (or old vs new) ways to get a result |
| `tip_hack` | One focused tip, lesson or trick |
| `transformation` | A before and after (the client's own or a client's), plus how |
| `challenge` | A goal attempted as a challenge, documented |

### A2. Delivery
`educational`, `storytelling`

### A3. Story types
| ID | Meaning |
|---|---|
| `my_story` | Life story or founder story |
| `win` | An achievement, milestone or opportunity |
| `loss` | A mistake, failure or bad result |
| `lesson` | What a win or loss taught them |
| `transformation` | Their own or a client's before and after |
| `challenge` | A self-set challenge and the journey through it |
| `big_goal` | Announcing a big goal and the plan to reach it |

### A4. Content types
`educational`, `storytelling`, `authority`

### A5. Formats
| ID | Meaning |
|---|---|
| `talking_back_forth` | One person plays two characters; the "smart" one teaches the "clueless" one |
| `visual_prop` | Props or visuals demonstrate the point |
| `voiceover` | Footage or images with narration over them |
| `multitasking` | Teaching while doing an unrelated task (cooking, cleaning, getting ready) |
| `setting_change` | A new location every 1 to 2 lines |
| `shot_angle_change` | A new shot or angle about every 2 seconds |
| `clone` | Two versions of the same person on screen, comparing two things |
| `whiteboard` | Explaining on a whiteboard |
| `qa` | Someone off camera asks one or more people a question |
| `green_screen` | Relevant images or video behind the speaker |
| `reaction` | React to a very popular niche video, then give an expert take |
| `audio_broll_text` | A new image or clip every 1 to 3 seconds, story told in on-screen text over emotional music |
| `talking_head` | Sitting and talking to camera. **Only allowed for `experiment` slots** |
| `unknown` | Only in Phase 3, when you can't see the video |

### A6. CTA types and lines

The lines are a playbook default; swap in the client's own wording from `voice`.

| ID | Use on | Line pattern |
|---|---|---|
| `follow` | TOFU, MOFU, BOFU | "Follow for more {{NICHE}} {{CONTENT_NOUN}} like this." / for series: "Follow so you don't miss part {{NEXT_N}}." |
| `freebie` | TOFU, BOFU | "Comment {{KEYWORD}} and I'll send you {{FREEBIE_NAME}}." (`KEYWORD` = `freebie.manychat_keyword`, ALL CAPS, ≤ 7 letters) |
| `paid_offer` | BOFU | "Comment {{KEYWORD}} and I'll send you the details on {{OFFER_NAME}}." (always pair with proof in the body) |
| `engagement` | any | "Comment {{QUESTION_ANSWER_OPTIONS}}, and tell me which one you are." |
| `none` | experiments only | (no CTA line) |

Never send viewers to "the link in bio" for a freebie or offer. Use the comment-keyword DM (ManyChat) pattern.

### A7. Funnel stages
`tofu` (goal: views), `mofu` (goal: followers), `bofu` (goal: leads)

### A8. Beat labels
| Label | What the sentence does |
|---|---|
| `HOOK` | The opening, in the first ~3 seconds |
| `CONTEXT` | Sets the scene or the problem |
| `PROMISE` | Says what the viewer will get |
| `NAME_METHOD` | Names the rule, framework or plan |
| `STEP` | One step or item of a list |
| `EXAMPLE` | A concrete illustration |
| `PROOF` | A result, number or testimonial |
| `MYTH` | States the wrong belief |
| `TRUTH` | Corrects it |
| `CONTRAST` | Puts two options or two people side by side |
| `TURN` | The twist or the moment things changed |
| `RESULT` | The outcome |
| `LESSON` | The takeaway or meaning |
| `RECAP` | A summary |
| `LOOP` | A cliffhanger or "part 2" tease |
| `CTA` | The call to action |

### A9. Slot types
`AUDIENCE`, `OUTCOME`, `PAIN`, `MISTAKE`, `MYTH`, `TRUTH`, `METHOD_NAME`, `NUMBER`, `ORDINAL`, `ITEM`, `STEP_ACTION`,
`EXAMPLE`, `TIMEFRAME`, `COST`, `RESULT`, `PROOF`, `STORY_MOMENT`, `EMOTION`, `CONTRAST_A`, `CONTRAST_B`, `QUESTION`,
`KEYWORD`, `FREEBIE`, `OFFER`, `TOPIC`, `NICHE`, `PERSON` (only a client, with permission, or "I")

### A10. Other labels
- `bucket`: `proven`, `double_down`, `experiment`
- `complexity`: `easy`, `complex`
- `series_type` (for series slots): `daily` (hook states the day number and restates the goal; a daily update), `progress_update`
  (one goal; updates whenever there's progress), `lesson` (one lesson per episode), `step_by_step` (one step of a process per episode)
- `carousel_type` (if asked for carousels): `tutorial`, `do_dont`, `tip_hack`, `storytelling`, `transformation`, `problem_solution`, `list`, `types`

---

## Appendix B: Prompts for sub-tasks

Use these when you hand a step to another model call. With OpenRouter, send the prompt as the `system` message and the
filled inputs as the `user` message (see the [OpenRouter quick reference](#openrouter-quick-reference)). Fill the `<…>`
parts and attach the relevant files' contents.

### B1. Templatize prompt (Phase 4)

```
You turn viral short-form video text into niche-neutral fill-in-the-blank templates.

INPUT: the exact source text below and its beat labels.
TASK:
1. Keep only frame words: words that create the pattern (question openers, time markers, list markers,
   contrast words, reveal phrases, CTA mechanics).
2. Replace every run of niche-specific or creator-specific words (nouns, activity verbs, their numbers,
   names, brands, places, claims) with one slot written {{NAME:TYPE}}. NAME is UPPER_SNAKE_CASE and unique.
   TYPE is one of: <paste A9 slot types>.
3. Turn repeated parts into [REPEAT {{N:NUMBER}} times] ... [/REPEAT].
4. For every slot, write a fill rule: what goes there, max words, and which client field it comes from
   (knowledge, stories, proof, offers, freebie, profile, any).
5. Check: with slots hidden, the template must not reveal the original niche. If it does, fix it.
OUTPUT: JSON matching this schema exactly: <paste the H### or T### schema>.
SOURCE TEXT: <paste>
BEATS: <paste>
```

### B2. Fill prompt (Phase 5)

```
You write one short-form video script for a real client by filling a template.

HARD RULES:
- Use ONLY facts from the CLIENT BANK ITEMS below. Never invent stories, numbers, results, names or credentials.
  If a slot needs a fact you don't have, write [[NEEDS CLIENT INPUT: <what>]].
- Do NOT reuse any wording or facts from the source videos. Only the template's frame words may stay.
- Write in the client's voice: uses <voice.uses>; never use <voice.never_uses>; <voice.reading_level>.
- Hooks: verbal ≤ 15 words, written ≤ 7 words, visual = one filmable action under 3 seconds.
- The value must be specific and actionable (a number, a named step, a concrete example).
- Total words: <target_words range>.

INPUTS:
SLOT: <the slot object from 01_month_plan.json>
HOOK TEMPLATES: <verbal, written and visual templates>
STRUCTURE TEMPLATE: <T### object>
CLIENT BANK ITEMS: <only the picked items, with IDs>
CTA: <cta_type and the line pattern; keyword; freebie or offer name>
FORMAT: <format id and meaning>
EDITING STYLE: <editing_style>

OUTPUT: the script file in exactly this layout: <paste the Step 5.6 layout>. List the bank IDs used.
```

### B3. QA prompt (Phase 6)

```
You are a strict reviewer. Check this script against each check below and answer PASS or FAIL for each,
with a one-line reason for every FAIL. Do not rewrite the script.
CHECKS: <paste the Q1–Q12 table>
SCRIPT: <paste>
SOURCE TRANSCRIPTS USED: <paste>
CLIENT BANK ITEMS LISTED: <paste>
MONTH PLAN SLOT: <paste>
OUTPUT: JSON {"slot_id": "...", "results": {"Q1": "PASS", ...}, "fail_reasons": {...}}
```

Run Q5 (the 6-word overlap check) in code, not by eye, if you can:

```python
import re
def grams(text, n=6):
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}
shared = grams(script_body) & grams(source_transcript)   # PASS when shared is empty
```

---

## Appendix C: Worked example

A complete walk-through of one slot. **Everything here is invented for illustration.** The "source video" isn't a real
video, and the client is fictional. Use it to see what each output looks like.

### C1. Inputs

- **Client:** the profile shown in [Phase 0](#00_client_profilejson-schema) (Maya Ortiz, dog trainer). Additional bank items for this example:
  - `K1` (crate training): 3-step crate intro: meals in the crate with the door open for 3 days; then close the door for
    1 minute while eating; then leave the room for 5 minutes once calm.
  - `K2` (crate training): Night routine: crate next to the bed for the first 3 nights, then move it one step farther away every 2 nights.
  - `S2` (story_type `loss`): "With my own first puppy, I lost about three weeks of sleep to night crying because I
    shoved him in the crate on day one."
- **Slot:** `V01`, week 1, Monday, `proven`, `tofu`, `educational`, `cta_type: freebie`, topic `crate training`.

### C2. Phase 2: the outliers found (invented)

| ID | Creator niche | Views | Followers | Ratio | Why saved |
|---|---|---|---|---|---|
| O001 | Meal prep | 126,000 | 18,000 | 7.0 | hook + structure |
| O006 | Personal finance | 410,000 | 52,000 | 7.9 | written hook |
| O011 | Home organizing | 98,000 | 9,500 | 10.3 | visual hook |

### C3. Phase 3: extraction of O001

Source transcript (invented, 98 words):

> I wasted two hundred dollars a month on takeout until I tried this. Here's the three-container rule.
> Container one: a protein you cook once on Sunday, I do a full tray of chicken thighs. Container two: a grain
> that keeps five days, like rice or farro. Container three: one sauce that changes the whole week, because the same
> chicken with a new sauce doesn't feel like leftovers. Monday is chicken, rice and peanut sauce. Wednesday, same
> base, salsa verde. That's it: three containers, forty-five minutes on Sunday. Comment PREP and I'll send you my
> five sauces.

Element record (key fields):

```json
{
  "outlier_id": "O001", "topic": "cross_niche",
  "verbal_hook": {"text": "I wasted two hundred dollars a month on takeout until I tried this.", "end_ms": 3100},
  "written_hook": {"text": "the 3-container rule", "confidence": "cover_only"},
  "visual_hook": {"text": "Creator stacks three glass containers on the counter, one at a time.", "confidence": "seen"},
  "value": {"summary": "A 3-part weekly meal-prep system with a day-by-day example.", "measurable": true, "source_type": "personal_experience"},
  "angle": "tutorial", "delivery": "educational", "story_type": null,
  "beats": [
    {"label": "HOOK", "text": "I wasted two hundred dollars a month on takeout until I tried this."},
    {"label": "NAME_METHOD", "text": "Here's the three-container rule."},
    {"label": "STEP", "text": "Container one: ... Container two: ... Container three: ..."},
    {"label": "EXAMPLE", "text": "Monday is chicken, rice and peanut sauce. Wednesday, same base, salsa verde."},
    {"label": "RECAP", "text": "That's it: three containers, forty-five minutes on Sunday."},
    {"label": "CTA", "text": "Comment PREP and I'll send you my five sauces."}
  ],
  "complexity": "easy", "cta": {"type": "freebie", "text": "Comment PREP and I'll send you my five sauces."},
  "format": "visual_prop", "content_type": "educational", "funnel": "tofu"
}
```

Why `easy`: "Container one/two/three: …" repeats one sentence shape 3 times with only the nouns changing.

### C4. Phase 4: the madlibs

| ID | Type | Template | Source |
|---|---|---|---|
| H001 | verbal | "I wasted {{COST:COST}} on {{BAD_HABIT:MISTAKE}} until I tried this." | O001 |
| H014 | written | "{{N:NUMBER}} steps to {{OUTCOME:OUTCOME}}" | O006 (its cover read "3 steps to a debt-free year", invented) |
| H027 | visual | "Pulls {{N:NUMBER}} {{ITEM:ITEM}}s out of a bag one at a time and sets each down." | O011 |
| T001 | structure | HOOK → "Here's the {{N}}-{{UNIT}} rule." → [REPEAT N] "{{UNIT}} {{ORDINAL}}: {{STEP_ACTION}}, {{STEP_EXAMPLE}}." → "{{SITUATION_1}}: {{APPLY_1}}. {{SITUATION_2}}: {{APPLY_2}}." → "That's it: {{N}} {{UNIT}}s, {{TIME_COST}}." → CTA | O001 |

Neutrality check on T001: with the slots hidden it reads "Here's the ___-___ rule. ___ one: ___, ___. … That's it: ___ ___s,
___." Nothing reveals meal prep, so it **passes**.

### C5. Phase 5: the filled script for the dog trainer

Hook stack. The templates come from 3 different outliers, so Q2 passes.

- **Verbal (H001 + S2):** "I wasted three weeks of sleep on a crying puppy until I tried this." (14 words ✓)
- **Written (H014 + K1):** "3 steps to a calm crate" (6 words ✓)
- **Visual (H027 + K1):** Maya pulls a crate pad, a food bowl and a kitchen timer out of a tote bag one at a time and sets each down.

The script, as it appears in `05_scripts/V01.md`:

1. LINE: I wasted three weeks of sleep on a crying puppy until I tried this. *(S2)*
   SHOT: Medium shot at the kitchen table; tote bag in front of Maya.
   EDIT: Written hook "3 steps to a calm crate" in the primary font, orange #E07A3F, top third.
2. LINE: Here's the three-step crate rule.
   SHOT: Close-up of the three items lined up on the floor next to an open crate.
   EDIT: Label each item as it's named.
3. LINE: Step one: feed every meal inside the crate with the door open, for three days, so the crate means dinner. *(K1)*
   SHOT: The puppy eating in the crate, door wide open.
   EDIT: "Days 1–3" callout.
4. LINE: Step two: close the door for one minute while they eat, and open it before they fuss. *(K1)*
   SHOT: The door closing; the kitchen timer in frame.
   EDIT: Zoom on the timer reading 1:00.
5. LINE: Step three: once they eat calmly with the door shut, leave the room for five minutes and come back boring. *(K1)*
   SHOT: Maya walking out of frame; the puppy settled.
   EDIT: "5 min" callout; "come back boring" in the accent font.
6. LINE: Night one through three: crate right next to your bed. After that: one step farther away every two nights. *(K2)*
   SHOT: The crate beside the bed, then a floor-level shot of it moved a step back.
   EDIT: Footstep icon for each move.
7. LINE: That's it: three steps, about ten minutes a day.
   SHOT: Back to the medium shot.
   EDIT: Recap list of all 3 steps on screen.
8. LINE: Comment PUPPY and I'll send you my Puppy's First 30 Days Checklist.
   SHOT: Maya holding up a phone showing the checklist.
   EDIT: "Comment PUPPY" banner.

Caption:

```
3 steps to a calm crate

Comment PUPPY and I'll send you my Puppy's First 30 Days Checklist

#dogtraining #newpuppyowner #cratetraining
```

### C6. Phase 6: QA on V01

| Check | Result |
|---|---|
| Q1 hook stack | PASS (all three present; 14 and 6 words) |
| Q2 diversity | PASS (O001, O006, O011) |
| Q3 hook ↔ value | PASS (every hook promises a calm crate, and the body delivers 3 crate steps) |
| Q4 measurable | PASS (3 days, 1 minute, 5 minutes, named steps) |
| Q5 overlap | PASS. Shared 6-word sequences between lines 2 to 8 and O001's transcript: **0**. The only shared runs are the frame words "Here's the", "That's it", "and I'll send you my" (5 words) |
| Q6 facts | PASS (every claim traces to S2, K1 or K2) |
| Q8 CTA | PASS (freebie, keyword PUPPY from the profile) |
| Q10 length | PASS (117 words; the template target is 78–118, i.e. 98 ± 20%) |

---

## Appendix D: Run checklist

Copy this into `02_research_log.md` at the start of every run, and tick boxes as you go.

- [ ] **Phase 0:** profile and Client Bank complete (Gate 0), or gaps listed
- [ ] **Phase 1:** `01_month_plan.json`, N slots, mix verified (Gate 1)
- [ ] **Phase 2:** keyword list built; mode chosen and logged; `GET /me` balance recorded; outlier quota met (Gate 2)
- [ ] **Phase 3:** first transcript's credit cost measured; element files written; seven factors filled (Gate 3)
- [ ] **Phase 4:** hook and structure templates built; neutrality check passed; minimums met (Gate 4)
- [ ] **Phase 5:** every slot has a script file and an ideation row (Gate 5)
- [ ] **Phase 6:** QA report written; every script PASS or FAILED with a reason; client needs listed (Gate 6)
- [ ] **Phase 7** (only with analytics): review written; own outliers marked; double downs queued
- [ ] **Phase 8** (only if `produce_videos`): scripts approved by a human; videos rendered; render checks passed; reference clips deleted (Gate 8)

---

## Appendix E: Source map

Where each rule comes from in the @PersonalBrandLaunch videos. Numbers that aren't in this list are playbook defaults.

| Rule in this playbook | Source video |
|---|---|
| Seven factors of a short; three hooks; measurable vs fluffy value; 7 angles; formats; editing style; ManyChat CTA | [How to Make a Killer Short](https://www.youtube.com/watch?v=PG0X3SjEmfU) |
| Niche + 5–7 sub-niches; profile; 70/20/10; doubling down; script layout (black/red/green); captions; 50–100 videos to 1K | [How to Grow an Instagram Account in 2026](https://www.youtube.com/watch?v=Hm-vzorCUHk) |
| 7 story types; story formats; templatizing a transcript with an LLM; past photos; emotional music | [How To Make Viral Storytelling Content](https://www.youtube.com/watch?v=yQX9wg5kvCA) |
| Research system: dummy account + reset, keyword, 4 account methods, most viewed, Reels tab; hook stacks; cross-niche hooks | [How to Create Irresistible Hooks](https://www.youtube.com/watch?v=sRutnMnQGo4) |
| Series types; three content types; doubling down variants A/B/C | [I Studied the Top 100 Fastest Growing Creators](https://www.youtube.com/watch?v=UM2Vv_3-ODA) |
| Script structures; easy vs complex; transcribe → templatize → bank; no word-for-word copying | [How to Write a Killer Script in 2026](https://www.youtube.com/watch?v=PJWWGq_Yuoo) |
| Six "cheat codes" summary; series formats | [How to Grow from 0 to 100K Followers](https://www.youtube.com/watch?v=IK8VpSy1tus) |
| TOFU/MOFU/BOFU; weekly posting splits by follower tier; avoid hard-sell testimonial videos | [Your EXACT System to Blowing Up on Instagram](https://www.youtube.com/watch?v=yFldV9hR3Sc) |
| Profile, 4-line bio, highlights, pinned posts | [Optimize Your Profile Like the Top 1%](https://www.youtube.com/watch?v=ChifKqh25Nk) |
| Carousel types; reel → carousel; trending audio on carousels | [8 VIRAL Carousel Ideas](https://www.youtube.com/watch?v=eBoc3TmL3yg) |
| Master prompt; role/context/command/format; SOP → skill → agent; human QC; anti-"AI slop" rules | [How to Use AI For Your Content](https://www.youtube.com/watch?v=9kfy0VO55kA) |
| Monthly batching order; 90/10 for new accounts; hook stacks from different videos; value from your own head | [How to Create a Month Worth of Content in 60 Minutes](https://www.youtube.com/watch?v=TpTY6hFJbic) |
| Founder split: 50–75% expert, 25–50% journey; documentation content types | [Stand Out Social Media for Your Personal Brand as a Founder](https://www.youtube.com/watch?v=PU6LdQCluYE) |

The tool choices (ScrapeCreators, OpenRouter, Hypit, Supadata) and their API details are this playbook's own. They aren't
from the videos. The ScrapeCreators details were checked against its OpenAPI spec, and the Hypit setup comes from its README.
