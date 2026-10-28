---
name: slideshow-content
description: Research the TikTok photo slideshows and Instagram carousels that outperform in a niche, find the proven formulas (plays ÷ followers, saves per 1,000 plays), and build ONE post from the version of each element that won, with every number checked against a primary source and a written case for why it should work. Renders ready-to-post 3:4 slides with real, licensed product photos found online (never generated), and matches a person's own video to the winning videos and edits it their way (talking head, voiceover, green screen, text over a clip), then sends either to TikTok as a draft. Use this whenever someone wants slideshow or carousel content for an app, brand or creator, e.g. "what slides should we make to market X", "find the outlier slideshows in this niche", "recreate this outlier", "a carousel for my app", "put real product photos in the slides", "edit my video like the outliers", even if they never say "slideshow". For talking-head reel, TikTok or Shorts scripts use short-form-content instead.
---

# Slideshow content: from outliers to a post that's ready to shoot

This skill turns a niche's winning slideshows into one post: research → proven formulas → one formula → the post,
built from the parts that won → every number checked → slide templates with photo spots → a write-up of why it
should work and how to post it.

It was built on a real run for Weight Class, a calorie-tracking app. The research found nearly 100 winning
slideshows and carousels, and food swaps was the most-saved formula. The post, "5 easy swaps that actually save
calories", was built from seven references and is the worked example in `assets/example/`.

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
  photo-search/           one numbered sheet of candidate photos per spot (step 8)
  photos/                 photos/<key>.jpg fills a spot (found photos until the person shoots), SOURCES.md credits
  assets/                 screenshots for the app slide
  out/slide_01.png …      the slides, and out/contact.jpg with all of them at a glance
```

Then a write-up (step 9) and the folder as a zip.

## 1. Know what you're promoting before writing a word about it

The last slide tells people what to do next, so everything on it has to be true. "The product" may be an app, a
shop, a service, a local club or a creator. Read its own pages (website, App Store or shop page, booking or sign-up
page, social profiles) and write `product.md`.

- **For an app:** run `python3 $S/app-store.py fetch <App Store link> briefs/<slug>`. It gets the app's real name,
  price, icon and store screenshots into `assets/`, and prints the `brand` block for `post.json`. Then note:
  - what it does
  - the price model ("free to download, with Premium")
  - platforms
  - where its numbers come from (e.g. USDA)
  - its real store link
- **For a local business, club or service:**
  - its name and handle
  - where, when, and how much
  - how to join or book (the link)
  - what a newcomer should know ("no experience needed, sets provided")

Look in the repo for what's already known and made before you search the web:
- `briefs/` (earlier posts and plans for this product)
- the project's week plans in the research app (`curl -s localhost:8000/api/projects/<id>/plans`). Each plan's
  `input.about` is the team's own description of the product.

Earlier posts tell you what not to repeat. If you can't reach the product's pages, build `product.md` from those
sources, mark each line as the team's claim, leave unverified claims (like the price) off the slides, and ask the
person for the store link. Ask for whatever else you can't find. Don't fill gaps with guesses.

Sites go stale: in the Weight Class run the site still said "on its way" while the app was live. When the sources
disagree, say so.

## 2. Research the niche's slideshow outliers

The research app finds posts that beat their creator's follower count by 5× or more. It searches TikTok's Top
results (slideshows) and creators' feeds (Instagram carousels), then tears each one down slide by slide. Its README
(`research_app/README.md`) has the details.

```bash
python3 $S/research.py serve          # starts the app on :8000 if it isn't running; prints credits left
python3 $S/research.py projects       # is there a project for this niche already?
python3 $S/research.py new --name "Weight Class" --niche "calorie tracking app for iPhone" \
  --keywords "calorie deficit, high protein snacks, food swaps, what i eat in a day, calorie counting app" \
  --kinds slideshows,carousels --study "calai.app, myfitnesspal" --budget 400
python3 $S/research.py run <id>       # 10–40 min; prints progress
python3 $S/research.py teardown <id>  # tears down the slideshow and carousel outliers, 3 at a time
```

- **Reuse what's there.** If a project for the niche exists, check it has slide posts:
  `python3 $S/formulas.py refs <id> --out /tmp/x` reports how many. Many projects were researched for reels only. To
  add slide posts, switch them on (`research.py kinds <id> --kinds slideshows,carousels`) and run it again. Posts it
  already found are kept.
- **Keywords:** 6–10, in the audience's own words. Mix three kinds:
  - the problem ("calorie deficit")
  - the content people save in the niche ("high protein snacks", "food swaps")
  - the category ("calorie counting app")

  For a local business, add the city's own searches ("things to do in austin").
- **Post types:** `slideshows` (TikTok) is the core. Add `carousels` (Instagram) when the post will go out on
  Instagram too.
- **Study accounts** are Instagram handles: competitors' accounts and creators who grew fast in the niche. They're
  scanned deeper, whatever their size, but only when reels or carousels are on. A TikTok-only run finds its creators
  through search.
- **Credits:** one budget covers the whole run, and Instagram goes first. With carousels on, a tight budget can run
  out before the TikTok search starts, so size it for both.
  - **TikTok:** about 2 credits per keyword, plus about 2 per creator scanned. 10 keywords and 40 creators come to
    about 100 credits.
  - **Instagram:** about 3 per keyword, plus about 5 per creator, plus about 17 per study account. 10 keywords, 40
    creators and 10 study accounts come to about 400.
  - **Teardowns:** slideshows cost 0–1 credits each and carousels 1.
  - **For reference:** the Weight Class run (reels, carousels and slideshows, 40 creators, 10 study accounts) used 458
    credits in 28 minutes.
- **Ask before spending.** Before the first run, tell the person in plain words what you'll search, the credit cap,
  the expected spend and the credits left. Then wait for a yes. "Find what's working" asks for the outcome, not for
  permission to spend. Go straight ahead only when they've said to run the research or given a budget.
- **Keys:** the ScrapeCreators key lives in `.env` as `SCRAPECREATORS_API_KEY`. If it's missing, ask the person to add
  it there. Never ask anyone to paste a key into the chat. AI teardowns need the `claude` command or
  `OPENROUTER_API_KEY`; `research.py serve` prints which one is in use.
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

A formula is **proven** when **3+ posts from 2+ creators** won with it. One creator repeating a format shows it works
for them; several show it works for the niche. With only two posts it's a lead: one borderline post more or less can
move it from first place to fifth. Group every post, even into "other", so nothing is quietly left out. Write
`groups.json` (`{"Food swaps": ["<shortcode>", …]}`) and run:

```bash
python3 $S/formulas.py stats <id> groups.json --out briefs/<slug>/research/formulas.md
```

**Rank formulas by median saves per 1,000 plays, then by the number of creators.** Plays show reach, which one lucky
post can get. Saves show that people found it useful enough to keep, which is the feeling a product needs attached to
it.

`stats` marks leads and one-creator formulas. It also prints the patterns across every winner: slides, shape, cover
length, covers with a number, sound, the ask, sounds used by several winners, and promotions. Promotions are posts
marked as ads, campaigns posting one caption from many accounts, and app accounts. They prove a brand can ride a
format, but weigh them apart from creators' own posts. Those patterns feed step 5.

`formulas.md` opens with the metrics in plain words. Use those words when you explain them, because people ask:
- **Plays ÷ followers:** a 1,000-follower account whose post got 50,000 plays scores 50×.
- **The median across a formula's winners:** the middle one, so one freak hit can't carry a formula.
- **Saves per 1,000 plays:** how many of every thousand viewers kept it. TikTok shows saves; Instagram doesn't.

## 4. Pick one formula

Take the most-saved **proven** formula that also passes these. A lead can win only if it's far ahead. Then say how
thin it is and name the proven runner-up, so the person can choose the safer bet.
1. **Room for the product.** The product can be the honest answer to something the post raises (where the numbers
   come from, how to log it), not an ad bolted on.
2. **Every number can be checked now** from a primary source (step 7). Weight Class's fast-food formula had more
   winners, but the chains' nutrition pages couldn't be read, so swaps went first, with numbers from USDA.
3. **Makeable in a day** with phone photos and no filming.
4. **Not owned by competitors' own accounts.**
5. **Not already made or planned** (step 1).

Show the person the references. For each, give its slides side by side (`formulas.py sheet <shortcode> … --out
sheet.jpg`), plays, followers, ratio, saves per 1,000, slide count and what its numbers look like. Then say which
formula you picked and why, in a sentence they can disagree with.

## 5. Plan the post by recreating what won

Read `references/elements.md`. For every element (formula, cover words, number on the cover, cover photo, slide
layout, number format, photos, verdict line, page count, save ask, length, shape, the product, sound, caption, angle),
take the version that won and write down the post it came from and its numbers.

The point of combining is that each reference has a weak spot another one covers. Pair the cover of the post that
travelled furthest with the slides of the post that was saved most. When one post leads on both, keep its strengths
and fix its weak spots from the other references and the niche-wide patterns. Put the product once, on the last slide,
as the answer the post sets up.

**Don't copy what shouldn't be copied, however well it did.** In diet, fitness and body niches, leave out:
- thin-body covers ("thinspo")
- "lowest calorie" or extreme-deficit framing
- before/after bodies
- shame

Reframe on what helps: fullness, protein, swaps, convenience. Platforms limit that content anyway, and a brand has no
body to show. The same goes for any reference's unsourced claims: copy the layout, not the claims. Say what you
changed and why, and expect the reach to differ from the reference's.

## 6. Write the slides

Copy `assets/example/post.json` to `briefs/<slug>/post.json` and rewrite it. The format is in
`references/post-spec.md`. The slide types:
- `cover`
- `photo`: full-bleed with white text over it, how most winners build their slides
- `compare`: one swap, before and after
- `item`: a framed photo with number boxes under it
- `list`
- `app`

Pick the content slide that matches the references' layout.

- **One idea per slide, readable in two seconds:** a short title, numbers in big boxes, one verdict line.
- **Every photo spot gets a brief, a search and a source:**
  `{"key": "greek-yogurt", "brief": "…", "search": "greek yogurt nonfat plain", "src": "openfoodfacts"}`.
  - The brief says exactly what the person should shoot: the real product, held or on a counter, the label to camera
    when the label carries the number.
  - The search says what a real photo found online should show, in plain words for what it looks like.
  - The source says where to look: `openfoodfacts` for anything sold in a package, `commons` for unbranded food,
    places and scenes.

  Step 8 fills every spot from these, so the person sees finished slides, not empty boxes.
- **Verdict lines must be literally true.** "3 full cups, and still 56 fewer calories" can be checked; "three times
  the bowl" can't. Totals say what they total ("across all five", not "a day").
- **The last slide** (type `app`) shows the product doing what the post promises, in an image under `assets/`:
  - for an app, a real screenshot of it searching the food or logging the order
  - for a club, shop or service, a real photo of it, with when, where and how to join or buy in the subtitle

  If you only have a stand-in (say, a screenshot from the website), use it, mark it as one, and ask for the real
  image.
- **The product's name has to be in the pictures, not only in the caption.** Set `brand` in `post.json`; the
  Weight Class drafts went out without it and that was the miss. It puts the icon and name in a small tag on every
  content slide, the way MenuFit marked each slide of its 751K-play post. The app slide then opens with the icon and
  name big.
  - Use a real store screenshot that shows the name inside the app, usually the home screen. Cut it out of the store
    image with `app-store.py crop … --box x1,y1,x2,y2`.
  - Keep the cover clean: none of the winning app accounts branded their cover.

## 7. Check every number against a primary source

Every number on a slide must come from a source you actually read in this session. A wrong number on a saved post
draws correction comments for as long as people find it, and the product's slide vouches for those numbers.

- **Food:** USDA FoodData Central. `python3 $S/usda.py search "greek yogurt plain nonfat"`, then `usda.py show
  <fdc id>` for per-100 g and per-serving values. Choose the serving people actually eat: the size it's sold in or a
  common measure. Use USDA's weight for that serving when it lists one, or `--grams` with the weight printed on the
  slide. Keep the fdc ids for the write-up.
- **Rounding:** `usda.py` rounds half up to whole calories and grams. US labels round calories to the nearest 5 or 10,
  so a label in the photo may read 150 where the slide says 149. Decide which the slide shows, and say so in the
  write-up.
- **Restaurant orders:** the chain's own nutrition page or PDF. Third-party sites don't count.
- **Prices, product claims:** the store's or the product's own page.
- **Other facts** (food safety, how long things keep, health claims): a government or university extension page.
- **Can't verify it?** Drop the number, change the item, or change the angle. Never publish a guess, and say what you
  dropped.

Generic values won't match every brand. Tell the person to check each one against the label in their photo, and to
use the label's number if they differ.

## 8. Fill every photo spot with a real photo, render and review

Hand over finished slides with real photos of real products in them, not empty boxes. Real reference content is what
makes a slide look like the posts people save, and it lets the person judge the post as it will appear.

The best photos are still the person's own phone photos of the exact products: the most-saved references use them, and
the label in shot matches the slide. Until they shoot (or when they can't), fill every spot with **a real, licensed
photo found online. Never use a generated image.** This follows Editor V1's sourcing rules: find the thing's own
picture, choose it by looking, and record its source and licence.

```bash
python3 $S/find-photos.py fill briefs/<slug>       # searches every empty spot in post.json, one sheet per spot
#   -> briefs/<slug>/photo-search/<key>.jpg: numbered candidates with licence and size. Look at each sheet, then:
python3 $S/find-photos.py get briefs/<slug> --key greek-yogurt 7    # -> photos/greek-yogurt.jpg + photos/SOURCES.md
python3 $S/find-photos.py search "plain greek yogurt tub" briefs/<slug> --key greek-yogurt --src openfoodfacts  # retry one
python3 $S/find-photos.py label briefs/<slug> --key greek-yogurt 7  # that product's nutrition label photo, to check
python3 $S/find-photos.py collage briefs/<slug> --key cover --cols 3 greek-yogurt beef-93 skim-milk popcorn light-mayo
```

Look at every sheet before you pick, and at the filled slides after rendering. A title can lie about what a photo
shows. Match the look of the most-saved references: product photos when they show products, food on a plate when
they show food. If no licensed photo fits a spot, leave it empty and say which spot and why.

**Sources:**
- `openfoodfacts`: real packaged products (US first), mostly shoppers' phone photos, with a photo of each
  nutrition label (`find-photos.py label …`). Licence CC BY-SA 3.0.
- `commons`: Wikimedia Commons. Its Unsplash and Pexels imports (CC0, no credit needed) come first, then the rest.
  Best for unbranded food and scenes. It matches titles and descriptions, so search for the thing's plain name
  ("watermelon", "cucumber slices", "hard-boiled eggs"), not the brief's sentence. It rate-limits busy addresses: short
  waits are waited out, and a block of minutes skips to the next source, so try again later.
- `openverse`: wider, but slow and often down. Only when asked for (`--src commons,openverse`).

**Picking rules,** from filling the Weight Class swaps post:
- **Match the slide's serving** where you can: a 1 oz bag for "1 oz", one-cup cartons for "1 cup".
- **No number on the package may contradict the slide.** Skip a yogurt with a "150 calories" badge on a slide that
  says 173.
- **Prefer store brands.** If a famous brand's label differs from the slide by more than label rounding, pick
  another. Lay's Classic is labelled 160 calories per ounce against the slide's 149, so it was swapped for Kettle
  (150).
- **A same-brand pair** shows the difference best: Signature Farms 80/20 next to Signature Farms 93/7.
- **At least about 800 px** on the long side. `get` warns when a photo will look soft.
- **No identifiable people** in found photos. A stranger's face in an ad needs their consent, which a licence doesn't
  give. Food, products, hands and places are fine.
- **Covers:** when no single found photo fits the cover, `collage` makes one from the post's own photos. Both
  Weight Class posts used one until the person shoots the real cover.
- **Crops:** use `"focus": "50% 20%"` on a photo spot to move the crop, and `"shade": 0.8` on a busy cover to keep
  the title readable.

**Credits and risks to tell the person:**
- **Credits:** `photos/SOURCES.md` lists every photo's source and licence. CC BY and CC BY-SA need a credit in the
  caption; `find-photos.py credits briefs/<slug>` writes the line ("Photos: Open Food Facts contributors (CC BY-SA
  3.0)"). CC0 and public-domain photos need none. CC BY-SA also asks that what's made from the
  photo is shared under the same licence.
- **Brands:** showing named brands from a brand account is comparative advertising, so the numbers must be right for
  what's pictured. Their own photos avoid both issues; say so.

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
   (each slide's items and numbers). Where every number comes from (source, id, serving weight). Where every photo
   comes from: which spots hold found photos (from `photos/SOURCES.md`, with licences) and which are the person's own,
   plus anything still a stand-in.
3. **Why we think it will work.** The weak-spot logic (step 5), then a table: Element | What we do | Taken from (linked)
   | The evidence. Then what could go wrong: sample sizes, account type, generic numbers against labels, and that a
   sound is a correlation, not a cause.
4. **How to post it.**
   - The shot list (photo key → what to shoot), to replace the found photos with their own when they can.
   - Check the numbers against the labels.
   - Replace the app screen, then rebuild with `render.py`.
   - Post as a TikTok photo post and an Instagram carousel the same day.
   - The sound. TikTok's original sounds don't carry over to Instagram, so pick a quiet song there.
   - The caption: one line, first person only if it's true, plus 4–5 hashtags. While found CC BY or CC BY-SA
     photos are in, end it with their credit ("Photos: Open Food Facts contributors, CC BY-SA 3.0").
   - An App Store campaign link in the bio.
   - Correct numbers in the comments and pin the correction.
5. **What to measure, and what to do next.**
   - Saves per 1,000 plays at 48 hours and 7 days, against this formula's references. Use their range; for Weight
     Class swaps that was 27–49. Under about 5 means watched, not kept.
   - Plays ÷ followers (5× is an outlier).
   - Profile visits and installs from the campaign link.
   - Next: saves high → a second post in the same layout. Reach high but saves low → the content isn't worth keeping.
     Both low → post the same slides from a creator's account.

**Sending drafts.** When the person asks for drafts and has an Outstand key (`OUTSTAND_API_KEY` in `.env`), send
the post to TikTok as a photo draft:

```bash
python3 $S/send-drafts.py accounts                        # the connected accounts (the same one can appear twice)
python3 $S/send-drafts.py send briefs/<slug> --account <id> --caption-file briefs/<slug>/caption.txt
python3 $S/send-drafts.py send briefs/<slug> --account <id> --caption-file … --video briefs/<slug>/out/reel.mp4
```

- **Drafts only.** The slides go to the account's TikTok inbox as a draft (`MEDIA_UPLOAD`). Nothing is public until
  the person adds the sound and posts it in the app.
- **Other networks are refused,** because there they would publish for real.
- **The caption** goes in `caption.txt`: the line, the hashtags, then the photo credit line.
- **Check delivery.** The result is saved to `out/drafts.json`. Each account in the post should read
  `status: published` with an inbox id (`p_inbox_url~…` for slides, `v_inbox_url~…` for a video).
- **The key:** if it's missing, ask the person to add it to `.env`, never to paste it.

Zip the post folder and send it with the file tool when you have one. Finish with a few lines in chat: what the post
is, why it should work, and what the person does next (usually: take the photos, drop them in `photos/`, run
`render.py`).

## When the person brings a video

Sometimes the person brings a clip instead of asking for slides: their own before/after, a talking clip, a voiceover.
Don't design an edit around it. Match it to the research's winning videos and edit it the way they're edited.
`references/video-layouts.md` has the scoring, the evidence for each layout and every key.

```bash
python3 $S/match.py briefs/<slug>/assets/clip.mp4 --post briefs/<slug> --project <id>
#   -> match/matches.md (the matches, their numbers and how each is made), match/sheet.jpg, reel.suggested.json
python3 $S/reel.py briefs/<slug>          # reads briefs/<slug>/reel.json -> out/reel.mp4 (9:16) and out/reel-preview.jpg
python3 $S/send-drafts.py send briefs/<slug> --account <id> --caption-file briefs/<slug>/caption.txt \
  --video briefs/<slug>/out/reel.mp4
```

1. **Match.** `match.py` transcribes the clip, has the research app's AI describe it in the teardowns' own terms,
   and ranks every torn-down reel and Short by format, rare shared traits (a "transformation" angle), subject, length
   and pace. Look at `match/sheet.jpg`: drop a match whose frames look nothing like the clip, whatever its score.
2. **Pick the layout the matches use.**
   - `text`: no talking. A hook box above the clip, lines joining later, music added in the app. The body-turn
     reveal is this layout, slowed and with wall added above the head (`references/reel.md`).
   - `talking`: framed on the face, pauses cut, word-by-word captions, the hook on top, b-roll over the voice. A
     voiceover is this with b-roll over most of it.
   - `green-screen`: the person cut out, chest up, in front of the screenshots or photos they talk about.
3. **Write reel.json** from `reel.suggested.json`.
   - The hook follows the winners' pattern, with what's true for this clip.
   - The captions copy the matches' style.
   - B-roll and backgrounds are real: the person's own, the product's screenshots, or licensed photos.
   - Work through the `_check` list, then delete it.
   - For a talking clip, read `out/work/words-<clip>-*.json` and fix misheard names, capitals and punctuation.
   - Write where every clip, photo and background came from in `assets/SOURCES.md`.
4. **Check** `out/reel-preview.jpg` and `out/reel-strip.jpg` (one frame a second), then have the person watch it
   with the sound on.
5. **Caption and send.** The caption copies the matches' ask (`matches.md` lists each one). Send the video as a
   draft.

- No watermark on the clip. The product closes the video with its logo, like TikTok's end card (`end_card`).
- Timeframes, lists and results are the person's own words. If any of the clip is made with AI, the caption says so
  and the post gets TikTok's AI-generated label.
- Don't credit the product for a result that came before it.
- The first match or talking build sets up the video tools (about 1.3 GB, one time).

## When the person comes back with photos

Put them at `briefs/<slug>/photos/<key>.jpg` (the keys are in `post.json`), replacing the found photo, and delete that
key's row from `photos/SOURCES.md` (their own photo needs no credit). Then run `render.py`. Check each filled slide
at full size: crop, readability of the text over the photo, the label in shot. If a product's label disagrees with the
slide, change the number and its verdict line in `post.json`, then render again.
