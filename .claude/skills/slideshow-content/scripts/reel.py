"""Build a body-turn reveal reel: a short before/after clip in @movementwithjulie's format, with a closing logo.

    python3 reel.py <post folder>          # reads <post>/reel.json, writes <post>/out/reel.mp4

The format, from the research (references/reel.md has the evidence and the rules):
- The person's real before/after turn plays full width, untouched, slowed so each state reads (2x by default, with
  motion-interpolated in-between frames, not repeated ones).
- A small black text box with the hook sits on plain wall above the head, below the apps' top bars. When the head is
  at the top of the frame, the clip moves down by `headroom` px, and the strip above is made from the clip's own top
  rows of wall: blurred and faded in, so there are no streaks and no seam.
- A second line ("here's the 2 things I did") joins it about a third of the way in. Music only (add it in the app).
- No watermark on the clip. The product closes the video instead, like TikTok's end logo: its mark pops in with a cyan
  and red split on the icon's own background, then the name and `where` rise in under it.

reel.json:
{
  "video": "assets/flip.mp4",
  "hook": "I gave myself 365 days, and\\nthis is what happened...",
  "second_line": "↓ here's the 2 things I did ↓",
  "second_line_at": 0.33,                 # a fraction of the slowed clip, or seconds if > 1
  "slow": 2.0,                            # 1 keeps the original speed
  "headroom": 340,                        # px of wall added above the head (0: none; the hook then sits over the clip)
  "text_top": 200,                        # px; keep it at 200 or more, below TikTok's and Instagram's top bars
  "end_card": {"icon": "assets/app-icon-1024.png", "name": "Weight Class", "where": "Free on the App Store",
               "seconds": 2.5}            # leave end_card out for no closing logo
}
"""

import base64
import html
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

SKILL = Path(__file__).resolve().parent.parent
FONTS = SKILL / "assets/fonts"
W, H, FPS = 1080, 1920, 30
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def face(weight):
    data = base64.b64encode((FONTS / f"Inter-{weight}.woff2").read_bytes()).decode()
    return f"@font-face{{font-family:Inter;src:url(data:font/woff2;base64,{data}) format('woff2');font-weight:{weight}}}"


def uri(path):
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def text(s):
    return html.escape(s or "").replace("\\n", "\n").replace("\n", "<br>")


def browser(p):
    return p.chromium.launch(executable_path=CHROME if Path(CHROME).exists() else None)


def overlays(out, spec):
    """Two transparent overlays: the hook box alone, then the hook box with the second line."""
    from playwright.sync_api import sync_playwright
    css = f"""{face(700)}*{{margin:0;padding:0}} html,body{{background:transparent;width:{W}px;height:{H}px}}
    .wrap{{position:absolute;top:{spec.get('text_top', 200)}px;left:0;right:0;display:flex;flex-direction:column;
          align-items:center;gap:12px}}
    .b1{{background:#000;color:#fff;font:700 38px/1.22 Inter;padding:8px 18px;border-radius:8px;text-align:center;max-width:700px}}
    .b2{{background:#fff;color:#111;font:700 34px Inter;padding:6px 16px;border-radius:8px}}"""
    with sync_playwright() as p:
        b = browser(p)
        page = b.new_page(viewport={"width": W, "height": H})
        for name, second in (("hook1.png", ""), ("hook2.png", spec.get("second_line", ""))):
            body = f'<div class="wrap"><div class="b1">{text(spec["hook"])}</div>' + \
                   (f'<div class="b2">{text(second)}</div>' if second else "") + "</div>"
            page.set_content(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(100)
            page.screenshot(path=str(out / name), omit_background=True)
        b.close()


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
    page_html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{face(700)}{face(900)}
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


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def build(post):
    post = Path(post).resolve()
    spec = json.loads((post / "reel.json").read_text())
    video = post / spec["video"]
    out = post / "out"
    out.mkdir(exist_ok=True)
    slow, shift = float(spec.get("slow", 2.0)), int(spec.get("headroom", 340))
    clip_s = duration(video) * slow - (1 / FPS if slow != 1 else 0)
    at = float(spec.get("second_line_at", 0.33))
    at = at * clip_s if at <= 1 else at
    overlays(out, spec)
    card = spec.get("end_card")
    end_s = end_card(out / "endcard", card, post) if card else 0

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
    fc += (f"[base][1:v]overlay=0:0:enable='lt(t,{at:.2f})'[a];"
           f"[a][2:v]overlay=0:0:enable='gte(t,{at:.2f})',setsar=1,format=yuv420p[clip];")
    inputs = ["-i", str(video), "-i", str(out / "hook1.png"), "-i", str(out / "hook2.png")]
    if card:
        inputs += ["-framerate", str(FPS), "-i", str(out / "endcard/%03d.png")]
        fc += f"[3:v]fps={FPS},setsar=1,format=yuv420p[end];[clip][end]concat=n=2:v=1:a=0[out]"
        audio = 4
    else:
        fc += "[clip]null[out]"
        audio = 3
    inputs += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[out]", "-map", f"{audio}:a",
                    "-t", f"{clip_s + end_s:.3f}", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac",
                    "-b:a", "128k", "-movflags", "+faststart", str(out / "reel.mp4")], check=True)
    # square pixels or players stretch it: check, don't assume
    sar = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=sample_aspect_ratio",
                          "-of", "csv=p=0", str(out / "reel.mp4")], capture_output=True, text=True).stdout.strip()
    if sar not in ("1:1", "N/A", ""):
        raise SystemExit(f"reel.mp4 has pixel shape {sar}, not 1:1; players would stretch it")
    print(f"out/reel.mp4: {clip_s:.1f} s clip + {end_s:.1f} s closing logo, {W}x{H}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    build(sys.argv[1])
