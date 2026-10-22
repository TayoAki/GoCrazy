"""Madlib variables: line a template up against the words that filled it, so its blanks become named values that can
be shown (the reference's original variables, the plan's variables) and changed (your own version).

A sheet is {"lines": [...], "variables": [...]}. Each line keeps its template, how many times its [REPEAT] block ran,
the words that filled it and, in order, the (slot, value) pair behind every blank. A variable is one distinct
(slot, value) pair: "baggy jeans" in the hook, the spoken line and the on-screen text is one variable, so changing it
rewrites all three, while the different items of a list stay separate variables.
"""

import re

SLOT = re.compile(r"\{\{([A-Z0-9_]+)(?::[A-Z_]+)?\}\}")
REPEAT = re.compile(r"\[REPEAT[^\]]*\](.*?)\[/REPEAT\]", re.S)
PUNCT = ",;:.!?…–—-"


def _frame(text, first, last, end_ok):
    """Frame words as a loose regex: same words in order; spacing, case and punctuation between them may drift.

    A frame of punctuation only (", " between two blanks) must really be there, or a blank could swallow half a word;
    at the very end of a template the closing punctuation may also be missing.
    """
    words = re.findall(rf"[^\s{PUNCT}]+", text)
    sep = rf"[\s{PUNCT}]*"
    if words:
        body = sep.join((r"\b" if w[0].isalnum() else "") + re.escape(w) + (r"\b" if w[-1].isalnum() else "") for w in words)
        return sep + body + sep
    has_punct = any(c in PUNCT for c in text)
    if first:
        return sep
    if has_punct:
        return rf"(?:\s*[{PUNCT}]+\s*|\s*$)" if last and end_ok else rf"\s*[{PUNCT}]+\s*"
    return r"\s*" if last else r"\s+"


def _pattern(template, end_ok=True):
    parts = SLOT.split(template)  # frame, name, frame, name, ..., frame
    regex, names = "", []
    for i, part in enumerate(parts):
        if i % 2:
            regex += r"(\S.*?)"
            names.append(part)
        else:
            regex += _frame(part, i == 0, i == len(parts) - 1, end_ok)
    return regex, names


def _clean(value):
    return value.strip().strip(PUNCT).strip()


def align(template, text):
    """[(slot, value), ...] in the order the blanks are used, and the repeat count; None if the words don't fit."""
    if not template or not text:
        return None
    pieces = REPEAT.split(template)  # outside, inner, outside, ...
    regex, plan = "", []
    for i, piece in enumerate(pieces):
        if i % 2:
            regex += r"(\S.*?)"
            plan.append(("repeat", piece))
        else:
            r, names = _pattern(piece, end_ok=i == len(pieces) - 1)  # only the template's true end may drop its punctuation
            regex += r
            plan += [("slot", n) for n in names]
    match = re.fullmatch(regex, text.strip(), re.I | re.S)
    if not match:
        return None
    uses, count = [], 1
    for (kind, item), value in zip(plan, match.groups()):
        if kind == "slot":
            uses.append((item, _clean(value)))
            continue
        inner, names = _pattern(item)
        found = list(re.finditer(inner, value.strip(), re.I | re.S))
        if not found or not names or sum(len(m.group(0)) for m in found) < len(value.strip()) * 0.8:
            return None
        count = len(found)
        for m in found:
            uses += [(n, _clean(v)) for n, v in zip(names, m.groups())]
    return uses, count


def sheet(lines, slots=None):
    """lines: [(label, template, filled text)] -> {"lines", "variables"}; slots: the madlib's fill rules, by name."""
    rules = {s.get("name"): s for s in slots or []}
    out, variables, seen = [], [], set()
    for label, template, text in lines:
        if not template:
            continue
        got = align(template, text)
        uses = [[n, v] for n, v in got[0]] if got else []
        for n, v in uses:
            if (n, v.lower()) not in seen:
                seen.add((n, v.lower()))
                variables.append({"slot": n, "value": v, "type": (rules.get(n) or {}).get("type"), "rule": (rules.get(n) or {}).get("rule")})
        out.append({"label": label, "template": template, "count": got[1] if got else 1, "text": text,
                    "aligned": bool(got), "uses": uses})
    return {"lines": out, "variables": variables}


def render(sh, changes=None):
    """Each line filled again, with {(slot, original value): new value} applied. Lines that didn't line up stay as they were."""
    changes = {(k[0], k[1].lower()): v for k, v in (changes or {}).items()}
    out = []
    for line in sh["lines"]:
        if not line["aligned"]:
            out.append(line["text"] or line["template"])
            continue
        uses = iter(line["uses"])

        def fill(t):
            def one(_):
                n, v = next(uses, (None, ""))
                return changes.get((n, v.lower()), v)
            return SLOT.sub(one, t)

        pieces = REPEAT.split(line["template"])
        text = "".join(fill(p) if i % 2 == 0 else " ".join(fill(p).strip() for _ in range(line["count"])) for i, p in enumerate(pieces))
        out.append(re.sub(r"\s+", " ", text).strip())
    return out


def reference_sheet(madlib):
    """The reference reel's madlib lined up against its original words: its original variables."""
    hooks = madlib.get("hooks") or {}
    lines = [(f"{k.capitalize()} hook", (hooks.get(k) or {}).get("template"), (hooks.get(k) or {}).get("original"))
             for k in ("verbal", "written", "visual")]
    lines += [(x.get("beat") or "Line", x.get("template"), x.get("original")) for x in madlib.get("spoken") or []]
    lines += [("On screen", x.get("template"), x.get("original")) for x in madlib.get("on_screen") or []]
    cap = madlib.get("caption") or {}
    lines.append(("Caption", cap.get("template"), cap.get("original")))
    return sheet(lines, madlib.get("slots"))


def post_sheet(post, slots=None):
    """A planned post's script lined up against the madlib it filled: the plan's variables."""
    hook = post.get("hook") or {}
    lines = [(f"{k.capitalize()} hook", hook.get(f"{k}_template"), hook.get(k)) for k in ("verbal", "written", "visual")]
    lines += [(b.get("label") or "Line", b.get("template"), b.get("say")) for b in post.get("beats") or []]
    return sheet(lines, slots)
