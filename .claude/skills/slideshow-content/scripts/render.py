"""Render a slideshow post spec (post.json) to slide PNGs and a contact sheet.

    python3 render.py <post folder or post.json>      # writes <folder>/out/slide_01.png ... and out/contact.jpg

Photo spots: each slide names a photo key and a brief ("what to shoot"). Until <folder>/photos/<key>.jpg (or .jpeg, .png,
.webp) exists, the spot renders as a dashed PHOTO box showing the brief, so the slides can be reviewed before anything
is shot. Drop the photo in and render again to fill it. Screens (app screenshots) are paths relative to the folder.

Text: "*word*" marks the cover's highlighted words (an accent box) and the accent elsewhere; a newline (or "\\n") is a
line break you choose. Long lines are balanced automatically. Spec format: references/post-spec.md.
"""

import base64
import html
import json
import os
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
FONTS = SKILL / "assets/fonts"
PHOTO_EXT = (".jpg", ".jpeg", ".png", ".webp")
TYPES = ("cover", "photo", "compare", "item", "list", "app")
DEFAULT_THEME = {"accent": "#2340B0", "muted": "#5B6475", "ink": "#121417", "paper": "#FFFFFF", "soft": "#F3F4F7",
                 "no": "#9A3B3B", "yes": "#1D7A46", "faint": "#8A909A"}


def font_css():
    faces = []
    for weight in (600, 700, 900):
        data = base64.b64encode((FONTS / f"Inter-{weight}.woff2").read_bytes()).decode()
        faces.append(f"@font-face{{font-family:'Inter';src:url(data:font/woff2;base64,{data}) format('woff2');"
                     f"font-weight:{weight};}}")
    return "".join(faces)


def text(s, em_class="em"):
    """Escape, then *word* -> highlighted span and newlines -> <br>."""
    s = html.escape(str(s or "")).replace("\\n", "\n")
    s = re.sub(r"\*(.+?)\*", lambda m: f'<span class="{em_class}">{m.group(1)}</span>', s)
    s = re.sub(r"\w+(?:-\w+)+", lambda m: f'<span class="nb">{m.group(0)}</span>', s)  # never break "HIGH-PROTEIN"
    return s.replace("\n", "<br>")


def data_uri(path):
    mime = {".png": "image/png", ".webp": "image/webp"}.get(path.suffix.lower(), "image/jpeg")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


class Post:
    def __init__(self, folder, spec):
        self.folder, self.spec = folder, spec
        self.w, self.h = spec.get("size", [1080, 1440])
        self.theme = {**DEFAULT_THEME, **spec.get("theme", {})}
        self.total = len(spec["slides"])
        self.photos = []  # (key, brief, filled) in slide order, for the shot list

    def photo(self, spec, cls="photo", style=""):
        """A photo spot: the photo when photos/<key>.* exists, else a dashed box with the brief."""
        spec = spec or {}
        key, brief = spec.get("key"), spec.get("brief", "")
        found = next((self.folder / "photos" / f"{key}{ext}" for ext in PHOTO_EXT
                      if key and (self.folder / "photos" / f"{key}{ext}").exists()), None)
        if key:
            self.photos.append((key, brief, bool(found)))
        if found:
            return f'<div class="{cls} filled" style="{style}"><img src="{data_uri(found)}"></div>'
        return f'<div class="{cls}" style="{style}"><div><b>PHOTO</b>{html.escape(brief)}</div></div>'

    def screen(self, path, brief):
        p = self.folder / path if path else None
        if p and p.exists():
            return f'<img class="screen" src="{data_uri(p)}">'
        return self.photo({"key": None, "brief": brief or "a screenshot of the app"}, "photo screenbox")

    def css(self):
        t, w, h = self.theme, self.w, self.h
        return font_css() + f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{w}px;height:{h}px;overflow:hidden;font-family:Inter,sans-serif;color:{t['ink']};background:{t['paper']};
     position:relative;display:flex;flex-direction:column;padding:96px 60px 48px}}
.nb{{white-space:nowrap}}
.count{{position:absolute;top:44px;right:56px;font:700 30px Inter;color:{t['faint']}}}
.title{{text-align:center;font:900 62px/1.08 Inter;letter-spacing:-1.5px;text-wrap:balance}}
.title .em{{color:{t['accent']}}}
.photo{{position:relative;border-radius:22px;overflow:hidden;background:#EEF0F3;border:4px dashed #C6CBD3;display:flex;
       align-items:center;justify-content:center;text-align:center;color:#7d848f;font:600 27px/1.3 Inter;padding:26px}}
.photo.filled{{border:none;padding:0}}
.photo img{{width:100%;height:100%;object-fit:cover}}
.photo b{{display:block;font:900 24px Inter;letter-spacing:2px;color:#9aa1ab;margin-bottom:8px}}
.box{{background:{t['accent']};color:#fff;border-radius:14px;padding:10px 20px;font:900 54px/1.05 Inter;letter-spacing:-1px;
     width:max-content;max-width:100%}}
.box small{{font:700 28px Inter;letter-spacing:0;margin-left:6px}}
.verdict{{text-align:center;font:900 44px/1.15 Inter;text-wrap:balance}}
.verdict .em{{color:{t['accent']}}}
.src{{text-align:center;font:600 22px Inter;color:#9aa1ab;margin-top:12px}}
.save{{font:900 34px Inter;letter-spacing:1px;color:{t['accent']};text-align:center;margin-top:18px}}
.sub{{font:700 38px/1.3 Inter;color:#30343b;text-align:center;text-wrap:balance}}
"""

    def page(self, i, body, css="", count=True):
        counter = f'<div class="count">{i}/{self.total}</div>' if count and self.spec.get("counter", True) else ""
        return (f"<!doctype html><html><head><meta charset='utf-8'><style>{self.css()}{css}</style></head>"
                f"<body>{body}{counter}</body></html>")

    def save_line(self, slide, cls="save"):
        line = slide.get("save_line", self.spec.get("save_line")) if slide.get("save", False) else None
        return f'<div class="{cls}">{text(line)}</div>' if line else ""

    def source_line(self, slide, default=True):
        line = slide.get("source", self.spec.get("source_line") if default else None)
        return f'<div class="src">{text(line)}</div>' if line else ""

    # Slide types -------------------------------------------------------------------------------------------------

    def cover(self, i, s):
        t = self.theme
        css = f"""
        body{{padding:0;color:#fff;background:#222}}
        .shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.55) 0%,rgba(0,0,0,.15) 45%,rgba(0,0,0,.6) 100%)}}
        .wrap{{position:absolute;inset:0;display:flex;flex-direction:column;padding:150px 70px 82px}}
        .t{{font:900 {s.get('title_size', 112)}px/1.02 Inter;letter-spacing:-3px;text-transform:uppercase;text-wrap:balance}}
        .t .em{{background:{t['accent']};padding:0 14px;border-radius:12px;box-decoration-break:clone;-webkit-box-decoration-break:clone}}
        .s{{margin-top:auto;font:700 50px/1.25 Inter;text-wrap:balance}}
        .save{{color:#fff;text-align:left;font-size:38px;margin-top:24px}}
        .count{{color:rgba(255,255,255,.8)}}
        """
        body = (self.photo(s.get("photo"), "photo", "position:absolute;inset:0;border-radius:0;border:none")
                + '<div class="shade"></div><div class="wrap">'
                + f'<div class="t">{text(s.get("title"))}</div>'
                + (f'<div class="s">{text(s.get("subtitle"))}</div>' if s.get("subtitle") else '<div class="s"></div>')
                + self.save_line(s) + "</div>")
        return self.page(i, body, css)

    def side(self, cls, d):
        d = d or {}
        boxes = "".join(f'<div class="box">{text(v)}<small>{text(u)}</small></div>' for v, u in d.get("stats", []))
        tag = d.get("label", "INSTEAD OF" if cls == "before" else "SWAP TO")
        return (f'<div class="row {cls}">{self.photo(d.get("photo"))}'
                f'<div class="nums"><div class="tag">{text(tag)}</div><div class="name">{text(d.get("name"))}</div>'
                + (f'<div class="serv">{text(d.get("serving"))}</div>' if d.get("serving") else "")
                + f"{boxes}</div></div>")

    def compare(self, i, s):
        t = self.theme
        css = f"""
        .rows{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:30px;margin:40px 0 30px;min-height:0}}
        .row{{flex:1;display:flex;gap:34px;align-items:center;max-height:460px;min-height:0}}
        .row .photo{{width:520px;height:100%;flex:none}}
        .nums{{flex:1;display:flex;flex-direction:column;gap:16px;min-width:0}}
        .tag{{font:900 26px Inter;letter-spacing:2px;color:{t['yes']}}}
        .row.before .tag{{color:{t['no']}}}
        .row.before .box{{background:{t['muted']}}}
        .name{{font:700 32px/1.15 Inter}}
        .serv{{font:600 26px Inter;color:#6b7280;margin-top:-8px}}
        """
        body = (f'<div class="title">{text(s.get("title"))}</div><div class="rows">'
                + self.side("before", s.get("before")) + self.side("after", s.get("after")) + "</div>"
                + (f'<div class="verdict">{text(s.get("verdict"))}</div>' if s.get("verdict") else "")
                + self.source_line(s) + self.save_line(s))
        return self.page(i, body, css)

    def item(self, i, s):
        """One thing per slide (an order, a meal, a product): its photo, name, numbers, notes and a verdict."""
        css = """
        .photo.main{flex:1;margin:36px 0 26px;min-height:0}
        .name{font:900 46px/1.1 Inter;text-align:center;text-wrap:balance}
        .boxes{display:flex;gap:16px;justify-content:center;margin:18px 0 6px;flex-wrap:wrap}
        .notes{font:600 32px/1.35 Inter;color:#30343b;text-align:center;margin-top:10px}
        .verdict{margin-top:18px}
        """
        boxes = "".join(f'<div class="box">{text(v)}<small>{text(u)}</small></div>' for v, u in s.get("stats", []))
        notes = "".join(f"<div>{text(n)}</div>" for n in s.get("notes", []))
        body = ((f'<div class="title">{text(s.get("title"))}</div>' if s.get("title") else "")
                + self.photo(s.get("photo"), "photo main")
                + (f'<div class="name">{text(s.get("name"))}</div>' if s.get("name") else "")
                + (f'<div class="boxes">{boxes}</div>' if boxes else "")
                + (f'<div class="notes">{notes}</div>' if notes else "")
                + (f'<div class="verdict">{text(s.get("verdict"))}</div>' if s.get("verdict") else "")
                + self.source_line(s) + self.save_line(s))
        return self.page(i, body, css)

    def list(self, i, s):
        """A text slide: a title and short lines (tips, steps, a checklist), with an optional photo strip."""
        t = self.theme
        css = f"""
        .lines{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:28px;margin:40px 10px}}
        .line{{display:flex;gap:22px;font:700 40px/1.25 Inter;align-items:baseline}}
        .line .n{{flex:none;width:58px;height:58px;border-radius:50%;background:{t['accent']};color:#fff;font:900 30px/58px Inter;
                 text-align:center;transform:translateY(8px)}}
        .photo.strip{{height:380px;flex:none;margin-top:30px}}
        """
        lines = "".join(f'<div class="line"><span class="n">{k}</span><span>{text(x)}</span></div>'
                        for k, x in enumerate(s.get("lines", []), 1))
        body = (f'<div class="title">{text(s.get("title"))}</div>'
                + (self.photo(s.get("photo"), "photo strip") if s.get("photo") else "")
                + f'<div class="lines">{lines}</div>' + self.source_line(s, default=False) + self.save_line(s))
        return self.page(i, body, css)

    def app(self, i, s):
        css = f"""
        body{{background:{self.theme['soft']}}}
        .title{{font-size:66px}}
        .screen{{flex:1;min-height:0;object-fit:contain;margin:44px auto 36px;max-width:100%;border-radius:44px;
                box-shadow:0 30px 60px rgba(0,0,0,.18)}}
        .photo.screenbox{{flex:1;margin:44px 120px 36px}}
        .sub{{margin:0 20px}}
        """
        body = (f'<div class="title">{text(s.get("title"))}</div>' + self.screen(s.get("screen"), s.get("screen_brief"))
                + (f'<div class="sub">{text(s.get("subtitle"))}</div>' if s.get("subtitle") else "") + self.save_line(s))
        return self.page(i, body, css)

    def photo_slide(self, i, s):
        """Full-bleed photo with white text over it, the way most slideshows are built: a title at the top (or the
        bottom), short lines, number boxes and a verdict."""
        t = self.theme
        bottom = s.get("text_at", "top") == "bottom"
        css = f"""
        body{{padding:0;color:#fff;background:#222}}
        .shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,{'.15' if bottom else '.6'}) 0%,
               rgba(0,0,0,.1) 40%,rgba(0,0,0,{'.7' if bottom else '.35'}) 100%)}}
        .wrap{{position:absolute;inset:0;display:flex;flex-direction:column;padding:110px 64px 70px;
              justify-content:{'flex-end' if bottom else 'flex-start'};text-shadow:0 2px 12px rgba(0,0,0,.35)}}
        .t{{font:900 {s.get('title_size', 76)}px/1.04 Inter;letter-spacing:-2px;text-wrap:balance}}
        .t .em{{background:{t['accent']};padding:0 12px;border-radius:10px;text-shadow:none}}
        .ls{{margin-top:22px;font:700 40px/1.3 Inter}}
        .boxes{{display:flex;gap:14px;flex-wrap:wrap;margin-top:24px;text-shadow:none}}
        .v{{margin-top:auto;font:900 46px/1.15 Inter;text-wrap:balance}}
        .v .em{{background:{t['accent']};padding:0 10px;border-radius:8px;text-shadow:none}}
        .wrap.bottom .v{{margin-top:22px}}
        .src{{color:rgba(255,255,255,.75);text-align:left;text-shadow:none}}
        .save{{color:#fff;text-align:left;margin-top:18px}}
        .count{{color:rgba(255,255,255,.85)}}
        """
        boxes = "".join(f'<div class="box">{text(v)}<small>{text(u)}</small></div>' for v, u in s.get("stats", []))
        lines = "".join(f"<div>{text(x)}</div>" for x in s.get("lines", []))
        body = (self.photo(s.get("photo"), "photo", "position:absolute;inset:0;border-radius:0;border:none")
                + f'<div class="shade"></div><div class="wrap{" bottom" if bottom else ""}">'
                + (f'<div class="t">{text(s.get("title"))}</div>' if s.get("title") else "")
                + (f'<div class="ls">{lines}</div>' if lines else "")
                + (f'<div class="boxes">{boxes}</div>' if boxes else "")
                + (f'<div class="v">{text(s.get("verdict"))}</div>' if s.get("verdict") else "")
                + self.source_line(s, default=bool(boxes)) + self.save_line(s) + "</div>")
        return self.page(i, body, css)

    def pages(self):
        out = []
        for i, s in enumerate(self.spec["slides"], 1):
            kind = s.get("type")
            make = getattr(self, "photo_slide" if kind == "photo" else kind, None) if kind in TYPES else None
            if not make:
                raise SystemExit(f"Slide {i}: unknown type {kind!r} ({', '.join(TYPES)})")
            out.append(make(i, s))
        return out


def chrome():
    for path in (os.environ.get("CHROME"), "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"):
        if path and Path(path).exists():
            return path
    return None  # Playwright's own Chromium


def render(target):
    target = Path(target).resolve()
    spec_path = target / "post.json" if target.is_dir() else target
    folder = spec_path.parent
    post = Post(folder, json.loads(spec_path.read_text()))
    pages = post.pages()
    out = folder / "out"
    out.mkdir(exist_ok=True)
    for old in out.glob("slide_*.png"):
        old.unlink()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome())
        page = browser.new_page(viewport={"width": post.w, "height": post.h})
        for k, doc in enumerate(pages, 1):
            page.set_content(doc, wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(100)
            page.screenshot(path=str(out / f"slide_{k:02d}.png"))
        browser.close()
    contact_sheet(out, len(pages), post.w, post.h)
    missing = [(k, b) for k, b, filled in post.photos if not filled]
    print(f"{len(pages)} slides -> {out}")
    if missing:
        print(f"{len(missing)} photo spots still empty (put each at photos/<key>.jpg):")
        for key, brief in dict.fromkeys(missing):
            print(f"  {key}: {brief}")


def contact_sheet(out, n, w, h, cols=4, tw=360, gap=14):
    from PIL import Image
    th = round(tw * h / w)
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols - 1) * gap, rows * th + (rows - 1) * gap), "white")
    for k in range(n):
        im = Image.open(out / f"slide_{k + 1:02d}.png").convert("RGB").resize((tw, th))
        sheet.paste(im, ((k % cols) * (tw + gap), (k // cols) * (th + gap)))
    sheet.save(out / "contact.jpg", quality=88)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    render(sys.argv[1])
