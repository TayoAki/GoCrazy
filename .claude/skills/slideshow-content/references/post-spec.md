# post.json: the slide spec `render.py` reads

One file per post, in the post's folder (`briefs/<slug>/post.json`). The worked example is
`assets/example/post.json` (the Weight Class food-swaps post). Copy it and change it rather than starting blank.

```json
{
  "title": "5 easy swaps that actually save calories",
  "size": [1080, 1440],
  "theme": {"accent": "#2340B0", "muted": "#5B6475"},
  "save_line": "↓ SAVE THIS FOR YOUR NEXT GROCERY RUN ↓",
  "source_line": "Per serving · USDA FoodData Central",
  "counter": true,
  "slides": [ ... ]
}
```

| Key | Meaning |
| --- | --- |
| `size` | Pixels. 3:4 is `[1080, 1440]` (the default: TikTok photo posts show it whole and Instagram takes it uncropped). 4:5 is `[1080, 1350]`, 9:16 is `[1080, 1920]`. Match what the references use |
| `theme` | Any of `accent` (boxes, highlights), `muted` (the "before" boxes), `ink`, `paper`, `soft` (app slide background), `no` / `yes` (the INSTEAD OF / SWAP TO labels), `faint` (page count). Use the brand's colour for `accent` if it reads well as white-on-colour |
| `save_line` | The save ask. It appears on slides with `"save": true` (usually the cover and the last slide) |
| `source_line` | Small grey line under every `compare` and `item` slide saying where the numbers come from. A slide's own `"source"` overrides it (`""` hides it) |
| `counter` | The `n/N` page count top right (default on) |
| `brand` | `{"name": "Weight Class", "icon": "assets/app-icon.png", "where": "Free on the App Store"}`. It puts the product's icon and name, small, top left on every content slide. The app slide also opens with the icon and name big, and `where` under it. `on` lists the slide types that get the small tag (default `photo`, `compare`, `item`, `list`; the cover stays clean). `text` replaces the name in the small tag |

## Text

- `*word*` highlights: on the cover it puts the words in an accent box, elsewhere it colours them.
- A newline (`\n` in JSON) is a line break you choose. Lines are balanced automatically, and hyphenated words
  ("HIGH-PROTEIN") never split, but put the break yourself whenever a title reads better split at a phrase
  ("POTATO CHIPS →\nAIR-POPPED POPCORN").
- Keep every slide readable in two seconds: a title under about 8 words, numbers in the boxes, one verdict line.

## Photo spots

Wherever a slide takes a photo:

```json
{"key": "greek-yogurt", "brief": "a Greek yogurt cup with berries on top",
 "search": "greek yogurt nonfat plain", "src": "openfoodfacts", "focus": "50% 40%"}
```

- `brief`: what the person should shoot.
- `search` and `src`: what a real photo found online should show, and where `scripts/find-photos.py fill` looks for
  it. Use `openfoodfacts` for anything sold in a package, and `commons` for unbranded food, places and scenes. Write
  the search as the thing's plain name ("hard-boiled eggs"), not a sentence.
- `focus` (optional): moves the crop.

- Until `photos/<key>.jpg` (or `.jpeg`, `.png`, `.webp`) exists, the spot renders as a dashed PHOTO box showing the
  brief, so the person sees exactly what to shoot and where it goes. `render.py` lists the empty spots.
- Write the brief as a shot: the real product, how it's held or placed, what must be readable ("label to camera").
- Keys are file names: lowercase, hyphens, unique per photo. Reuse a key to reuse a photo.
- `"focus": "50% 20%"` moves the crop (CSS object-position: across, then down). Photos fill their spot and are
  cropped to it, so aim the focus at the label or the food.
- Fill spots with the person's photos, or with real licensed ones from `scripts/find-photos.py` (never generated
  images). See SKILL.md step 8.

## Slide types

### `cover`
```json
{"type": "cover", "title": "5 easy swaps that *actually* save calories",
 "subtitle": "368 fewer calories and 16 g more protein across all five. Same meals.",
 "photo": {"key": "cover", "brief": "COVER: your grocery haul in the car boot, phone photo"},
 "save": true, "title_size": 112}
```
Full-bleed photo with a dark gradient, the title big in white capitals at the top, the subtitle and the save line at the
bottom. Lower `title_size` (px) when a long title runs past four lines. `shade` (0–0.9, default 0.55) darkens the top
of the gradient; raise it when the photo is busy behind the title (a collage needs about 0.8).

### `photo`: full-bleed photo, white text over it
```json
{"type": "photo", "photo": {"key": "cucumber", "brief": "one whole cucumber, sliced, in a white bowl, from above"},
 "title": "CUCUMBER", "lines": ["1 whole cucumber · 301 g"], "stats": [["45", "CAL"], ["2 G", "FIBER"]],
 "verdict": "The whole thing: *45 calories*", "text_at": "top"}
```
How most winning slideshows are built: the photo fills the slide and the text sits on it, with a dark gradient
for legibility. Text goes at the top (default) or the bottom (`"text_at": "bottom"`); put it where the photo is
empty. All text fields are optional. A slide with number boxes gets the source line.

### `compare`: one swap, before above after
```json
{"type": "compare", "title": "FRUIT YOGURT →\nGREEK YOGURT",
 "before": {"name": "Fruit low-fat yogurt", "serving": "6 oz", "stats": [["173", "CAL"], ["7 G", "PROTEIN"]],
            "photo": {"key": "fruit-yogurt", "brief": "a fruit yogurt cup, label to camera"}},
 "after":  {"name": "Plain nonfat Greek yogurt", "serving": "6 oz", "stats": [["100", "CAL"], ["17 G", "PROTEIN"]],
            "photo": {"key": "greek-yogurt", "brief": "a Greek yogurt cup with berries on top"}},
 "verdict": "73 fewer calories and 10 g more protein"}
```
`before` / `after` take an optional `label` (default INSTEAD OF / SWAP TO, e.g. "BEFORE" / "AFTER", "❌" / "✅").
`stats` is a list of `[big value, small unit]` boxes; leave out what doesn't apply (mayo has no protein box).

### `item`: one thing per slide (an order, a meal, a product, a tip with a photo)
```json
{"type": "item", "title": "CHICK-FIL-A",
 "photo": {"key": "cfa", "brief": "the 12-count grilled nuggets, opened on the passenger seat"},
 "name": "12-ct Grilled Nuggets", "stats": [["200", "CAL"], ["38 G", "PROTEIN"]],
 "notes": ["+ Zesty Buffalo sauce", "no fries"], "verdict": "The most protein per calorie on the menu"}
```
A big photo, then the name, the number boxes, short notes (the order's changes, the recipe's swaps) and a verdict. Every
field but `photo` is optional.

### `list`: a text slide
```json
{"type": "list", "title": "How to *order* it", "lines": ["Ask for grilled, not fried", "Sauce on the side"],
 "photo": {"key": "menu", "brief": "the menu board"}, "save": true}
```
Numbered lines, with an optional photo strip above. Use it for steps, rules or a recap. It gets no source line
unless the slide sets `"source"`.

### `app`: the product, once, last
```json
{"type": "app", "title": "Check any swap yourself", "screen": "assets/app-home.jpg",
 "screen_brief": "the app's food search on a phone",
 "subtitle": "Every number here is a USDA entry. Search it in Weight Class, free on iPhone.", "save": true}
```
With a `brand`, the slide opens with the icon and name (`"brand_header": false` turns that off). `screen` is an
image path relative to the post folder. For an app, use a real screenshot of it doing the thing the
post promises (searching the food, logging the order). For a club, shop or service, use a real photo of it, and put
when, where and how to join in the subtitle. Without it the slide shows a placeholder with `screen_brief`. The
title says what the product does for this post's reader, not the product's slogan.

## Output

`python3 scripts/render.py briefs/<slug>` writes `out/slide_01.png` … and `out/contact.jpg` (every slide at a
glance, 4 to a row). It rewrites `out/` each time, so edit `post.json`, never the PNGs.
