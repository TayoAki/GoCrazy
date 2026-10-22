"""One way to ask a model for JSON, whichever model does the work.

Providers:
- "claude-code": the Claude Code CLI on this machine (`claude -p`), running on your Claude plan instead of per-token
  credits. It may only use its Read tool, only on the media folder, and keeps no session history.
- "openrouter": OpenRouter's API with OPENROUTER_API_KEY (the model is the project's ai_model setting).

AI_PROVIDER picks one; otherwise Claude Code is used when the CLI is installed, then OpenRouter.
"""

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile

import requests

from .config import MEDIA, openrouter_key

URL = "https://openrouter.ai/api/v1/chat/completions"
CLAUDE = os.environ.get("CLAUDE_CLI") or shutil.which("claude")


def provider():
    chosen = (os.environ.get("AI_PROVIDER") or "").strip().lower()
    if chosen in ("claude-code", "openrouter"):
        return chosen if (chosen == "openrouter" and openrouter_key()) or (chosen == "claude-code" and CLAUDE) else None
    return "claude-code" if CLAUDE else "openrouter" if openrouter_key() else None


def available():
    return provider() is not None


def label(model):
    return "claude-code" + (f" ({os.environ['CLAUDE_CODE_AI_MODEL']})" if os.environ.get("CLAUDE_CODE_AI_MODEL") else "") \
        if provider() == "claude-code" else model


def ask(system, parts, model, max_tokens=6000, temperature=0.3):
    """parts: [("text", str) | ("image", path)]. Returns (reply text, cost in dollars; 0 on a Claude plan)."""
    which = provider()
    if which == "claude-code":
        return _claude_code(system, parts)
    if which == "openrouter":
        return _openrouter(system, parts, model, max_tokens, temperature)
    raise RuntimeError("No AI provider: install Claude Code (the `claude` command) or set OPENROUTER_API_KEY")


def ask_json(system, parts, model, max_tokens=6000, temperature=0.3):
    """ask(), parsed as JSON, with one repair pass when the reply isn't valid JSON. Returns (object, cost)."""
    reply, cost = ask(system, parts, model, max_tokens, temperature)
    try:
        return parse(reply), cost
    except ValueError:
        fixed, fix_cost = ask("You repair broken JSON. Reply with only the corrected JSON object, changing nothing else.",
                              [("text", reply)], model, max_tokens, 0)
        return parse(fixed), cost + fix_cost


def parse(reply):
    match = re.search(r"\{.*\}", reply or "", re.S)
    if not match:
        raise ValueError("no JSON object in the reply")
    return json.loads(match.group(0))  # JSONDecodeError is a ValueError


def _openrouter(system, parts, model, max_tokens, temperature):
    content = [{"type": "text", "text": p} if kind == "text" else
               {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode()}}
               for kind, p in parts]
    resp = requests.post(URL, timeout=300, headers={"Authorization": f"Bearer {openrouter_key()}"}, json={
        "model": model, "temperature": temperature, "max_tokens": max_tokens, "usage": {"include": True},
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
    })
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code != 200 or "choices" not in body:
        raise RuntimeError(f"OpenRouter {resp.status_code}: {(body.get('error') or {}).get('message') or resp.text[:200]}")
    return body["choices"][0]["message"]["content"] or "", (body.get("usage") or {}).get("cost") or 0


def _claude_code(system, parts):
    images = [p for kind, p in parts if kind == "image"]
    prompt = []
    if images:
        prompt.append("Before answering, open every image listed below with the Read tool, in order. Each is a frame of "
                      "the video; refer to it by its number.")
    n = 0
    for kind, p in parts:
        if kind == "image":
            n += 1
            prompt.append(f"[IMAGE {n}: {p}]")
        else:
            prompt.append(p)
    prompt.append("Reply with only the JSON object, no other text.")
    with tempfile.TemporaryDirectory() as empty:  # an empty working folder: no project files, settings or hooks
        cmd = [CLAUDE, "-p", "--output-format", "json", "--system-prompt", system, "--tools", "Read",
               "--allowedTools", "Read", "--add-dir", str(MEDIA), "--no-session-persistence", "--strict-mcp-config",
               "--setting-sources", "", "--max-turns", str(len(images) + 6)]
        if os.environ.get("CLAUDE_CODE_AI_MODEL"):
            cmd += ["--model", os.environ["CLAUDE_CODE_AI_MODEL"]]
        run = subprocess.run(cmd, input="\n\n".join(prompt), capture_output=True, text=True, cwd=empty, timeout=900)
    raw = run.stdout[run.stdout.find("{"):] if "{" in run.stdout else ""
    try:
        out = json.loads(raw)
    except ValueError:
        raise RuntimeError(f"Claude Code failed ({run.returncode}): {(run.stderr or run.stdout)[-300:]}")
    if out.get("is_error"):
        raise RuntimeError(f"Claude Code: {str(out.get('result'))[:300]}")
    return out.get("result") or "", 0  # on a Claude plan there's no per-call charge
