# campaign.json

The campaign's rules, one place, each with the words it came from. `campaign.py new <slug>` makes a skeleton and
`campaign.py check <folder>` checks it.

```json
{
 "name": "DreamMe — TikTok Slideshow Campaign",
 "brand": {"name": "DreamMe", "what": "GLP-1 tracker app with a pet fish that grows as you log",
           "store": "https://apps.apple.com/us/app/id6755569693", "maker": "Everr AI LLC"},
 "organizer": {"name": "Reachify", "platform": "Content Rewards", "url": "https://contentrewards.com/c/campaigns/…"},
 "platform": "tiktok",
 "format": "photo slideshow (native)",
 "slides": [5, 10],
 "language": "English",
 "audience": {"tier1_min": 0.4, "countries": ["US", "UK", "CA", "AU"]},
 "pay": {"per_1k": 1.0, "min_payout": 1, "max_per_post": 400, "budget": 4000, "min_views": 1000,
         "currency": "USD", "budget_left": null},
 "submit": {"within_minutes": 30, "proof": ["analytics screenshot showing 40%+ Tier-1"], "payouts": "Whop"},
 "rules": [
  {"id": "C5", "kind": "content", "text": "Show realistic transformation / struggle (not perfection)",
   "source": "campaign.txt line 17", "status": "stated", "note": ""}
 ],
 "locked": ["Creator Onboarding Guide", "Content Vault"],
 "open_questions": ["Is the analytics screenshot due at submission (30 minutes in) or at payout?"]
}
```

| Field | What goes in it |
| --- | --- |
| `brand` | What the product is and does, from its own store page or site (`app-store.py fetch` for an app), not from the campaign's pitch |
| `organizer` | Who runs the campaign (often an agency) and where creators join |
| `slides` | `[min, max]` slides per post |
| `audience` | The share of views that must come from the listed countries |
| `pay` | `per_1k` per 1,000 views; `min_payout`; `max_per_post` (the cap); `budget` for the whole campaign; `min_views` to qualify; `budget_left` when the campaign page shows it |
| `submit` | How soon after posting to submit (`within_minutes`), the `proof` asked for, and where `payouts` are made |
| `rules` | **Every** line of the campaign that asks creators to do something, in its own words. `kind`: platform, format, audience, language, content, account, tools, quality, pay or submit. `source`: the file and line, or the page. `status`: `stated`, `unclear` (ambiguous: add an open question) or `conflict` (two sources disagree: say which in `note`) |
| `locked` | Pages behind the campaign's login that couldn't be read: the person pastes them once they've joined |
| `open_questions` | What to ask the brand before creators start |

Keep the campaign's own words in `text`, including rules that may not be allowed. The brief doesn't turn those into
steps; the compliance check (tiktok-ftc-check) rules on them.
