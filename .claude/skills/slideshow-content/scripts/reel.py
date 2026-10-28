"""Build a reel from the person's own footage, in the layout the matched outliers use (match.py finds them).

    python3 reel.py <post folder>          # reads <post>/reel.json, writes <post>/out/reel.mp4 and out/reel-preview.jpg

Layouts ("layout" in reel.json), each taken from what the winning posts in the research do:
- "text" (the default): a clip with no talking. The hook sits in a box above it, more lines join later, and the music
  is added in the app. The body-turn reveal is this layout, slowed, with wall added above the head (references/reel.md).
- "talking": the person talks to camera. Framed 9:16 on their face, pauses cut, word-by-word captions, the hook on
  top, and b-roll (photos or clips) cutting in over the voice. A voiceover is this layout with b-roll over most of it.
- "green-screen": the person, cut out, stands at the bottom of the frame in front of the screenshots or photos they
  talk about, with captions and the hook.
Any layout can close on the product's logo, like TikTok's end card ("end_card"). Every key, with the evidence for each
layout, is in references/video-layouts.md.

The talking layouts transcribe the speech first (out/work/words-*.json, kept between runs); fix misheard names there.
"""

import base64
import html
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from videokit import face as find_face, key, probe, vision, words as transcribe  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent
FONTS = SKILL / "assets/fonts"
W, H, FPS = 1080, 1920, 30
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
LAYOUTS = ("text", "talking", "green-screen")
OUTLINE = "0 0 3px #000," + ",".join(f"{x}px {y}px 0 #000" for x in (-4, -2, 0, 2, 4) for y in (-4, -2, 0, 2, 4)) \
          + ",0 6px 16px rgba(0,0,0,.55)"


def font(weight):
    data = base64.b64encode((FONTS / f"Inter-{weight}.woff2").read_bytes()).decode()
    return f"@font-face{{font-family:Inter;src:url(data:font/woff2;base64,{data}) format('woff2');font-weight:{weight}}}"


def text(s):
    return html.escape(s or "").replace("\\n", "\n").replace("\n", "<br>")


def browser(p):
    return p.chromium.launch(executable_path=CHROME if Path(CHROME).exists() else None)


def run(cmd):
    subprocess.run(cmd, check=True)


def duration(path):
    return probe(path)["duration"]


def when(at, length):
    """A time given as a fraction of the clip (up to 1) or in seconds."""
    at = float(at)
    return at * length if at <= 1 else at


# --- the hook and the lines that join it --------------------------------------------------------------------------

def hook_css(spec, layout):
    style = spec.get("hook_style", "box")
    size = spec.get("hook_size", 38 if layout == "text" else 46)
    b1 = {"box": f"background:#000;color:#fff;font:700 {size}px/1.22 Inter;padding:8px 18px;border-radius:8px",
          "white-box": f"background:#fff;color:#111;font:700 {size}px/1.22 Inter;padding:8px 18px;border-radius:8px",
          "outline": f"color:#fff;font:900 {size}px/1.15 Inter;text-shadow:{OUTLINE}"}[style]
    return f"""{font(700)}{font(900)}*{{margin:0;padding:0}} html,body{{background:transparent;width:{W}px;height:{H}px}}
    .wrap{{position:absolute;top:{spec.get('text_top', 200)}px;left:0;right:0;display:flex;flex-direction:column;
          align-items:center;gap:12px}}
    .b1{{{b1};text-align:center;max-width:{spec.get('hook_width', 920 if style == 'outline' else 700)}px}}
    .b2{{background:#fff;color:#111;font:700 34px Inter;padding:6px 16px;border-radius:8px}}"""


def hook_states(out, spec, layout, length):
    """Overlays: the hook alone, then the hook with each extra line as it joins. Returns [(png, start, end)]."""
    from playwright.sync_api import sync_playwright
    lines = list(spec.get("lines") or [])
    if spec.get("second_line"):
        lines.insert(0, {"text": spec["second_line"], "at": spec.get("second_line_at", 0.33)})
    if not spec.get("hook") and not lines:
        return []
    lines = sorted(({"text": l["text"], "at": when(l["at"], length)} for l in lines), key=lambda l: l["at"])
    stop = when(spec["hook_seconds"], length) if spec.get("hook_seconds") else None
    starts = [0.0] + [l["at"] for l in lines]
    states = []
    with sync_playwright() as p:
        b = browser(p)
        page = b.new_page(viewport={"width": W, "height": H})
        for k, start in enumerate(starts):
            if stop is not None and start >= stop:
                break
            body = '<div class="wrap">' + (f'<div class="b1">{text(spec["hook"])}</div>' if spec.get("hook") else "") + \
                   "".join(f'<div class="b2">{text(l["text"])}</div>' for l in lines[:k]) + "</div>"
            page.set_content(f"<!doctype html><html><head><meta charset='utf-8'><style>{hook_css(spec, layout)}</style>"
                             f"</head><body>{body}</body></html>")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(100)
            png = out / f"hook{k + 1}.png"
            page.screenshot(path=str(png), omit_background=True)
            end = starts[k + 1] if k + 1 < len(starts) else None
            if stop is not None:
                end = min(end, stop) if end is not None else stop
            states.append((png, start, end))
        b.close()
    return states


def hook_filters(states, first_input, src, dst):
    """Overlay chain for hook_states, from stream `src` to `dst`."""
    if not states:
        return f"[{src}]null[{dst}];", []
    fc, inputs, cur = "", [], src
    for k, (png, start, end) in enumerate(states):
        inputs += ["-i", str(png)]
        cond = [f"gte(t,{start:.2f})"] if start > 0 else []
        cond += [f"lt(t,{end:.2f})"] if end is not None else []
        enable = f":enable='{'*'.join(cond)}'" if cond else ""
        nxt = dst if k == len(states) - 1 else f"h{k}"
        fc += f"[{cur}][{first_input + k}:v]overlay=0:0{enable}[{nxt}];"
        cur = nxt
    return fc, inputs


# --- the closing logo ----------------------------------------------------------------------------------------------

def end_card(folder, card, post):
    """The closing logo, frame by frame. A light mark on a plain dark icon is cut out and shown on the icon's own
    background (so the square disappears, like TikTok's note); any other icon is shown whole on black."""
    from playwright.sync_api import sync_playwright
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    icon = Image.open(post / card["icon"]).convert("RGB")
    corners = [icon.getpixel(xy) for xy in ((4, 4), (icon.width - 5, 4), (4, icon.height - 5), (icon.width - 5, icon.height - 5))]
    bg = corners[0]
    plain_dark = max(max(abs(a - b) for a, b in zip(c, bg)) for c in corners) < 12 and sum(bg) < 150
    if plain_dark:
        lum = icon.convert("L").point(lambda v: max(0, v - max(bg)) * 255 // max(1, 255 - max(bg)))
        mark = Image.new("RGBA", icon.size, (255, 255, 255, 0))
        mark.putalpha(ImageOps.autocontrast(lum))
        mark_path, background = folder / "mark.png.src", "#%02x%02x%02x" % bg
        mark.save(mark_path, format="PNG")
        radius = "0"
    else:
        mark_path, background, radius = post / card["icon"], "#000", "22%"
    src = "data:image/png;base64," + base64.b64encode(Path(mark_path).read_bytes()).decode()
    page_html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{font(700)}{font(900)}
    *{{margin:0;padding:0}} body{{width:{W}px;height:{H}px;background:{background};overflow:hidden;font-family:Inter}}
    .logo{{position:absolute;left:50%;top:640px;width:420px;height:420px;margin-left:-210px}}
    .logo img{{position:absolute;inset:0;width:100%;height:100%;border-radius:{radius}}}
    .main{{animation:pop .55s cubic-bezier(.2,1.4,.4,1) both}}
    .cyan,.red{{mix-blend-mode:screen;opacity:0}}
    .cyan{{filter:url(#c);animation:split-c .5s ease-out both}} .red{{filter:url(#r);animation:split-r .5s ease-out both}}
    .name{{position:absolute;left:0;right:0;top:1090px;text-align:center;color:#fff;font:900 92px Inter;letter-spacing:-2px;
          animation:rise .45s ease-out .45s both}}
    .where{{position:absolute;left:0;right:0;top:1210px;text-align:center;color:#9aa0a6;font:700 40px Inter;
           animation:rise .45s ease-out .7s both}}
    @keyframes pop{{0%{{transform:scale(.55);opacity:0}}60%{{transform:scale(1.07);opacity:1}}100%{{transform:scale(1)}}}}
    @keyframes split-c{{0%{{opacity:0;transform:scale(.55)}}25%{{opacity:.9;transform:translate(-24px,-8px) scale(1.05)}}100%{{opacity:0;transform:none}}}}
    @keyframes split-r{{0%{{opacity:0;transform:scale(.55)}}25%{{opacity:.9;transform:translate(24px,8px) scale(1.05)}}100%{{opacity:0;transform:none}}}}
    @keyframes rise{{0%{{opacity:0;transform:translateY(30px)}}100%{{opacity:1;transform:none}}}}
    </style></head><body>
    <svg width="0" height="0"><filter id="c"><feColorMatrix values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/></filter>
    <filter id="r"><feColorMatrix values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter></svg>
    <div class="logo"><img class="cyan" src="{src}"><img class="red" src="{src}"><img class="main" src="{src}"></div>
    <div class="name">{text(card['name'])}</div><div class="where">{text(card.get('where'))}</div></body></html>"""
    seconds = float(card.get("seconds", 2.5))
    with sync_playwright() as p:
        b = browser(p)
        page = b.new_page(viewport={"width": W, "height": H})
        page.set_content(page_html, wait_until="load")
        page.evaluate("document.fonts.ready")
        for k in range(round(seconds * FPS)):
            page.evaluate(f"document.getAnimations().forEach(a => {{ a.pause(); a.currentTime = {k * 1000 / FPS}; }})")
            page.screenshot(path=str(folder / f"{k:03d}.png"))
        b.close()
    return seconds


# --- captions ------------------------------------------------------------------------------------------------------

def chunks(spoken, size):
    """Words grouped for the screen: up to `size` words, breaking after punctuation and at pauses."""
    out, cur = [], []
    for k, w in enumerate(spoken):
        cur.append(w)
        nxt = spoken[k + 1] if k + 1 < len(spoken) else None
        if len(cur) >= size or not nxt or re.search(r"[.!?,;:]$", w["w"]) or nxt["s"] - w["e"] > 0.35:
            out.append(cur)
            cur = []
    return out


def caption_track(out, spoken, caps, length):
    """Word-by-word captions: one transparent PNG per moment (a word appears), and an ffconcat list timing them."""
    from playwright.sync_api import sync_playwright
    folder = out / "captions"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    size, y = caps.get("size", 64), caps.get("at", 0.66) * H
    marked = {re.sub(r"\W", "", h.lower()) for h in caps.get("highlight", [])}
    color, active = caps.get("color", "#FFD400"), caps.get("active")
    box = caps.get("style", "outline") == "box"
    css = f"""{font(900)}*{{margin:0;padding:0}} html,body{{background:transparent;width:{W}px;height:{H}px}}
    .cap{{position:absolute;left:130px;right:130px;top:{y:.0f}px;transform:translateY(-50%);text-align:center;
         font:900 {size}px/1.18 Inter;color:#fff;{'' if box else f'text-shadow:{OUTLINE};'}
         {'text-transform:uppercase;' if caps.get('upper') else ''}}}
    .bx{{background:#000;padding:4px 14px;border-radius:10px;-webkit-box-decoration-break:clone;box-decoration-break:clone}}
    .w{{visibility:hidden}} .on{{visibility:visible}} .hl{{color:{color}}} .now{{color:{active or 'inherit'}}}"""
    groups = chunks(spoken, int(caps.get("words", 3)))
    moments = []  # (start, html)
    for g, group in enumerate(groups):
        for k, w in enumerate(group):
            spans = []
            for j, x in enumerate(group):
                cls = ["w"] + (["on"] if j <= k else []) + (["now"] if j == k and active else [])
                bare = re.sub(r"\W", "", x["w"].lower())
                if bare in marked or re.search(r"\d", x["w"]):
                    cls.append("hl")
                spans.append(f'<span class="{" ".join(cls)}">{html.escape(x["w"])}</span>')
            inner = " ".join(spans)
            moments.append((w["s"], f'<div class="cap">{f"<span class=bx>{inner}</span>" if box else inner}</div>'))
        last = group[-1]
        nxt = groups[g + 1][0]["s"] if g + 1 < len(groups) else length
        moments.append((min(nxt, last["e"] + 0.6), ""))  # a short beat of nothing between sentences
    with sync_playwright() as p:
        b = browser(p)
        page = b.new_page(viewport={"width": W, "height": H})
        page.set_content(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body></body></html>")
        page.evaluate("document.fonts.ready")
        blank = folder / "blank.png"
        page.screenshot(path=str(blank), omit_background=True)
        listing, prev_t, prev_png = ["ffconcat version 1.0"], 0.0, blank
        for k, (t, body) in enumerate(moments):
            t = max(prev_t, min(t, length))
            if body:
                page.evaluate("b => document.body.innerHTML = b", body)
                png = folder / f"{k:04d}.png"
                page.screenshot(path=str(png), omit_background=True)
            else:
                png = blank
            if t > prev_t:
                listing += [f"file '{prev_png.name}'", f"duration {t - prev_t:.3f}"]
            prev_t, prev_png = t, png
        b.close()
    listing += [f"file '{prev_png.name}'", f"duration {max(0.04, length - prev_t):.3f}", f"file '{prev_png.name}'"]
    (folder / "track.ffconcat").write_text("\n".join(listing) + "\n")
    return folder / "track.ffconcat"


# --- the talking layouts: cut, frame, transcribe -------------------------------------------------------------------

def keep_segments(spoken, start, end, gap):
    """The stretches to keep when pauses longer than `gap` seconds are cut, snapped to whole frames."""
    if not gap or not spoken:
        return [(start, end)]
    segs, a, last = [], max(start, spoken[0]["s"] - 0.15), spoken[0]["e"]
    for w in spoken[1:]:
        if w["s"] - last > gap:
            segs.append((a, min(end, last + 0.12)))
            a = max(segs[-1][1], w["s"] - 0.08)
        last = max(last, w["e"])
    segs.append((a, min(end, last + 0.35)))
    snap = lambda t: start + round((t - start) * FPS) / FPS  # noqa: E731
    return [(snap(a), snap(b)) for a, b in segs if snap(b) - snap(a) >= 2 / FPS]


def mapper(segs):
    """Source time -> finished-video time (a moment inside a cut maps to where the video picks up again)."""
    def to_out(t):
        off = 0.0
        for a, b in segs:
            if t < a:
                return off
            if t <= b:
                return off + t - a
            off += b - a
        return off
    return to_out


def crop_box(src, info, spec, work):
    w, h = info["width"], info["height"]
    fx, fy = 0.5, 0.4
    crop, fh = spec.get("crop", "face"), None
    if crop == "face":
        f = find_face(src, work)
        if f.get("found", 0) * 3 >= f.get("of", 1):
            fx, fy, fh = f["x"], f["y"], f["h"]
        else:
            print("No steady face found; framing the centre. Set \"crop\": {\"x\": 0.3} to move it.")
    elif isinstance(crop, dict):
        fx, fy = crop.get("x", 0.5), crop.get("y", 0.4)
    cw, ch = (h * 9 / 16, h) if w / h > 9 / 16 else (w, w * 16 / 9)
    zoom = float(spec.get("zoom", 1))
    cw, ch = int(cw / zoom) // 2 * 2, int(ch / zoom) // 2 * 2
    x = int(min(max(0, fx * w - cw / 2), w - cw))
    y = int(min(max(0, fy * h - ch * 0.4), h - ch))
    seen = {"x": (fx * w - x) / cw, "y": (fy * h - y) / ch, "h": fh * h / ch} if fh else None
    return (cw, ch, x, y), seen


def speaking_base(post, spec, work):
    """The person's clip trimmed, with its pauses cut, framed 9:16 and loudness-levelled: work/base-<key>.mp4.
    Returns (base, spoken words in finished-video time, segments, source->finished time mapper, where the face is
    in the 9:16 frame or None)."""
    src = post / spec["video"]
    info = probe(src)
    if not info["audio"]:
        raise SystemExit(f"{spec['video']} has no sound. Use \"layout\": \"text\" for a clip with no talking.")
    start, end = spec.get("trim") or (0.0, info["duration"])
    said = transcribe(src, work, start, end if spec.get("trim") else None, spec.get("model", "small"), spec.get("language"))
    if not said:
        raise SystemExit("No speech found. Use \"layout\": \"text\" for a clip with no talking.")
    segs = keep_segments(said, start, end, spec.get("cut_pauses", 0.5))
    box, seen = crop_box(src, info, spec, work)
    to_out = mapper(segs)
    spoken = [{"w": w["w"], "s": to_out(w["s"]), "e": to_out(w["e"])} for w in said]
    base = work / f"base-{key(src, segs, box)}.mp4"
    if not base.exists():
        sel = "+".join(f"between(t,{a - start:.4f},{b - start:.4f})" for a, b in segs)
        cw, ch, x, y = box
        print(f"cutting {len(segs) - 1} pauses and framing {cw}x{ch} at {x},{y}...", flush=True)
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(src),
             "-filter_complex",
             f"[0:v]fps={FPS},select='{sel}',setpts=N/FRAME_RATE/TB,crop={cw}:{ch}:{x}:{y},"
             f"scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p[v];"
             f"[0:a]aselect='{sel}',asetpts=N/SR/TB,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-c:a", "aac",
             "-b:a", "192k", str(base)])
    return base, spoken, segs, to_out, seen


def fill(src, dest, focus="50% 50%", mode="cover"):
    """An image made 1080x1920. cover: cropped to fill (focus moves the crop). top: shown whole near the top, over a
    blurred, darkened copy of itself (for screenshots behind a green-screen speaker)."""
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    fx, fy = (float(v.rstrip("%")) / 100 for v in focus.split())
    if mode == "cover":
        scale = max(W / im.width, H / im.height)
        big = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        x, y = round((big.width - W) * fx), round((big.height - H) * fy)
        big.crop((x, y, x + W, y + H)).save(dest, quality=92)
        return
    back = ImageOps.fit(im, (W, H)).filter(ImageFilter.GaussianBlur(40)).point(lambda v: v * 0.45)
    scale = min((W - 60) / im.width, (H * 0.36) / im.height)
    front = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    back.paste(front, ((W - front.width) // 2, 400))
    back.save(dest, quality=92)


def broll_inputs(post, items, to_out, work, first_input, src, dst):
    """B-roll (photos or clips) cut in full-frame over the voice at their times."""
    fc, inputs, cur = "", [], src
    for k, item in enumerate(items):
        path = post / item["src"]
        t, sec = to_out(float(item["at"])), float(item.get("seconds", 2.0))
        if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            still = work / f"broll-{k}-{key(path, item.get('focus'))}.jpg"
            fill(path, still, item.get("focus", "50% 50%"))
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{sec:.3f}", "-i", str(still)]
        else:
            inputs += ["-ss", f"{float(item.get('from', 0)):.3f}", "-t", f"{sec:.3f}", "-i", str(path)]
        nxt = dst if k == len(items) - 1 else f"r{k}"
        fc += (f"[{first_input + k}:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
               f"format=yuv420p,setpts=PTS-STARTPTS+{t:.3f}/TB[rb{k}];"
               f"[{cur}][rb{k}]overlay=0:0:enable='between(t,{t:.3f},{t + sec:.3f})':eof_action=pass[{nxt}];")
        cur = nxt
    return (fc or f"[{src}]null[{dst}];"), inputs


def backgrounds(post, items, to_out, length, work):
    """The green-screen backdrop: each image from its time until the next, as an ffconcat list of 1080x1920 stills."""
    items = sorted(items, key=lambda b: float(b.get("at", 0)))
    listing = ["ffconcat version 1.0"]
    for k, item in enumerate(items):
        path = post / item["src"]
        still = work / f"bg-{k}-{key(path, item.get('fit'), item.get('focus'))}.jpg"
        fill(path, still, item.get("focus", "50% 50%"), item.get("fit", "top"))
        start = 0.0 if k == 0 else to_out(float(item["at"]))
        end = to_out(float(items[k + 1]["at"])) if k + 1 < len(items) else length
        listing += [f"file '{still.name}'", f"duration {max(1 / FPS, end - start):.3f}"]
    listing.append(listing[-2])
    track = work / "backgrounds.ffconcat"
    track.write_text("\n".join(listing) + "\n")
    return track


# --- build ---------------------------------------------------------------------------------------------------------

def build_text(post, spec, out):
    video = post / spec["video"]
    slow, shift = float(spec.get("slow", 1)), int(spec.get("headroom", 0))
    start, end = spec.get("trim") or (0.0, duration(video))
    clip_s = (end - start) * slow - (1 / FPS if slow != 1 else 0)
    states = hook_states(out, spec, "text", clip_s)
    speed = (f"setpts={slow}*PTS,minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
             if slow != 1 else f"fps={FPS}")
    fc = f"[0:v]{speed},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
    if shift:
        # the wall above the head: the clip's own top rows, stretched, blurred wide, and faded into the clip over 60 px
        fc += (f",split[v][t];[t]crop={W}:14:0:0,scale={W}:{shift + 60},setsar=1,gblur=sigma=30,format=rgba,"
               f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(Y,{shift}),255,max(0,255*({shift + 60}-Y)/60))'[top];"
               f"[v]crop={W}:{H - shift}:0:0,pad={W}:{H}:0:{shift}[body];[body][top]overlay=0:0,format=yuv420p[base];")
    else:
        fc += "[base];"
    hooks, hook_in = hook_filters(states, 1, "base", "hooked")
    fc += hooks + "[hooked]setsar=1,format=yuv420p[clip];"
    source = (["-ss", f"{start:.3f}", "-t", f"{end - start:.3f}"] if spec.get("trim") else []) + ["-i", str(video)]
    # keep_audio keeps the clip's own sound (a sound already in it); otherwise it's silent and the music goes on in the app
    keep = spec.get("keep_audio") and slow == 1 and probe(video)["audio"]
    return fc, [*source, *hook_in], clip_s, "0:a" if keep else None


def speaker_place(spk, seen):
    """Where the cut-out goes: scaled so the face is `face` of the frame's height (0.12: chest up, as green-screen
    creators film themselves), the face at `x` across and `y` down, and never floating above the bottom edge."""
    if "height" in spk or not seen:  # a fixed size, standing on the bottom edge
        scale = float(spk.get("height", 0.58))
        return round(W * (float(spk.get("x", 0.5)) - scale / 2)), H - round(H * scale / 2) * 2, scale
    scale = min(2.0, max(0.4, float(spk.get("face", 0.12)) / seen["h"]))
    x = round(W * float(spk.get("x", 0.5)) - seen["x"] * W * scale)
    y = round(H * float(spk.get("y", 0.66)) - seen["y"] * H * scale)
    return x, max(y, H - round(H * scale / 2) * 2), scale


def build_speaking(post, spec, out, layout):
    work = out / "work"
    base, spoken, segs, to_out, seen = speaking_base(post, spec, work)
    clip_s = sum(b - a for a, b in segs)
    inputs, fc = ["-i", str(base)], ""
    if layout == "green-screen":
        if not spec.get("backgrounds"):
            raise SystemExit('green-screen needs "backgrounds": [{"src": "assets/screenshot.png", "at": 0}, ...]')
        mask = work / f"mask-{key(base)}.mkv"
        if not mask.exists():
            small = work / "matte-in.mp4"
            run(["ffmpeg", "-v", "error", "-y", "-i", str(base), "-vf", f"scale={W // 2}:{H // 2}", "-an", "-c:v",
                 "libx264", "-crf", "18", str(small)])
            print("cutting the person out, frame by frame...", flush=True)
            vision("matte", small, mask, "--fps", FPS)
            small.unlink()
        track = backgrounds(post, spec["backgrounds"], to_out, clip_s, work)
        inputs += ["-i", str(mask), "-f", "concat", "-safe", "0", "-i", str(track)]
        x, y, scale = speaker_place(spec.get("speaker", {}), seen)
        sw, sh = round(W * scale / 2) * 2, round(H * scale / 2) * 2
        fc += (f"[1:v]scale={W}:{H},format=gray[m];[0:v][m]alphamerge,scale={sw}:{sh}[spk];"
               f"[2:v]fps={FPS},scale={W}:{H},setsar=1,format=yuv420p[bg];"
               f"[bg][spk]overlay=x={x}:y={y}:eof_action=pass,format=yuv420p[v0];")
    else:
        fc += "[0:v]null[v0];"
    first = sum(1 for x in inputs if x == "-i")  # the next input's index
    rb, rb_in = broll_inputs(post, spec.get("broll") or [], to_out, work, first, "v0", "v1")
    fc += rb
    inputs += rb_in
    caps = spec.get("captions", {})
    if caps is not False:
        track = caption_track(out, spoken, {"at": 0.52 if layout == "green-screen" else 0.66, **(caps or {})}, clip_s)
        first = sum(1 for x in inputs if x == "-i")
        inputs += ["-f", "concat", "-safe", "0", "-i", str(track)]
        fc += f"[{first}:v]fps={FPS},format=rgba[cap];[v1][cap]overlay=0:0:eof_action=pass[v2];"
    else:
        fc += "[v1]null[v2];"
    states = hook_states(out, spec, layout, clip_s)
    first = sum(1 for x in inputs if x == "-i")
    hooks, hook_in = hook_filters(states, first, "v2", "hooked")
    fc += hooks + f"[hooked]trim=duration={clip_s:.3f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[clip];"
    return fc, inputs + hook_in, clip_s, "0:a"


def preview(reel, dest, length):
    times = [0.5, length * 0.2, length * 0.4, length * 0.6, length * 0.85, length - 0.3]
    shots = []
    for k, t in enumerate(times):
        frame = dest.parent / f"_preview{k}.jpg"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, t):.2f}", "-i", str(reel), "-frames:v", "1",
             "-vf", "scale=270:480", str(frame)])
        shots.append(Image.open(frame).copy())
        frame.unlink()
    sheet = Image.new("RGB", (270 * len(shots), 480))
    for k, im in enumerate(shots):
        sheet.paste(im, (270 * k, 0))
    sheet.save(dest, quality=85)


def build(post):
    post = Path(post).resolve()
    spec = json.loads((post / "reel.json").read_text())
    layout = spec.get("layout", "text")
    if layout not in LAYOUTS:
        raise SystemExit(f"layout must be one of {', '.join(LAYOUTS)}, not {layout!r}")
    out = post / "out"
    out.mkdir(exist_ok=True)
    fc, inputs, clip_s, audio = build_text(post, spec, out) if layout == "text" else build_speaking(post, spec, out, layout)
    card = spec.get("end_card")
    end_s = end_card(out / "endcard", card, post) if card else 0
    n = sum(1 for x in inputs if x == "-i")
    if card:
        inputs += ["-framerate", str(FPS), "-i", str(out / "endcard/%03d.png")]
        fc += f"[{n}:v]fps={FPS},setsar=1,format=yuv420p[end];[clip][end]concat=n=2:v=1:a=0[out]"
        n += 1
    else:
        fc += "[clip]null[out]"
    total = clip_s + end_s
    if audio:  # the person's voice, with silence under the closing logo
        fc += f";[{audio}]apad=whole_dur={total:.3f}[aout]"
        audio_map = "[aout]"
    else:  # silent: the music is added in the app
        inputs += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        audio_map = f"{n}:a"
    reel = out / "reel.mp4"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[out]", "-map", audio_map,
         "-t", f"{total:.3f}", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac",
         "-b:a", "128k" if not audio else "192k", "-movflags", "+faststart", str(reel)])
    # square pixels or players stretch it: check, don't assume
    sar = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=sample_aspect_ratio",
                          "-of", "csv=p=0", str(reel)], capture_output=True, text=True).stdout.strip()
    if sar not in ("1:1", "N/A", ""):
        raise SystemExit(f"reel.mp4 has pixel shape {sar}, not 1:1; players would stretch it")
    preview(reel, out / "reel-preview.jpg", total)
    print(f"out/reel.mp4: {layout}, {clip_s:.1f} s" + (f" + {end_s:.1f} s closing logo" if card else "")
          + f", {W}x{H}. Look at out/reel-preview.jpg, then watch it.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    build(sys.argv[1])
