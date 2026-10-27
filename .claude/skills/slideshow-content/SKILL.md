---
name: slideshow-content
description: Research the TikTok photo slideshows and Instagram carousels that outperform in a niche, find the proven formulas (plays ÷ followers, saves per 1,000 plays), pick one, and build ONE post that combines the version of each element that won, with every number checked against a primary source and a written case for why it should work. Then render it as ready-to-post 3:4 slide templates whose photo spots the person replaces with their own photos. Use this whenever someone wants slideshow or carousel content for an app, brand or creator, e.g. "what slides should we make to market X", "find the outlier slideshows in this niche", "proven formulas for this niche", "recreate this outlier", "combine what works into one post", "make the slide templates", "a carousel for my app", even if they never say "slideshow". For talking-head reel, TikTok or Shorts scripts use short-form-content instead.
---

# Slideshow content: from outliers to a post that's ready to shoot

This skill turns a niche's winning slideshows into one post: research → proven formulas → one formula → the post,
built from the parts that won → every number checked → slide templates with photo spots → a write-up of why it
should work and how to post it.

It was built on a real run for Weight Class, a calorie-tracking app: nearly 100 winning slideshows and carousels, food swaps chosen as the
most-saved formula, and "5 easy swaps that actually save calories" built from seven references. That post is the
worked example in `assets/example/`.

Everything runs from the repository that holds `research_app/` (the outlier research app). Scripts are in this
skill's `scripts/` folder. Below, `$S` stands for that folder, e.g. `.claude/skills/slideshow-content/scripts`.

## What you deliver

One folder per post, `briefs/<slug>/`. `briefs/` is gitignored, because it holds research about other people's
posts and this repo is public. Never commit it, or `data/`.

```
briefs/<slug>/
  product.md              what's true about the product (step 1)
  research/refs.md        every winning post, readable (step 3)
  research/formulas.md    the formulas ranked, and the patterns across all winners (step 3)
  post.json               the slides (step 6)
  photos/                 empty until the person shoots; photos/<key>.jpg fills a spot
  assets/                 screenshots for the app slide
  out/slide_01.png …      the slides, and out/contact.jpg with all of them at a glance
```

Then a write-up (step 9) and the folder as a zip.

## 1. Know the product before writing a word about it

The last slide makes claims about the product, so get them right first. Read its website and its App Store or shop
page, and write `product.md`:
- what it does
- the price model ("free to download, with Premium")
- platforms
- where its numbers come from (e.g. USDA)
- its real store link

Sites go stale: in the Weight Class run the site still said "on its way" while the app was live. When the sources
disagree, say so.

## 2. Research the niche's slideshow outliers

The research app finds posts that beat their creator's follower count by 5× or more. It searches TikTok's Top
results (slideshows) and creators' feeds (Instagram carousels), then tears each one down slide by slide. Its README
(`research_app/README.md`) has the details.

```bash
python3 $S/research.py serve          # starts the app on :8000 if it isn't running
python3 $S/research.py projects       # reuse an existing project for this niche when there is one
python3 $S/research.py new --name "Weight Class" --niche "calorie tracking app for iPhone" \
  --keywords "calorie deficit, high protein snacks, food swaps, what i eat in a day, calorie counting app" \
  --study "calai.app, myfitnesspal" --budget 400
python3 $S/research.py run <id>       # 20–40 min; prints progress
python3 $S/research.py teardown <id>  # tears down the slideshow and carousel outliers, 3 at a time
```

- **Keywords:** 6–10, in the audience's own words. Mix three kinds:
  - the problem ("calorie deficit")
  - the content people save in the niche ("high protein snacks", "food swaps")
  - the category ("calorie counting app")
- **Study accounts:** competitors' own accounts and creators who grew fast in the niche. They're scanned deeper,
  whatever their size.
- **Credits:** the research spends ScrapeCreators credits. The Weight Class run used 458 credits in 28 minutes, with
  40 creators and 10 study accounts. Tell the person the budget and get a yes before `run`, unless they already asked
  you to run the research. The key lives in `.env` as `SCRAPECREATORS_API_KEY`. If it's missing, ask them to add it
  there. Never ask anyone to paste a key into the chat.
- **AI teardowns** need the `claude` command or `OPENROUTER_API_KEY`. `research.py serve` prints which one is in use.
- **Don't import `research_app.server` from another process while the app works.** Its start-up marks any run in
  progress as failed. The scripts here only use HTTP, or read the database read-only. Don't restart the app during a
  run either.

## 3. Find the proven formulas

```bash
python3 $S/formulas.py refs <id> --out briefs/<slug>/research    # refs.md + refs.json
```

Read `refs.md` in full. It has every winning post: plays, followers, ratio, saves per 1,000, cover text and template,
each slide's text, style, ask, sound and caption.

Group the posts into **formulas**. A formula is a promise plus the way each slide keeps it, not just a topic:
- "Food swaps": one swap per slide, both foods with their calories
- "Fast-food orders": one chain per slide, the order and its macros
- "What I eat in a day"

A formula is proven when **at least two different creators** won with it. One creator repeating a format shows it
works for them; several show it works for the niche. Write `groups.json` (`{"Food swaps": ["<shortcode>", …]}`) and
run:

```bash
python3 $S/formulas.py stats <id> groups.json --out briefs/<slug>/research/formulas.md
```

**Rank formulas by median saves per 1,000 plays, then by the number of creators.** Plays show reach, which one lucky
post can get. Saves show that people found it useful enough to keep, which is the feeling a product needs attached to
it. `stats` also prints the patterns across every winner: slides, shape, cover length, covers with a number, sound,
the ask, sounds used by several winners. Those patterns feed step 5.

When you explain the metrics, say what they are in plain words. People ask.
- **Plays ÷ followers:** a 1,000-follower account whose post got 50,000 plays scores 50×.
- **The median across a formula's winners:** the middle one, so one freak hit can't carry a formula.
- **Saves per 1,000 plays:** how many of every thousand viewers kept it. TikTok shows saves; Instagram doesn't.

## 4. Pick one formula

Take the most-saved formula that also passes these:
1. **Room for the product.** The product can be the honest answer to something the post raises (where the numbers
   come from, how to log it), not an ad bolted on.
2. **Every number can be checked now** from a primary source (step 7). Weight Class's fast-food formula had more
   winners, but the chains' nutrition pages couldn't be read, so swaps went first, with numbers from USDA.
3. **Makeable in a day** with phone photos and no filming.
4. **Not owned by competitors' own accounts.**

Show the person the references. For each, give its slides side by side (`formulas.py sheet <shortcode> … --out
sheet.jpg`), plays, followers, ratio, saves per 1,000, slide count and what its numbers look like. Then say which
formula you picked and why, in a sentence they can disagree with.

## 5. Plan the post by recreating what won

Read `references/elements.md`. For every element (formula, cover words, number on the cover, cover photo, slide
layout, number format, photos, verdict line, page count, save ask, length, shape, the product, sound, caption, angle),
take the version that won and write down the post it came from and its numbers.

The point of combining is that each reference has a weak spot another one covers. Pair the cover of the post that
travelled furthest with the slides of the post that was saved most. Put the product once, on the last slide, as the
answer the post sets up.

## 6. Write the slides

Copy `assets/example/post.json` to `briefs/<slug>/post.json` and rewrite it. The format is in
`references/post-spec.md`, with slide types `cover`, `compare`, `item`, `list` and `app`.

- **One idea per slide, readable in two seconds:** a short title, numbers in big boxes, one verdict line.
- **Every photo spot gets a brief** that says exactly what to shoot: the real product, held or on a counter, the label
  to camera when the label carries the number. Real phone photos are what the most-saved references used.
- **Verdict lines must be literally true.** "3 full cups, and still 56 fewer calories" can be checked; "three times
  the bowl" can't. Totals say what they total ("across all five", not "a day").
- **The app slide** needs a real screenshot of the product doing what the post promises (`assets/`). If you only have
  a website screenshot, use it as a stand-in and ask for the real one.

## 7. Check every number against a primary source

Every number on a slide must come from a source you actually read in this session. A wrong number on a saved post
draws correction comments for as long as people find it, and the product's slide vouches for those numbers.

- **Food:** USDA FoodData Central. `python3 $S/usda.py search "greek yogurt plain nonfat"`, then `usda.py show
  <fdc id>` for per-100 g and per-serving values at USDA's own serving weights, rounded like a label. Use the serving
  people actually eat, and keep the fdc ids for the write-up.
- **Restaurant orders:** the chain's own nutrition page or PDF. Third-party sites don't count.
- **Prices, product claims:** the store's or the product's own page.
- **Can't verify it?** Drop the number, change the item, or change the angle. Never publish a guess, and say what you
  dropped.

Generic values won't match every brand. Tell the person to check each one against the label in their photo, and to
use the label's number if they differ.

## 8. Render and review

```bash
python3 $S/render.py briefs/<slug>       # out/slide_NN.png + out/contact.jpg; lists photo spots still empty
```

Look at `out/contact.jpg`, then at the cover and one content slide at full size. Fix what you see in `post.json` and
render again:
- a line that breaks mid-phrase (put a `\n` where it should break)
- a verdict that leaves one word on its own line
- text that runs into a photo
- anything too small to read on a phone

Rendering needs Playwright's Chromium and Pillow.

## 9. Write it up, and hand it over

If the docs connector is available, write the write-up as a doc. Otherwise write `briefs/<slug>/brief.md`. Use these
sections:

1. **The post.** What it is in one paragraph. Why this formula, with its saves and creators. What it takes from the
   rest of the research.
2. **The slides.** The contact sheet, then the cover and one content slide at full size. A table for repeated slides
   (each slide's items and numbers). Where every number comes from (source, id, serving weight).
3. **Why we think it will work.** The weak-spot logic (step 5), then a table: Element | What we do | Taken from (linked)
   | The evidence. Then what could go wrong: sample sizes, account type, generic numbers against labels, and that a
   sound is a correlation, not a cause.
4. **How to post it.**
   - The shot list (photo key → what to shoot).
   - Check the numbers against the labels.
   - Replace the app screen, then rebuild with `render.py`.
   - Post as a TikTok photo post and an Instagram carousel the same day.
   - The sound. TikTok's original sounds don't carry over to Instagram, so pick a quiet song there.
   - The caption: one line, first person only if it's true, plus 4–5 hashtags.
   - An App Store campaign link in the bio.
   - Correct numbers in the comments and pin the correction.
5. **What to measure, and what to do next.**
   - Saves per 1,000 plays at 48 hours and 7 days, against the references' range (Weight Class swaps: 27–49 when it
     works; under 5 means watched, not kept).
   - Plays ÷ followers (5× is an outlier).
   - Profile visits and installs from the campaign link.
   - Next: saves high → a second post in the same layout. Reach high but saves low → the content isn't worth keeping.
     Both low → post the same slides from a creator's account.

Zip the post folder and send it with the file tool when you have one. Finish with a few lines in chat: what the post
is, why it should work, and what the person does next (usually: take the photos, drop them in `photos/`, run
`render.py`).

## When the person comes back with photos

Put them at `briefs/<slug>/photos/<key>.jpg` (the keys are in `post.json`) and run `render.py`. Check each filled slide
at full size: crop, readability of the text over the photo, the label in shot. If a product's label disagrees with the
slide, change the number and its verdict line in `post.json`, then render again.
