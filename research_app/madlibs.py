"""Madlib variables: line a template up against the words that filled it, so its blanks become named values that can
be shown (the reference's original variables, the plan's variables) and changed (your own version).

A sheet is {"lines": [...], "variables": [...]}. Each line keeps its template, how many times its [REPEAT] block ran,
the words that filled it and, in order, the (slot, value) pair behind every blank. A variable is one distinct
(slot, value) pair: "baggy jeans" in the hook, the spoken line and the on-screen text is one variable, so changing it
rewrites all three, while the different items of a list stay separate variables.
"""

import re
import time

import regex  # like re, but a match can be given a time limit

SLOT = re.compile(r"\{\{([A-Z0-9_]+)(?::[A-Z_]+)?\}\}")
REPEAT = re.compile(r"\[REPEAT[^\]]*\](.*?)\[/REPEAT\]", re.S)
PUNCT = ",;:.!?…–—-"
ALIGN_SECONDS = 1.0  # time limit for aligning one line


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
    if last:
        return r"\s*"
    return r"[ \t]*\n\s*" if "\n" in text else r"\s+"  # a line break between two blanks must be a line break


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
    regex_text, plan = "", []
    for i, piece in enumerate(pieces):
        if i % 2:
            regex_text += r"(\S.*?)"
            plan.append(("repeat", piece))
        else:
            r, names = _pattern(piece, end_ok=i == len(pieces) - 1)  # only the template's true end may drop its punctuation
            regex_text += r
            plan += [("slot", n) for n in names]
    # Lazy blanks between frame words can backtrack for minutes on a line that almost fits, and re holds the whole
    # server while it does; so every match on a line shares a time limit, and a line that runs out stays unaligned.
    deadline = time.monotonic() + ALIGN_SECONDS
    try:
        return _align(text, regex_text, plan, deadline)
    except TimeoutError:
        return None


def _match(pattern, text, deadline, find=False):
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError
    if find:
        return list(regex.finditer(pattern, text, regex.I | regex.S, timeout=left))
    return regex.fullmatch(pattern, text, regex.I | regex.S, timeout=left)


def _align(text, regex_text, plan, deadline):
    match = _match(regex_text, text.strip(), deadline)
    if not match:
        return None
    uses, count = [], 1
    for (kind, item), value in zip(plan, match.groups()):
        if kind == "slot":
            uses.append((item, _clean(value)))
            continue
        # A separator after a repeat's last word (" / ") joins it to the next one; the joints below cover it. A leading
        # bullet stays: it marks where each repeat starts.
        item = re.sub(r"\s*[/|]+\s*$", "", item)
        inner, names = _pattern(item)
        found = _match(inner, value.strip(), deadline, find=True)
        if not found or not names:
            return None
        if re.search(r"\w", SLOT.sub("", item)):
            # Frame words mark where each repeat starts, so match the repeats back to back, trying the most first so one
            # repeat can't swallow two. (Without frame words this would try every split, so those keep the scan below.)
            # Repeats meet at punctuation, a slash or a line break; only short lines may meet at a bare space, since
            # that joint can backtrack for minutes on a long one.
            # Punctuation only joins repeats where it touches a space or a line break, so PUSH-UPS stays one word.
            sep = f"[/|•{PUNCT}]"
            joints = [rf"(?:\s+{sep}+\s*|\s*{sep}+\s+|\s*\n\s*|(?<={sep}\s)\s*|(?<=\s{sep})\s*|(?<=\n))"]
            if len(value) <= 160:
                joints.append(rf"(?:\s+{sep}+\s*|\s*{sep}+\s+|\s+|(?<=\s))")
            m = next((m for count in range(len(found), 0, -1) for joint in joints
                      if (m := _match(joint.join([inner] * count), value.strip(), deadline))), None)
            if not m:
                return None
            count = len(m.groups()) // len(names)
            uses += [(n, _clean(v)) for n, v in zip(names * count, m.groups())]
            continue
        # Blanks only: each repeat runs to a line break, punctuation, a slash or the end, so its last blank can't stop short.
        found = _match(r"[\s/|•]*" + inner + rf"(?:(?<=[\n/|•{PUNCT}])|(?<=[\n/|•{PUNCT}]\s)|(?=\s*$|\s*\n|\s*[/|•{PUNCT}]))",
                       value.strip(), deadline, find=True)
        if not found or sum(len(m.group(0)) for m in found) < len(value.strip()) * 0.8:
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


COMMON = set("""I The A An And Or But If So You Your My We Our It This That These Those Here There What Why How When Where Who
Which Remember Save Follow Comment Share Like Day Part Step Number First Second Third Last Next Today Now Yes No Not Instagram
Reel Reels TikTok YouTube""".split())


def distinctive(lines):
    """The reference's own specific content: numbers (3+ digits) and names. A name is a capitalised word that appears
    somewhere other than the start of a sentence, is never written in lowercase in the reference, and isn't all caps
    (all caps is emphasis). Hashtags, handles and links are ignored."""
    text = re.sub(r"https?://\S+|[#@][\w.]+", " ", "\n".join(l for l in lines if l))
    lower = set(re.findall(r"\b[a-z][\w'’]*", text))
    found = set()
    for sentence in re.split(r"(?<=[.!?:\n])\s+|\n", text):
        words = [w.strip(".,'’!?:;()\"") for w in re.findall(r"[\w'’,.]+", sentence)]
        long = [w for w in words if len(w) >= 3 and w[0].isalpha()]
        title_case = len(long) >= 3 and sum(w[0].isupper() for w in long) / len(long) >= 0.6  # a headline: capitals mean nothing
        for k, w in enumerate(words):
            digits = re.sub(r"\D", "", w)
            if len(digits) >= 3 and not re.fullmatch(r"[1-9]0{2,3}", digits):  # 100, 500, 1000 are too common to count
                found.add(w)
            elif (k > 0 and not title_case and len(w) >= 3 and w[0].isupper() and not w.isupper()
                  and not re.match(r"I['’]", w) and w.lower() not in lower and w not in COMMON):
                found.add(w)
    return found


def reused(text, tokens):
    """Which of the reference's own content words a text reuses."""
    return sorted(t for t in tokens if re.search(rf"(?<![\w]){re.escape(t)}(?![\w])", text or ""))


def copies(text, tokens):
    """A text copies the reference's content when it reuses any of its numbers, or two or more of its names."""
    hits = reused(text, tokens)
    return hits if any(re.search(r"\d", h) for h in hits) or len(hits) >= 2 else []
