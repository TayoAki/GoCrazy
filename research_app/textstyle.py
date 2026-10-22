"""Measure the on-screen text in a frame, so a brief can ask for the same size, colours and position as the reference.

The model says where each text block is (a box, in % of the frame) and what colour its letters are. This module then
measures from the pixels: the letters' actual colour, how many lines there are, how tall a line is and where the block
sits, as % of the frame and as pixels on a 1080×1920 reel.
"""

import re
import statistics

import numpy as np
from PIL import Image

REEL_W, REEL_H = 1080, 1920
NEAR = 70  # how far (RGB distance) a pixel may be from the fill colour and still count as letter


def _rgb(value):
    value = str(value or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(int(round(c)) for c in rgb)


def measure(path, box, fill):
    """box: [x0, y0, x1, y1] in % of the frame; fill: the letters' colour (hex). None when it can't be measured."""
    target = _rgb(fill)
    if not target or not box or len(box) != 4:
        return None
    im = np.asarray(Image.open(path).convert("RGB")).astype(int)
    h, w, _ = im.shape
    pad = 0.01
    x0, y0 = max(0, int((min(box[0], box[2]) / 100 - pad) * w)), max(0, int((min(box[1], box[3]) / 100 - pad) * h))
    x1, y1 = min(w, int((max(box[0], box[2]) / 100 + pad) * w) + 1), min(h, int((max(box[1], box[3]) / 100 + pad) * h) + 1)
    crop = im[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    mask = np.sqrt(((crop - np.array(target)) ** 2).sum(axis=2)) < NEAR
    if mask.sum() < 15:
        return None
    # Lines are runs of rows that hold letter pixels, separated by empty rows.
    has = mask.sum(axis=1) >= max(2, int(mask.shape[1] * 0.01))
    runs, start = [], None
    for i, v in enumerate(list(has) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= 3:
                runs.append((start, i))
            start = None
    if not runs:
        return None
    cols = np.where(mask.any(axis=0))[0]
    line_px = statistics.median(e - s for s, e in runs)
    return {
        "lines": len(runs),
        "line_height_pct": round(line_px / h * 100, 1),          # letter height, top of tallest to bottom of lowest
        "line_height_px": round(line_px / h * REEL_H),            # the same on a 1080×1920 reel
        "top_pct": round((y0 + runs[0][0]) / h * 100, 1),
        "bottom_pct": round((y0 + runs[-1][1]) / h * 100, 1),
        "left_pct": round(float(x0 + cols[0]) / w * 100, 1),
        "right_pct": round(float(x0 + cols[-1] + 1) / w * 100, 1),
        "fill": _hex(np.median(crop[mask], axis=0)),              # the letters' colour as measured
    }


def colour(hexs):
    """A measured colour, named when it is really white or black (video compression tints them slightly)."""
    rgb = _rgb(hexs)
    if not rgb:
        return hexs
    if min(rgb) >= 225:
        return f"white (measured {hexs})"
    if max(rgb) <= 35:
        return f"black (measured {hexs})"
    return hexs


def describe(block):
    """One line a designer can follow: font, case, colours, size and position, measured where possible."""
    m = block.get("measured") or {}
    case = {"upper": "ALL CAPS", "lower": "all lowercase", "title": "Title Case", "sentence": "Sentence case"}.get(block.get("case"), block.get("case"))
    bits = [block.get("font") or block.get("family"), block.get("weight"), case, "italic" if block.get("italic") else None,
            f"letters {colour(m.get('fill') or block.get('fill'))}" if (m.get("fill") or block.get("fill")) else None]
    for h in block.get("highlight") or []:
        bits.append(f"“{h.get('words')}” in {h.get('color')}")
    if block.get("stroke"):
        bits.append(f"{block['stroke']} outline")
    if block.get("shadow"):
        bits.append("drop shadow")
    bg = block.get("background") or {}
    if bg.get("color"):
        bits.append(f"on a {bg.get('shape') or 'box'} of {bg['color']}" + (f" at {round(bg['opacity'] * 100)}% opacity" if bg.get("opacity") not in (None, 1) else ""))
    if m:
        bits.append(f"{m['lines']} line{'s' if m['lines'] != 1 else ''}, each {m['line_height_pct']}% of the frame height (≈{m['line_height_px']} px on 1080×1920)")
        bits.append(f"from {m['top_pct']}% to {m['bottom_pct']}% down the frame, {m['left_pct']}–{m['right_pct']}% across")
    elif block.get("box"):
        b = block["box"]
        bits.append(f"about {round(b[1])}–{round(b[3])}% down the frame (size not measured)")
    if block.get("align"):
        bits.append(f"{block['align']}-aligned")
    if block.get("animation") and block["animation"] != "static":
        bits.append(block["animation"])
    return ", ".join(str(b) for b in bits if b)


def check(text, reference_blocks):
    """Make a shot's on-screen text follow its reference's text, and say where it still differs.

    Case and the spacing around symbols such as "+" are mechanical, so they're copied. Line count, punctuation and emoji
    change what the text says, so they're reported, not changed. Returns (text, [differences]).
    """
    if not text or not reference_blocks:
        return text, []
    ref = reference_blocks[0]
    model = ref.get("text") or ""
    kase = ref.get("case")
    if kase == "upper":
        text = text.upper()
    elif kase == "lower":
        text = text.lower()
    for sym in "+&=→×|":  # spacing around a symbol is mechanical: copy the reference's
        if sym in model and sym in text:
            tight = f" {sym} " not in model
            text = re.sub(rf"[ \t]*{re.escape(sym)}[ \t]*", sym if tight else f" {sym} ", text)
    issues = []
    ref_lines, new_lines = model.count("\n") + 1, text.count("\n") + 1
    if len(reference_blocks) == 1 and ref_lines != new_lines:
        issues.append(f"{new_lines} line{'s' if new_lines != 1 else ''} where the reference has {ref_lines}")
    for sym in "+&/=→×|":
        if sym in model and sym in text:
            tight_ref, tight_new = f" {sym} " not in model, f" {sym} " not in text
            if tight_ref != tight_new:
                issues.append(f"“{sym}” {'with' if tight_ref else 'without'} spaces around it; the reference has it {'tight' if tight_ref else 'spaced'}")
    punct = lambda s: {c for c in s if c in ".,!?…:;\"'()-–—"}
    if punct(model) != punct(text):
        extra, missing = sorted(punct(text) - punct(model)), sorted(punct(model) - punct(text))
        issues.append("punctuation differs" + (f": adds {' '.join(extra)}" if extra else "") + (f"; drops {' '.join(missing)}" if missing else ""))
    emoji = lambda s: any(ord(c) > 0x2600 for c in s)
    if emoji(model) != emoji(text):
        issues.append("the reference " + ("uses" if emoji(model) else "has no") + " emoji")
    return text, issues
