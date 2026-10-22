"""Automatic first-pass annotations for the teardown card (AGENT_PLAYBOOK.md, Phase 3).

Only what can be read reliably from data is filled here: stats, transcript-based hooks, pattern matches, series
markers, CTA wording, pacing and audio. Anything that needs watching the video or judgement (written/visual hook,
angle, delivery, format, beats, value) is left for review and marked as such, never guessed.
"""

import re

BEATS = ["HOOK", "CONTEXT", "PROMISE", "NAME_METHOD", "STEP", "EXAMPLE", "PROOF", "MYTH", "TRUTH", "CONTRAST", "TURN",
         "RESULT", "LESSON", "RECAP", "LOOP", "CTA"]

VOCAB = {
    "post_type": ["reel", "carousel", "photo"],
    "hook_pattern": ["is_it_possible", "time_ago", "did_you_know_if", "levels_of", "smart_vs_dumb", "good_better_best",
                     "not_a_flex", "picture_of", "this_to_this", "stop_doing", "if_you_audience", "number_list", "niche_specific"],
    "angle": ["tutorial", "comparison", "myth_bust", "do_dont", "tip_hack", "transformation", "challenge"],
    "video_type": ["ranking", "tier_list", "rapid_fire_qa", "levels", "smart_vs_dumb", "good_better_best", "if_then_list",
                   "two_people_compare", "day_in_the_life", "founder_story", "product_story", "metric_update",
                   "cost_breakdown", "retrospective", "fake_case_study_brand", "fake_case_study_situation", "none"],
    "delivery": ["educational", "storytelling"],
    "story_type": ["my_story", "win", "loss", "lesson", "transformation", "challenge", "big_goal"],
    "series_type": ["daily", "progress_update", "lesson", "step_by_step"],
    "content_type": ["educational", "storytelling", "authority"],
    "funnel": ["tofu", "mofu", "bofu"],
    "complexity": ["easy", "complex"],
    "cta_type": ["follow", "freebie", "paid_offer", "engagement", "none"],
    "cta_mechanic": ["comment_keyword", "follow", "link_in_bio", "dm_keyword", "save_or_share", "none"],
    "format": ["talking_back_forth", "visual_prop", "voiceover", "multitasking", "setting_change", "shot_angle_change",
               "clone", "whiteboard", "qa", "green_screen", "reaction", "audio_broll_text", "talking_head", "unknown"],
    "audio": ["original_voice", "voice_plus_music", "emotional_music", "trending_audio", "music_only", "none", "unknown"],
}

# The 17 teardown elements, in card order. Each entry: (element number, label, field keys).
ELEMENTS = [
    (1, "Performance", ["stats"]),
    (2, "Post type", ["post_type"]),
    (3, "Topic", ["topic"]),
    (4, "Verbal hook", ["verbal_hook"]),
    (5, "Written hook", ["written_hook"]),
    (6, "Visual hook", ["visual_hook"]),
    (7, "Hook pattern", ["hook_pattern"]),
    (8, "Angle", ["angle"]),
    (9, "Video type", ["video_type"]),
    (10, "Delivery & story type", ["delivery", "story_type"]),
    (11, "Series", ["is_series", "series_type", "episode_marker", "series_evidence"]),
    (12, "Content type & funnel", ["content_type", "funnel"]),
    (13, "Script structure", ["complexity", "structure_pattern", "word_count", "words_per_second"]),
    (14, "Value", ["value_summary"]),
    (15, "CTA", ["cta_type", "cta_mechanic", "cta_keyword", "cta_text"]),
    (16, "Format", ["format"]),
    (17, "Editing style", ["audio", "avg_shot_s", "cuts", "captions"]),
]

HOOK_PATTERNS = [
    ("is_it_possible", r"\bis it possible\b"),
    ("time_ago", r"\b(\d+|a|one|two|three|six)\s+(days?|weeks?|months?|years?)\s+ago\b"),
    ("did_you_know_if", r"\bdid you know\b"),
    ("levels_of", r"\b(\d+|two|three|four|five)\s+levels?\s+of\b"),
    ("smart_vs_dumb", r"\bsmart\b.*\b(vs\.?|versus)\b.*\bdumb\b"),
    ("good_better_best", r"\bbad\b.*\bgood\b.*\b(excellent|best|great)\b"),
    ("not_a_flex", r"\bnot (a|to) flex\b"),
    ("picture_of", r"\bthis is a (picture|photo) of\b"),
    ("this_to_this", r"\bfrom this to this\b"),
    ("stop_doing", r"^(stop|don'?t)\b"),
    ("if_you_audience", r"^if (you'?re|you are|you)\b"),
    ("number_list", r"^(\d+|three|four|five|six|seven|eight|nine|ten)\s+(ways|tips|mistakes|things|reasons|steps|signs|rules|habits|lessons)\b"),
]

VIDEO_TYPES = [
    ("tier_list", r"\btier list\b|\b[sabcdf][- ]tier\b"),
    ("ranking", r"(\b\d{1,2}\s*(/|out of)\s*10\b.*){2,}"),
    ("rapid_fire_qa", r"\bthis or that\b|\brapid[- ]fire\b"),
    ("levels", r"\b(\d+|two|three|four|five)\s+levels?\s+of\b"),
    ("smart_vs_dumb", r"\bsmart\b.*\bdumb\b"),
    ("good_better_best", r"\bbad\b.{0,80}\bgood\b.{0,80}\bexcellent\b"),
    ("two_people_compare", r"\btwo (people|couples|guys|girls|friends|business owners|\w+s) (are )?(trying|want)\b"),
    ("day_in_the_life", r"\bday in (the|my) life\b"),
    ("founder_story", r"\b(i|we) started (my|our|this) (business|company|brand)\b|\bhow i started\b"),
    ("product_story", r"\bprototype\b|\bhow (we|i) (made|built|created) (this|our|my) (product|app|brand)\b"),
    ("metric_update", r"\bhow much (i|we) made\b|\b(revenue|income) (report|update)\b"),
    ("cost_breakdown", r"\bcost breakdown\b|\bhow much (it|this) cost\b"),
    ("retrospective", r"\bwhat i('d| would) do differently\b|\bif i could start over\b"),
    ("fake_case_study_brand", r"\bif i (were|was) (the )?(ceo|running|in charge) of\b|\bif i had to (create content|market) for\b"),
    ("fake_case_study_situation", r"\bif i (were|was|had to) start(ing)? (from scratch|over)\b|\bif i had \$?[\d,]+\b"),
]

SERIES_MARKER = re.compile(r"\b(day|part|episode|ep\.?|lesson|step|week|month)\s*#?\s*(\d{1,4})\b", re.I)


def field(value, source, note=None):
    """source: api | auto (read directly from data) | heuristic (pattern match, check it) | needs_review | human."""
    return {"value": value, "source": source, "note": note}


def normalize(text):
    return (text or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').lower().strip()


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def verbal_hook(transcript):
    """Words spoken before 3 s, extended to the end of that sentence (or the first sentence without timestamps)."""
    if not transcript or not transcript.get("text"):
        return field(None, "needs_review", "No transcript available")
    segments = transcript.get("segments")
    if segments:
        words = []
        for seg in segments:
            if seg["start"] < 3.0 or (words and not re.search(r"[.!?]$", " ".join(words))):
                words.append(seg["text"].strip())
            else:
                break
            if len(" ".join(words).split()) >= 30:
                break
        if words:
            return field(" ".join(words), "auto", "Speech in the first 3 seconds, to the end of the sentence")
    first = sentences(transcript["text"])[:1]
    text = " ".join(first[0].split()[:25]) if first else None
    return field(text, "auto", "First sentence (no timestamps available)")


def match_first(patterns, text, default):
    norm = normalize(text)
    for name, rx in patterns:
        if re.search(rx, norm, re.S):
            return name
    return default


def hook_pattern(hook_text, caption_first_line):
    found = match_first(HOOK_PATTERNS, hook_text or "", None) or match_first(HOOK_PATTERNS, caption_first_line or "", None)
    if found:
        return field(found, "heuristic", "Matched the hook's frame words")
    return field("niche_specific", "heuristic", "No universal pattern matched; check the written hook too")


def video_type(transcript_text, caption):
    found = match_first(VIDEO_TYPES, f"{caption}\n{transcript_text}", None)
    if found:
        return field(found, "heuristic", "Matched signal words in the caption or transcript")
    if sum(1 for s in sentences(transcript_text) if normalize(s).startswith("if you")) >= 3:
        return field("if_then_list", "heuristic", "3+ sentences start with 'If you'")
    return field("none", "heuristic", "No named video type detected")


def series(hook_text, caption, sibling_reels):
    """Marker in the hook/caption, confirmed by 2+ sibling reels from the same creator with the same marker word."""
    first_line = (caption or "").split("\n")[0]
    m = SERIES_MARKER.search(f"{hook_text or ''} {first_line}")
    if not m:
        return {"is_series": field(False, "heuristic", "No episode marker in the hook or caption"),
                "series_type": field(None, "auto"), "episode_marker": field(None, "auto"), "series_evidence": field([], "auto")}
    word = m.group(1).lower().rstrip(".")
    marker = f"{m.group(1)} {m.group(2)}"
    siblings = []
    for reel in sibling_reels:
        sm = SERIES_MARKER.search((reel["caption"] or "").split("\n")[0])
        if sm and sm.group(1).lower().rstrip(".") == word and sm.group(2) != m.group(2):
            siblings.append(reel)
    if len(siblings) < 2:
        return {"is_series": field(False, "heuristic", f'Marker "{marker}" found, but fewer than 2 sibling episodes among scanned reels'),
                "series_type": field(None, "auto"), "episode_marker": field(marker, "auto"),
                "series_evidence": field([r["url"] for r in siblings], "auto")}
    if word == "day":
        series_type = "daily"
    elif word == "lesson":
        series_type = "lesson"
    elif word in ("step", "part"):
        series_type = "step_by_step"
    else:
        series_type = "progress_update"
    return {"is_series": field(True, "heuristic", f"{len(siblings)} sibling episodes share the \"{word} N\" marker"),
            "series_type": field(series_type, "heuristic", f'From the "{word}" marker'),
            "episode_marker": field(marker, "auto"),
            "series_evidence": field([r["url"] for r in siblings[:5]], "auto")}


def cta(transcript_text, caption):
    tail = " ".join(sentences(transcript_text)[-3:])
    text = f"{tail}\n{(caption or '').split(chr(10))[0]}"
    norm = normalize(text)
    paid = re.search(r"\b(program|course|coaching|enroll|join|apply|work with (me|us)|mastermind|details)\b", norm)
    m = re.search(r"\bcomment\s+[\"']?([a-z0-9]{2,20})[\"']?", norm)
    if m:
        keyword = m.group(1).upper()
        return {"cta_type": field("paid_offer" if paid else "freebie", "heuristic", "Comment-keyword CTA; offer type guessed from wording"),
                "cta_mechanic": field("comment_keyword", "auto"), "cta_keyword": field(keyword, "auto"),
                "cta_text": field(_cta_sentence(text, "comment"), "auto")}
    for rx, mechanic, kind in [(r"link in (my |the )?bio", "link_in_bio", "freebie"), (r"\b(dm|message) me\b", "dm_keyword", "freebie"),
                               (r"\bfollow (me|for|along)\b", "follow", "follow"), (r"\b(save|share) this\b|\bsend this to\b", "save_or_share", "engagement")]:
        if re.search(rx, norm):
            if mechanic != "follow" and paid:
                kind = "paid_offer"
            return {"cta_type": field(kind, "heuristic"), "cta_mechanic": field(mechanic, "auto"),
                    "cta_keyword": field(None, "auto"), "cta_text": field(_cta_sentence(text, rx), "auto")}
    return {"cta_type": field("none", "heuristic", "No ask found in the last sentences or caption"),
            "cta_mechanic": field("none", "heuristic"), "cta_keyword": field(None, "auto"), "cta_text": field(None, "auto")}


def _cta_sentence(text, rx):
    for s in sentences(text.replace("\n", ". ")):
        if re.search(rx, normalize(s)):
            return s
    return None


def structure(transcript_text, duration):
    sents = sentences(transcript_text)
    words = len((transcript_text or "").split())
    starts = {}
    for s in sents:
        key = " ".join(normalize(s).split()[:2])
        starts[key] = starts.get(key, 0) + 1
    repeated = max(starts.values()) if starts else 0
    complexity = "easy" if repeated >= 3 else "complex"
    note = f"{repeated} sentences share the same opening" if repeated >= 3 else "No sentence shape repeats 3+ times"
    return {
        "complexity": field(complexity if sents else None, "heuristic" if sents else "needs_review", note if sents else "No transcript"),
        "structure_pattern": field(None, "needs_review", "Label each sentence's beat (HOOK, STEP, PROOF…)"),
        "word_count": field(words or None, "auto"),
        "words_per_second": field(round(words / duration, 1) if words and duration else None, "auto"),
    }


def audio(music_info, has_speech):
    if not music_info:
        return field("unknown", "needs_review")
    original = music_info.get("uses_original_audio")
    if original and has_speech:
        return field("original_voice", "heuristic", "Original audio with speech; listen for a music bed (voice_plus_music)")
    if not original and has_speech:
        return field("voice_plus_music", "heuristic", f'Speech over "{music_info.get("song_name")}"')
    if not original:
        return field("music_only", "heuristic", f'"{music_info.get("song_name")}"; mark trending_audio if many reels use it')
    return field("unknown", "needs_review", "Original audio but no transcript")


def format_guess(avg_shot_s):
    if avg_shot_s is not None and avg_shot_s <= 2.5:
        return field("shot_angle_change", "heuristic", f"Fast cutting ({avg_shot_s}s per shot); confirm with the frames")
    return field(None, "needs_review", "Use the frames and the format checklist (playbook step 3.3)")
