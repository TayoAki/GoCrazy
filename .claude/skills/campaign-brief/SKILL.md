---
name: campaign-brief
description: Turn a paid clipping or UGC campaign (Whop, Content Rewards, an agency's brief) into its rules and a creator brief. It reads every page the campaign links to with Firecrawl, writes each rule in its own words into campaign.json, works out what the pay really means (the cap, the budget, the views needed), and writes a creator brief whose formats, hooks and slide plans come from the slideshow-content skill's outlier research. Then it hands the brief to tiktok-ftc-check (step 2) and gives creators only the checked version. Use it when someone shares a campaign and wants a brief, e.g. "make a creator brief for this campaign", "break down this clipping campaign", "what does this campaign want", "brief for the DreamMe slideshow campaign", "turn this Whop campaign into instructions for my creators".
---

# Campaign brief

A two-step process. **Step 1 (this skill):** the campaign's rules (`campaign.json`) and a creator brief (`brief.md`).
**Step 2 (`tiktok-ftc-check`):** rule on both against TikTok's rules and FTC law, and write `brief.checked.md`.
Creators get the checked brief, never the step-1 draft.

The content comes from the `slideshow-content` skill: its outlier research, formulas, hooks and slide renderer. `$S`
below is this skill's `scripts/` folder, and `$SC` is `slideshow-content/scripts`. Everything goes in
`briefs/campaign-<slug>/`, which is gitignored because it holds a client's campaign.

## 1. Set up and paste the campaign

```bash
python3 $S/campaign.py new <slug>      # briefs/campaign-<slug>/ with campaign.txt and a campaign.json to fill
```

Paste the campaign into `campaign.txt` exactly as the brand or agency wrote it, links included. A paste often loses
its links (they come through as "👉 Content Vault"): ask for the URLs, or find the pages in step 2.

## 2. Read everything it links to

```bash
python3 $S/explore.py briefs/campaign-<slug> --search "<brand> <platform> campaign"   # find the campaign's own pages
python3 $S/explore.py briefs/campaign-<slug> --url <campaign page> --url <guide> --follow
```

- Firecrawl reads each page into `sources/` and lists them in `sources/index.md`. It needs `FIRECRAWL_API_KEY` in the
  repo's `.env`. If the key is missing, ask the person to add it there, never to paste it. A search is about 2 credits
  and a page 1.
- **Locked pages.** The guide, the vault and the rules file are often behind the campaign's login. Mark them in
  `locked` and ask the person to paste or export them once they've joined. Don't try to get past a login.
- **Sites Firecrawl won't read** (TikTok, Instagram) are reported as FAILED. Read them with a normal web fetch, or
  skip them.
- **Read the product's own page too.** For an app, run `python3 $SC/app-store.py fetch <app> briefs/campaign-<slug>`.
  It gets the real name, what the app does in its own words (and any "not medical advice" line), the icon and
  screenshots. The brief describes the product from this, not from the campaign's pitch.
- **Compare sources.** The campaign page can disagree with the paste (a different budget, a rule only one of them
  has). Note each conflict.

## 3. Write the rules: campaign.json

`references/campaign-schema.md` has the fields. Every line of the campaign that asks creators to do something becomes
a rule: its own words, its kind, where it came from, and whether it's clear.

- Keep rules that may not be allowed (AI images, account tricks, watermark removal) in the campaign's words. Step 2
  rules on them; step 1 just records them.
- Mark a rule `unclear` when it can be read two ways, and `conflict` when two sources disagree. Add the question for
  the brand to `open_questions`.

```bash
python3 $S/campaign.py check briefs/campaign-<slug>     # missing fields, open questions, and the payout math
```

## 4. Find the formats that win (slideshow-content)

Use the slideshow-content skill's research for the campaign's niche (its SKILL.md steps 2 to 4).

- **Reuse what's there.** `python3 $SC/formulas.py refs <project> --out briefs/campaign-<slug>/research` and
  `formulas.py stats`. Search the outliers for the campaign's topic words too (e.g. "GLP-1", "Ozempic").
- **A new niche** needs a research run. Ask before spending credits, as that skill says.
- **Pick 2 to 4 formulas.** They should fit the campaign's style rules (hook first, the slide count, the angle it
  asks for). They also have to work honestly for the product: a tracking app suits "what I track", "what I eat" and
  grocery formats, not dramatic results.
- **Say who can post each one.** A first-person story ("my GLP-1 journey") is only for a creator it happened to.
  Formats anyone can post (lists, groceries, tips, product facts) are what most of a campaign's creators will make.
- **For each formula,** take the hooks, the slide structure and the caption shape from the winning posts. Link the
  posts and give their numbers.
- **Render one example post** with slideshow-content, so creators see the standard. That means `post.json` and
  `render.py`, with real licensed photos from `find-photos.py` and the product's real screenshots from
  `app-store.py`. Every number on it must be checked, as that skill's step 7 says.

## 5. Write the brief: brief.md

`references/brief-template.md` has the sections:
- the campaign in one minute
- pay (the table from `campaign.py pay`)
- the rules
- your account
- what to post (each format with its evidence, who can post it, slides, hooks, caption and pictures)
- making the slides
- posting
- submitting

**Held for the compliance check.** Requirements that may break TikTok's rules or FTC law go in this last section,
quoted exactly, with the rule each may break. Don't turn them into steps: no instructions for generating people,
removing watermarks, or making an account look like someone else. Step 2 decides them. Write the rest of the brief so
it works without them.

## 6. Step 2: check it

Run the `tiktok-ftc-check` skill on `campaign.txt`, `campaign.json`, `brief.md` and the example post's `post.json`. It
writes:
- `compliance.md`: a verdict on every requirement and claim, with the rule and the fix.
- `brief.checked.md`: the brief with the fixes made, and compliant alternatives where something can't run.

## 7. Hand it over

- **To creators:** `brief.checked.md` and the example post's slides.
- **To the person who asked:** `compliance.md`, or a doc if they want one to share.
- **In chat:** a few lines on what the campaign wants and what it pays. Then what can't run as written and what the
  brief does instead, and the questions for the brand.
