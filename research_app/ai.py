"""AI annotation of a teardown through OpenRouter: the model looks at the frames, transcript and caption and fills the
fields that need eyes or judgement, choosing only from the playbook's closed vocabularies."""

import base64
import json
import re

import requests

from .annotate import VOCAB, field
from .config import MEDIA, openrouter_key

URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_OVERVIEW_FRAMES = 12

SYSTEM = """You analyze one viral short-form video (an Instagram reel) so its structure can be reused as a template.
You get: hook frames (the first 3 seconds, 0.5 s apart), overview frames (sampled across the video), the transcript
with timestamps, the caption, stats, and some automatic pre-annotations (treat those as hints, not truth).

Rules:
- Describe what is actually there. Never invent on-screen text you cannot read; use null instead.
- For every enum field, use exactly one of the allowed values given below.
- Be concise: one sentence for descriptions.

Allowed values:
hook_pattern: is_it_possible ("Is it possible to…"), time_ago ("[N] days/months/years ago I…"), did_you_know_if,
  levels_of ("[N] levels of…"), smart_vs_dumb, good_better_best (bad/good/excellent ladder), not_a_flex,
  picture_of ("This is a picture of…"), this_to_this ("from this to this"), stop_doing (opens with Stop/Don't),
  if_you_audience ("If you're a…"), number_list ("[N] ways/tips/mistakes…"), niche_specific (none of these).
angle: tutorial (step-by-step/framework), comparison, myth_bust (debunks belief or mistake), do_dont (right vs wrong),
  tip_hack (one-off tip), transformation (before/after + how), challenge.
video_type: ranking, tier_list, rapid_fire_qa, levels, smart_vs_dumb, good_better_best, if_then_list, two_people_compare,
  day_in_the_life, founder_story, product_story, metric_update, cost_breakdown, retrospective, fake_case_study_brand,
  fake_case_study_situation, none.
delivery: educational (teaches) | storytelling (told as a narrative).
story_type (only if storytelling, else null): my_story, win, loss, lesson, transformation, challenge, big_goal.
series_type (only if it is a series episode, else null): daily, progress_update, lesson, step_by_step.
content_type: educational (authority through knowledge), storytelling (connection), authority (results/proof/testimonials).
funnel: tofu (broad, simple, for views), mofu (personal, for followers), bofu (in-depth, proof or offer, for leads).
complexity: easy (one sentence shape repeats 3+ times with only nouns/numbers changing) | complex (anything else).
cta_type: follow, freebie, paid_offer, engagement, none.
cta_mechanic: comment_keyword, follow, link_in_bio, dm_keyword, save_or_share, none.
audio: original_voice, voice_plus_music, emotional_music, trending_audio, music_only, none.
format — go through this list IN ORDER and pick the FIRST that is true:
  1 reaction (another video visible inset/split screen), 2 clone (same person twice in one frame),
  3 talking_back_forth (same person alternates two characters/looks in dialogue), 4 whiteboard (whiteboard/paper/tablet
  writing in 30%+ of frames), 5 green_screen (speaker composited over image/video), 6 qa (off-camera question, on-camera
  answer, often a handheld mic), 7 if no speaker on camera in 70%+ of frames: audio_broll_text (story carried by on-screen
  text over music, new image every 1-3 s) else voiceover, 8 multitasking (talking while doing an unrelated task),
  9 setting_change (location changes 3+ times), 10 visual_prop (props demonstrate the point), 11 shot_angle_change
  (new shot about every 2 s in one location), 12 talking_head.
Beat labels for structure_pattern: HOOK, CONTEXT, PROMISE, NAME_METHOD, STEP, EXAMPLE, PROOF, MYTH, TRUTH, CONTRAST, TURN,
  RESULT, LESSON, RECAP, LOOP, CTA. Write repeats as STEP×3. Join with " → ".

Reply with ONLY a JSON object with exactly these keys:
{"topic": str, "written_hook": str|null, "visual_hook": str, "hook_pattern": str, "angle": str, "video_type": str,
 "delivery": str, "story_type": str|null, "is_series": bool, "series_type": str|null, "episode_marker": str|null,
 "content_type": str, "funnel": str, "complexity": str, "structure_pattern": str, "value_summary": str,
 "value_measurable": bool, "cta_type": str, "cta_mechanic": str, "cta_keyword": str|null, "cta_text": str|null,
 "format": str, "format_evidence": str, "audio": str, "has_speech": bool, "captions": str, "notes": str}
- written_hook: the largest on-screen text in the hook frames, copied exactly (null if none).
- visual_hook: what happens on screen in the first 3 seconds.
- Trust AUDIO FACTS FROM INSTAGRAM over your own guess about the soundtrack.
- has_speech: false if nobody talks (music or song lyrics only); then the transcript is lyrics, not a hook.
- captions: caption style, e.g. "word_by_word, center, 2 colors" or "none".
- format_evidence: which frames show it, e.g. "overview 3-9: two copies of the creator side by side".
- notes: anything a human reviewer should double-check."""

ENUM_FIELDS = {"hook_pattern", "angle", "video_type", "delivery", "story_type", "series_type", "content_type", "funnel",
               "complexity", "cta_type", "cta_mechanic", "format", "audio"}
TEXT_FIELDS = {"topic", "written_hook", "visual_hook", "episode_marker", "structure_pattern", "value_summary",
               "cta_keyword", "cta_text", "captions"}
# Values read straight from data are only filled by the AI when they are empty.
KEEP_IF_SET = {"cta_keyword", "cta_text"}


def _data_url(path):
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def _frame_paths(data, key, limit=None):
    names = [url.rsplit("/", 1)[-1] for url in (data.get("media") or {}).get(key) or []]
    if limit and len(names) > limit:
        step = len(names) / limit
        names = [names[int(i * step)] for i in range(limit)]
    folder = MEDIA / data["shortcode"]
    return [folder / n for n in names if (folder / n).exists()]


def _transcript_text(transcript):
    if not transcript:
        return "(no transcript)"
    if transcript.get("segments"):
        return "\n".join(f"[{s['start']:.1f}s] {s['text'].strip()}" for s in transcript["segments"])
    return transcript["text"]


def _audio_facts(music):
    if not music or music.get("uses_original_audio") is None:
        return "unknown"
    if music.get("uses_original_audio"):
        return "the reel uses its own original audio (the creator's recording), so the transcript is probably real speech"
    return (f'the reel uses a licensed track ("{music.get("song_name")}" by {music.get("artist_name")}), so the '
            "transcript may be song lyrics; set has_speech=false unless it clearly reads like someone talking")


def analyze(data, model):
    """Call the model and return (parsed_json, usage). Raises on HTTP or parse errors."""
    fields = data["fields"]
    hints = {k: fields[k]["value"] for k in ("verbal_hook", "hook_pattern", "video_type", "is_series", "series_type",
                                              "episode_marker", "complexity", "cta_type", "cta_mechanic", "cta_keyword",
                                              "audio", "avg_shot_s", "cuts", "post_type") if k in fields}
    stats = fields["stats"]["value"]
    hook_frames = _frame_paths(data, "hook_frames")
    overview = _frame_paths(data, "frames", MAX_OVERVIEW_FRAMES)
    text = (f"Creator: @{data['username']} · views {stats.get('views')} · followers {stats.get('followers')} · "
            f"ratio {stats.get('ratio')}× · length {stats.get('duration_s')} s\n\n"
            f"AUDIO FACTS FROM INSTAGRAM: {_audio_facts(data.get('music'))}\n\n"
            f"CAPTION:\n{(data.get('caption') or '')[:2000]}\n\nTRANSCRIPT:\n{_transcript_text(data.get('transcript'))[:8000]}\n\n"
            f"AUTOMATIC PRE-ANNOTATIONS (hints):\n{json.dumps(hints)}")
    content = [{"type": "text", "text": text}]
    if hook_frames:
        content.append({"type": "text", "text": f"HOOK FRAMES (first 3 s, 0.5 s apart, {len(hook_frames)} images):"})
        content += [{"type": "image_url", "image_url": {"url": _data_url(p)}} for p in hook_frames]
    if overview:
        content.append({"type": "text", "text": f"OVERVIEW FRAMES (sampled across the video, {len(overview)} images, numbered in order):"})
        content += [{"type": "image_url", "image_url": {"url": _data_url(p)}} for p in overview]
    if not hook_frames and not overview:
        content.append({"type": "text", "text": "(No frames available: set written_hook to null and format to \"unknown\". "
                        "Set visual_hook only if the transcript makes it obvious, otherwise null.)"})

    resp = requests.post(URL, timeout=180, headers={"Authorization": f"Bearer {openrouter_key()}"}, json={
        "model": model, "temperature": 0.2, "max_tokens": 2000, "usage": {"include": True},
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}],
    })
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code != 200 or "choices" not in body:
        raise RuntimeError(f"OpenRouter {resp.status_code}: {(body.get('error') or {}).get('message') or resp.text[:200]}")
    reply = body["choices"][0]["message"]["content"] or ""
    match = re.search(r"\{.*\}", reply, re.S)
    if not match:
        raise RuntimeError("The model did not return JSON")
    return json.loads(match.group(0)), body.get("usage") or {}


def merge(data, result, model, usage):
    """Write AI values into the card. Human edits are never touched; data-derived values are kept when present."""
    fields = data["fields"]
    note_for = {"format": result.get("format_evidence"),
                "value_summary": None if result.get("value_measurable") is None else
                ("Measurable" if result.get("value_measurable") else "Looks fluffy: not specific enough to act on")}
    for key in ENUM_FIELDS | TEXT_FIELDS | {"is_series"}:
        if key not in fields or key not in result:
            continue
        current = fields[key]
        if current.get("source") == "human":
            continue
        value = result[key]
        if key in ENUM_FIELDS and value is not None and value not in VOCAB[key]:
            continue  # off-vocabulary answer: keep what we had
        if key in KEEP_IF_SET and current.get("value"):
            continue
        if key in ("is_series", "series_type") and current.get("source") == "heuristic" and fields["is_series"]["value"]:
            continue  # sibling-episode evidence beats a single-video guess
        fields[key] = field(value, "ai", note_for.get(key))
    if result.get("has_speech") is False:
        # A music-only reel's "transcript" is song lyrics: no use for templating, and not ours to keep.
        data["transcript"] = None
        for key in ("word_count", "words_per_second"):
            if key in fields:
                fields[key] = field(None, "ai", "No speech")
        if fields.get("verbal_hook", {}).get("source") != "human":
            fields["verbal_hook"] = field(None, "ai", "No one speaks (music only), so there is no verbal hook")
    data["ai"] = {"model": model, "notes": result.get("notes"), "cost": usage.get("cost"),
                  "tokens": {"in": usage.get("prompt_tokens"), "out": usage.get("completion_tokens")}}
    return data
