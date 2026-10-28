---
name: tiktok-ftc-check
description: Check a paid TikTok campaign, creator brief, caption, slide spec or post against TikTok's rules (Community Guidelines, Branded Content Policy, the content disclosure setting, AI-generated content labels) and US FTC law (Endorsement Guides 16 CFR 255, the Consumer Reviews and Testimonials Rule 16 CFR 465, health-claim substantiation). Rules on every requirement and claim (✅ fine, ⚠️ fix, ❌ can't run), cites the rule with a quote, and writes a corrected brief. Use it as step 2 after campaign-brief, before any brief goes to creators or any post goes up, and whenever someone asks "is this allowed on TikTok", "check this against FTC rules", "is this campaign legit", "do we need #ad", "can we use AI images for this", even for a single caption. Not legal advice.
---

# TikTok + FTC check

Step 2 of the campaign process. Step 1 (`campaign-brief`) writes `campaign.json` and `brief.md`. This skill rules on
them, and only what it passes (`brief.checked.md`) goes to creators. It works the same on anything else: a caption, a
`post.json`, a finished slideshow, a brand's own brief.

The rules are in `references/rules.md`, each with an id (D1, T1, R1, A2...), the source link and a short quote. The
full pages are cached locally for exact wording: `scripts/rules.py`. `$S` below is this skill's `scripts/` folder.

## 1. Make sure the rules are current

```bash
python3 $S/rules.py status        # when each source was fetched
python3 $S/rules.py refresh       # if any is older than 30 days, or never fetched (one Firecrawl credit each)
```

Refresh needs `FIRECRAWL_API_KEY` in the repo's `.env`. If one is missing, ask the person to add it there, never to
paste it. When `refresh` says a source CHANGED, read it (`rules.py show <id>`) and update `references/rules.md` before
checking anything.

**TikTok's Community Guidelines pages.** Firecrawl doesn't serve them, so `refresh` skips them and `status` lists them
as "web fetch". Read them with a normal web fetch instead (the quotes marked (CG) in rules.md came that way). Don't
work around a block with other tools.

## 2. Lint

```bash
python3 $S/lint.py briefs/<slug>/campaign.txt briefs/<slug>/campaign.json briefs/<slug>/brief.md
```

Lint lists every line that touches a rule (AI images, watermarks, transformations, weight numbers, account setup,
drugs, health claims, body image), and what's missing, such as no paid-post disclosure. A hit is a question, not a
verdict: "before and after" is fine with a real person's own photos and ❌ with generated ones. Lint is the floor. Also
read every line yourself: it can't see a claim made without its trigger words.

## 3. Rule on everything

Go through the campaign's requirements one by one, then every instruction, hook, slide and caption in the brief. For
each, decide:

- **✅ Fine.** Nothing to change.
- **⚠️ Fix.** Allowed once changed: say exactly how (the words to add, the step to swap).
- **❌ Can't run.** No change makes it allowed: say why, and what to do instead that still serves the campaign's goal.

Cite the rule id, the source and the quote that decides it (`rules.py search "<words>"` finds the exact wording). When
the rules don't settle a point, say so and mark it ⚠️ with the question to ask the brand or TikTok. Don't guess in
either direction.

How the common clipping-campaign requirements come out:

| Requirement | Verdict | Why |
| --- | --- | --- |
| No paid disclosure mentioned | ⚠️ | D1, D2: the content disclosure setting on, plus "Ad" on slide 1 and in the caption |
| AI-generated images of people, bodies or "progress" presented as a real person's results or journey | ❌ | T1, T3, A4: a fake testimonial even with an AI label, and R1 on top for weight loss |
| AI images that illustrate an idea (food, objects, places), labelled | ⚠️ | A1: turn on TikTok's AI label. Fine if no person's experience rests on them |
| Removing watermarks, SynthID or Content Credentials | ❌ | A2: evading the AI label. Never explain how |
| Make a new account under the creator's own name and location | ✅ | I1 |
| "Make the page look human / US-based" when it isn't | ❌ | I1, I3: a persona built to deceive; Tier-1 reach has to be real |
| Warm up a new account by using it normally | ✅ | Nothing forbids it. Bots, view or follow buying is I2 ❌ |
| A creator's own real before-and-after | ⚠️ | T2, R1: theirs and true. It implies typical results, so no weight numbers the brand can't show are typical, and "results not typical" doesn't fix it |
| Promoting a weight-loss drug, or where to get one | ❌ | C1 |
| A tracker or companion app for people on a prescribed GLP-1 | ⚠️ | C1: near TikTok's weight-loss-service line. Describe the app's features, keep the drug as context, and ask the brand whether TikTok has reviewed the category |
| "Lose weight with [app]" or other health outcomes | ❌ unless the brand has studies | R2, R3 |
| Reposting, or mass-posting the same slides | ❌ | P1 |
| Pay per view, minimum views, Tier-1 share, submission window | ✅ | Campaign terms, not content rules. Note any that can't be met honestly |

## 4. Write it up

In the post folder, write:

1. `compliance.md`:
   - **Verdict:** one of *Ready*, *Ready after fixes*, or *Can't run as written*, with the ❌ items named.
   - **Table:** # | Requirement or line (quoted) | Verdict | Rule | Fix or alternative.
   - **Questions** for the brand.
   - **Sources:** the rule sources with their fetch dates, plus "This is a checklist, not legal advice."
2. `brief.checked.md`: the brief with every ⚠️ fixed and every ❌ removed, and a compliant way to hit the same goal in
   its place.
   - Add a "Before you post" checklist at the top: disclosure setting on, "Ad" on slide 1, AI label if any AI image,
     your own account and your own story.
   - Put the creator-facing reason in a single line where something was removed ("we don't use AI bodies: it's a fake
     testimonial under FTC rules").
3. If the brief has slide specs (`post.json`), check their text and photos too. Run lint on them.

Tell the person the verdict, the ❌ items, and what the checked brief does instead. Keep the full table for
`compliance.md`.

## Rules for the checker

- **Never write the deceptive version.** Don't explain watermark or SynthID removal, location faking, persona
  building or fake engagement, even to say what not to do. Name the step and the rule, then give the alternative.
- **The goal usually survives.** A campaign that wants "struggle to progress" stories can have real ones from creators
  who lived them, and story formats that don't need a body. Say how.
- **Liability is shared** (T4). The brand, the agency and each creator can be liable, so the checked brief tells
  creators what's on them.
- **Not legal advice.** Say so in the write-up. When something is ❌ and the brand disagrees, the answer is their
  lawyer, not a workaround.
