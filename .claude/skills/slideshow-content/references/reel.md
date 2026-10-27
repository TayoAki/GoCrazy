# The body-turn reel: a person's real before/after, in the format that won

When the person brings a video instead of asking for slides, match it to the research by **format**, not topic. A
before/after of their own body is not a slideshow and not a talking head. Find the outliers that show the same
thing, then copy their layout: where the text sits, what it says, how long each state stays on screen, and what the
caption asks for. Don't invent a new layout around it. `scripts/reel.py` builds this one.

## The evidence (Weight Class research, October 2026)

| Post | What it is | Numbers |
| --- | --- | --- |
| @movementwithjulie `DdcQd7MATse` | Turns front, side and back, before, then one cut to after. 19 s, music only. Black box at the top: "I gave myself 365 days, and this is what happened..."; a second line, "here's 10 things I did", joins later | 669,614 views on 685,309 followers (1.0×), **6,096 comments** (9.1 per 1,000 views): the caption's "comment DB WORKOUTS" ask |
| @movementwithjulie `DdNbFOgurK2` | The same before/after cut on a workout. 19 s, music only, "it doesn't feel like it working until..." | 1,183,195 views (1.7×), 3,800 comments, same comment-keyword ask |
| kaylahannprice (YouTube Short `Ivoqvv766CY`) | Mirror photos month by month, with a month label and her scale app's screen. 131 s | 366,601 views, 8.1× the channel's typical Short, 2,800 comments |
| LoveSweatFitness, mochi.muscles (YouTube Shorts) | 6–9 s before/after Shorts ("We lost 90 pounds but here's where we started…", "same body different times"). Not torn down: known from caption and length only | 3.4×, 6.6× and 3.1× their channels' typical Short |

What that says: three torn-down posts from two creators (the skill's bar for a proven formula) share the shape, plus
three short Shorts whose captions say the same thing. On Instagram it is a **comments** format more than a reach
format: Julie's posts hit about 1–1.7× her followers but pulled thousands of comments, because the caption lists what
she did and asks for a keyword. On YouTube Shorts the short before/afters beat their channels by 3–7×.

## The layout `reel.py` builds

1. **The person's real clip, full width, untouched.** No crop into the body, no filter. Slowed so each state reads:
   2× by default, with motion-interpolated in-between frames (not repeated ones). Julie holds each state about 9.6 s;
   an 8 s clip at normal speed flips too fast to read.
2. **The hook in a small black box on plain wall above the head**, white bold text, at 200 px or lower: TikTok's and
   Instagram's top bars cover the top ~180 px. When the head is at the top of the frame, `headroom` moves the clip
   down and fills the gap with the clip's own wall, blurred and faded in.
3. **A second line** in a white box under it, about a third of the way in: "↓ here's the N things I did ↓". N is
   what the caption lists.
4. **No watermark on the clip.** The product closes the video instead, like TikTok's end logo: the mark pops in
   with a cyan and red split, then the name and where to get it rise in under it (2.5 s). A light mark on a plain
   dark icon is cut out and shown on the icon's own colour; any other icon is shown whole on black.
5. **Silent.** The music is added in the app, so it's a sound people can tap through to. Julie's are music only.

## The caption: the second half of the format

```
There are 365 days between these two videos.

Here's what I did for the whole year:
1. Cut calories
2. Lifted 4x a week

That's it. Two things, every week, for a year.

<one or two lines on where the product fits, honest about what it does>

Save this for your day 1 👇

Before and after are real photos; the turn between them is made with AI.

#transformation #fatloss #caloriedeficit #strengthtraining #weightloss
```

- **The timeframe and the list are the person's, word for word.** Ask for them; never fill them in. Julie's list has
  ten items. A short true list beats a long made-up one.
- **The ask.** Julie's comment keyword ("comment DB WORKOUTS and I'll send you the plan") is what drove her comments.
  Use it only when the person has a way to send the thing (a comment-to-DM tool or time to answer by hand).
  Otherwise ask for the save.
- **Don't credit the product for a result it didn't cause.** If the transformation happened before the product
  existed, say how the product helps with the hard part now ("counting calories is the part most people quit"),
  not that it did this.

## Rules

- **Real footage only.** The before and after must be the person's own photos or video. If the turn between them is
  made with AI, say so in the caption and switch on TikTok's AI-generated content label when posting.
- **Real numbers only.** Timeframe, weight, what they did: from the person, nothing estimated.
- **Check the pixel shape.** Scaling and stacking can leave a non-square sample aspect ratio, which players show
  stretched. `reel.py` forces 1:1 and refuses to finish otherwise; check any other edit with
  `ffprobe -show_entries stream=sample_aspect_ratio`.
- **Look at it before sending:** a frame from the start, one after the second line appears, and one from the end
  card. Text below the top bars, nothing over the face, the end card readable.

## Build it and send it

```bash
# briefs/<slug>/reel.json (every key but video and hook is optional; the defaults are shown)
{"video": "assets/clip.mp4", "hook": "I gave myself 365 days, and\nthis is what happened...",
 "second_line": "↓ here's the 2 things I did ↓", "second_line_at": 0.33, "slow": 2.0,
 "headroom": 340, "text_top": 200,
 "end_card": {"icon": "assets/app-icon-1024.png", "name": "Weight Class", "where": "Free on the App Store",
              "seconds": 2.5}}

python3 $S/app-store.py fetch <app> briefs/<slug>          # the real icon, including assets/app-icon-1024.png
python3 $S/reel.py briefs/<slug>                            # -> out/reel.mp4, 1080x1920, 30 fps, silent audio track
python3 $S/send-drafts.py send briefs/<slug> --account <id> --caption-file briefs/<slug>/caption.txt \
  --video briefs/<slug>/out/reel.mp4
```

- `second_line_at` is a fraction of the slowed clip (0.33) or, above 1, seconds.
- `headroom: 0` keeps the clip where it is and puts the hook over it; use it when there's already wall above the head.
- `slow: 1` keeps the original speed; use it when each state already holds for a few seconds.
- Leave out `end_card` for no closing logo (a creator's own transformation with no product).
- The build takes about 4 minutes for an 8 s clip slowed 2×: motion interpolation is the slow part.

The worked example is the Weight Class flip reel: an 8 s clip of Ty's own before and after photos, with an AI turn
between them, built with the `reel.json` above (and `"second_line_at": 5.3`).
