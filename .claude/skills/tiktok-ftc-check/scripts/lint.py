"""First pass of the check: flag every line of a campaign, brief, caption or slide spec that touches a rule.

    python3 lint.py <file> [<file> ...]          # .md, .txt or .json (post.json, campaign.json)

It finds the lines a person has to rule on and names the rules (references/rules.md) to rule with. It doesn't decide:
a hit on "before and after" is fine for a real person's own photos and ❌ for generated ones. It also reports what's
missing: no paid-post disclosure anywhere is a finding of its own.
"""

import json
import re
import sys
from pathlib import Path

CHECKS = [
    (r"watermark|synth ?id|c2pa|content credentials|remove (the )?(ai )?label|avoid (the )?(ai )?label|undetect|bypass",
     "A2", "removing AI provenance or avoiding the AI label"),
    (r"\bgemini\b|midjourney|dall.?e|stable diffusion|nano banana|\bai[- ]generat|\bai (image|photo|picture|model)|faceless ai|generate[ds]? (an |the )?(image|photo|picture|body)|prompt",
     "A1 A3 A4 T1", "AI-generated images: labelled, and never standing in for a real person or their results"),
    (r"transformation|before[- /&]*(and[- ])?after|before/after|progress (photo|pic|picture)|struggle\s*(→|->|to)\s*progress|my (glp-?1 )?journey|weight loss journey",
     "T1 T2 R1", "a person's results or journey: real, theirs, and with typical results"),
    (r"\blost \d+|\bdown \d+|\d+\s?(lbs?|pounds|kg|kilos)\b|\bdress size|in \d+ (days|weeks|months)",
     "R1 R2", "a weight-loss number: real, substantiated, and typical"),
    (r"fresh (tiktok )?account|new account|burner|warm[- ]?up|look(s)? (human|real|natural|american|authentic)|us[- ]based|united states based|\bvpn\b|\bsim\b|location|persona|niche account",
     "I1 I3", "account identity and location: the creator's own"),
    (r"buy (followers|likes|views)|engagement (pod|group)|bot|automat|view ?bot|follow ?train",
     "I2", "fake engagement"),
    (r"ozempic|wegovy|mounjaro|zepbound|semaglutide|tirzepatide|retatrutide|glp-?1|peptide|compounded|prescription|telehealth|\bdoctor\b|physician|\bdr\. ",
     "C1 R3", "a weight-loss drug or medical service: context only, never promoted, never where to get it"),
    (r"\bcure|guarantee|clinically|proven|doctor[- ]recommended|fast weight|lose weight fast|melt|burn (belly )?fat|appetite suppress|detox|miracle|no diet|without (diet|exercise)",
     "R2 C1 C2", "a health or weight claim: needs competent and reliable scientific evidence"),
    (r"results not typical|individual results (may )?vary|results may vary", "R1",
     "a 'results not typical' style disclaimer: doesn't cure an atypical testimonial"),
    (r"insecur|ugly|disgusting|hate my body|thinspo|skinny|starv|skip(ping)? meals|eat less than|\d+ ?cal(ories)? a day",
     "C2", "body image or risky eating"),
    (r"repost|re-?upload|duplicate|same (slides|video) on|mass[- ]post|spam", "P1", "original posts only"),
]
DISCLOSED = re.compile(r"#ad\b|\bad\b:|\bad\s*[|·-]|\bsponsored\b|\bpaid partnership\b|content disclosure|\badvertisement\b|#paidpartner", re.I)
PAID = re.compile(r"\bpaid\b|per 1,?000 views|per 1k|\bcpm\b|payout|\$\d|campaign|brand deal|whop|content rewards|clipping", re.I)


def lines(path):
    text = Path(path).read_text()
    if path.endswith(".json"):
        try:  # one line per string value, with its key path, so a hit points at the field
            out = []

            def walk(v, where):
                if isinstance(v, dict):
                    for k, x in v.items():
                        walk(x, f"{where}.{k}" if where else k)
                elif isinstance(v, list):
                    for i, x in enumerate(v):
                        walk(x, f"{where}[{i}]")
                elif isinstance(v, str):
                    out.append((where, v))
            walk(json.loads(text), "")
            return out
        except ValueError:
            pass
    return [(str(k), line) for k, line in enumerate(text.splitlines(), 1)]


def lint(path):
    found, everything = [], []
    for where, line in lines(path):
        everything.append(line)
        for pattern, rules, why in CHECKS:
            m = re.search(pattern, line, re.I)
            if m:
                found.append((where, rules, why, m.group(0), line.strip()))
    text = "\n".join(everything)
    missing = []
    if PAID.search(text) and not DISCLOSED.search(text):
        missing.append(("D1 D2", "it's paid, but nothing says so: turn on TikTok's content disclosure setting, and put "
                        "\"Ad\" on the first slide and at the start of the caption"))
    return found, missing


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    total = 0
    for path in sys.argv[1:]:
        found, missing = lint(path)
        print(f"== {path}: {len(found)} lines to rule on" + (f", {len(missing)} missing" if missing else ""))
        for where, rules, why, hit, line in found:
            print(f"  {where:>6}  [{rules}] {why}\n          \"{hit}\" in: {line[:160]}")
        for rules, why in missing:
            print(f"  MISSING [{rules}] {why}")
        total += len(found) + len(missing)
    print(f"\n{total} findings. Rule on each one in compliance.md (SKILL.md step 3); a lint hit is a question, not a verdict.")


if __name__ == "__main__":
    main()
