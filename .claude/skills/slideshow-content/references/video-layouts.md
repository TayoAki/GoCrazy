# Videos: match the person's clip to the outliers, then edit it their way

When the person brings a video, don't design an edit around it. Find the winning videos in the research that look
like it, and copy how they're made: where the text sits and what it says, the captions, the pace, the length, the
sound and the ask. `scripts/match.py` finds them; `scripts/reel.py` builds the edit in one of three layouts.

## 1. Match it

```bash
python3 $S/match.py briefs/<slug>/assets/clip.mp4 --post briefs/<slug> --project <id>   # about a minute
```

It measures the clip (length, shape, shot changes, and the speech, which it transcribes), then has the research
app's AI describe it with the same instructions every outlier got, so the two are described in the same words:
format, audio, angle, video type, delivery, story and hook pattern. Then it scores every torn-down reel and Short:

- **The same format counts most** when the person talks, because the format decides the edit: a talking head and a
  green screen are cut differently. With no talking, "talking head" and "visual prop" both just mean a person on
  screen, so the whole on-camera family counts nearly as much.
- **Shared traits count by how rare they are.** "Transformation" (12 of 264 videos) says far more about two videos than
  "tip/hack" (125 of 264).
- **Then the subject** (shared words in the topic, summary and caption), **length and pace**, **this niche**
  (`--project`), and **how far the post beat its creator**.

It writes:

- `match/matches.md`: each match's numbers, score and why it matched, its on-screen and spoken hooks, captions,
  structure, sound and ask, then what the top matches have in common.
- `match/sheet.jpg`: the person's frames on top, each match's frames below. Look at it: a match whose frames look
  nothing like the clip is a weak one, whatever its score.
- `reel.suggested.json`: a starting `reel.json` in the layout that fits, with the winners' hooks listed to write from.
  The hook itself is left blank: write it in their pattern, from what's true about this clip.

`match/video.json` keeps the description. With no AI set up (no `claude` command, no `OPENROUTER_API_KEY`), or with
`--no-ai`, it writes the frames and the instructions to `match/describe.md`: look at the frames, write
`match/video.json` yourself and run it again. `--fresh` describes the clip again.

On the Weight Class research, it put @movementwithjulie's two before/after reels first for Ty's flip video, the same
outlier found by hand, and a talking clip got talking-head winners.

**Matches come from the niches that were researched.** A clip about something the research never covered gets
matches by format only (the subject scores near zero). For a new niche, run the research first (SKILL.md step 2).

## 2. The three layouts

The research's 264 torn-down videos, by the layout that edits them:

| Layout | Formats it covers | Posts | Creators | Median views ÷ followers | How they're made |
| --- | --- | --- | --- | --- | --- |
| `talking` | talking head, setting change, shot change, visual prop, multitasking, Q&A | 133 | 76 | 7.4× | 125 of 133 put a hook on screen. Of the 102 with speech, 46 have word-by-word captions. Median 61 s, a shot every 6 s |
| `talking` + b-roll | voiceover | 39 | 25 | 11.7× | 36 of 39 put a hook on screen. Voice over footage of the thing; 10 of 30 caption word by word |
| `green-screen` | green screen | 53 | 21 | 9.9× | 45 of 52 caption word by word (white bold with a black outline, centred). Median 32 s, the picture behind changes every 2 s |
| `text` | text over b-roll (and a music-only visual, like the body turn) | 27 | 11 | 10.0× | Music only in 19 of 27. One clip and one held block of text, median 7 s |

The rest (reaction, clone, talking back and forth, whiteboard) have no layout: 12 posts.

## 3. reel.json

Every layout reads these:

| Key | Meaning |
| --- | --- |
| `layout` | `text` (default), `talking` or `green-screen` |
| `video` | The person's clip, relative to the post folder |
| `trim` | `[start, end]` in seconds of the clip: use only this part |
| `hook` | The on-screen hook. `\n` breaks the line where you choose |
| `hook_style` | `box` (black box, white text: Julie's), `white-box` (white box, black text) or `outline` (big white bold with a black outline) |
| `hook_size` | Px. Defaults: 38 in `text` (a small box, like Julie's), 46 otherwise. 60–70 suits `outline` |
| `hook_seconds` | Take the hook off after this long (a fraction of the clip up to 1, else seconds). Default: on the whole time |
| `text_top` | Px from the top. Keep 200 or more: TikTok's and Instagram's top bars cover about 180 |
| `lines` | `[{"text": "↓ here's the 2 things I did ↓", "at": 0.33}]`: white boxes that join under the hook. `at` is a fraction of the finished clip up to 1, else seconds. `second_line` / `second_line_at` is the one-line shorthand |
| `end_card` | `{"icon": "assets/app-icon-1024.png", "name": "Weight Class", "where": "Free on the App Store", "seconds": 2.5}`: the product's closing logo, like TikTok's end card. Leave it out for no logo |

### `text`: a clip with no talking

| Key | Meaning |
| --- | --- |
| `slow` | 2 plays it at half speed, with motion-interpolated in-between frames. Default 1 |
| `headroom` | Px of wall added above the head (the clip's own top rows, blurred and faded in), so the hook sits on wall instead of over the head. Default 0 |
| `keep_audio` | `true` keeps the clip's own sound (only at `slow: 1`). Default: silent, and the music goes on in the app |

The clip is cropped to the centre of the 9:16 frame, so film it upright. The body-turn reveal is this layout with
`slow: 2` and `headroom: 340` (references/reel.md).

### `talking`: the person talks to camera (or over b-roll)

| Key | Meaning |
| --- | --- |
| `crop` | `"face"` (default: frames 9:16 on the face it finds), `"center"`, or `{"x": 0.3, "y": 0.4}` (where the face is, as fractions) |
| `zoom` | Crop in further. 1 by default. Above 1 it enlarges the footage, and a 720p source gets soft past about 1.3 |
| `cut_pauses` | Cut every pause longer than this (seconds), a jump cut, the way talking heads are edited. Default 0.5; `0` keeps everything |
| `captions` | Word-by-word captions, or `false` for none. `words` per screen (3), `style` `outline` or `box`, `at` (the height as a fraction: 0.66 for `talking`, 0.52 for `green-screen`), `size` (64 px), `highlight` (words in the accent `color`, `#FFD400`; numbers always are), `active` (a colour for the word being said), `upper` (capitals) |
| `broll` | `[{"src": "assets/meal.jpg", "at": 12.4, "seconds": 2}]`: a photo or clip cuts in full-frame over the voice. `at` is in the clip's own time (read it off the transcript); `focus` moves a photo's crop; `from` starts a clip part-way. A voiceover is this with b-roll over most of it |
| `language`, `model` | For the transcription: a language code (default: detected) and the Whisper model (`small`) |

The speech is transcribed first, to `out/work/words-*.json`: every word with its start and end in the clip's own
time. **Read it, and fix misheard names** ("Mark van de Hyde" for "Mark Vande Hei", product names), keeping the
times. The captions come from it, and the fixed file is kept until the clip changes.

The voice is levelled to -14 LUFS, the loudness TikTok and Instagram play at.

### `green-screen`: the person cut out in front of what they're talking about

Everything in `talking`, plus:

| Key | Meaning |
| --- | --- |
| `backgrounds` | `[{"src": "assets/screenshot.png", "at": 0}, {"src": "assets/photo.jpg", "at": 9.5, "fit": "cover"}]`: each from its time (clip time) until the next. `fit` is `top` (default: shown whole under the hook, over a blurred copy, for screenshots) or `cover` (fills the frame, for photos) |
| `speaker` | `face` (default 0.12: the face is 12% of the frame's height, chest up, as green-screen creators film themselves), `x` and `y` (where the face sits; default 0.5 and 0.66). `{"height": 0.58}` instead sets a fixed size |

The cut-out is MediaPipe's selfie segmentation. It's cleanest with a plain wall behind the person; clutter beside
them can come along with them.

## 4. Rules

- **Real footage, real claims.** The clip is the person's own. B-roll and backgrounds are their photos, the
  product's own screenshots, or licensed ones (find-photos.py), never generated. Anything made with AI is said in the
  caption, and the post gets TikTok's AI-generated label.
- **The hook is true for this clip.** Copy the winners' pattern ("I gave myself 365 days…", "POV: …"), not their
  facts.
- **Check before sending.** `out/reel-preview.jpg` shows six moments. Make a strip of one frame a second
  (`ffmpeg -i out/reel.mp4 -vf "fps=1,scale=180:320,tile=8x4" -frames:v 1 strip.jpg`) to check every caption and
  cut, then watch it with the sound on: captions in time, no cut in the middle of a word, the hook clear of the
  face.
- **Sound.** `text` reels are silent unless `keep_audio`: add the music in the app, so it's a sound people can tap
  through to. Talking reels keep the voice; a quiet track can go under it in the app.

## Setup

The first `talking` or `green-screen` build, or the first match, makes the video tools' Python environment at
`~/.cache/slideshow-content/venv` (Python 3.11 with faster-whisper and MediaPipe, about 1.3 GB), with `uv` when it's
installed. Whisper's model downloads on first use (about 500 MB). Building a 30 s talking or green-screen reel
from a 45 s clip took about 2 minutes on a cloud CPU the first time, and under a minute when only the text changed
(the transcript, the cut and the cut-out are kept in `out/work/`).
