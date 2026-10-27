"""Look up foods in USDA FoodData Central (SR Legacy) and work out calories and macros per serving.

    python3 usda.py search "greek yogurt plain nonfat"          # matching foods with their fdc ids
    python3 usda.py show 170894                                  # per 100 g and per each USDA serving
    python3 usda.py show 170894 --grams 170                      # per a serving you name, in grams

The first run downloads USDA's SR Legacy CSV release (about 6 MB zipped) into data/usda/ (or ~/.cache/usda outside the
repo) and reuses it after that. Its API's DEMO_KEY rate-limits after a few calls, which is why this reads the files.
Numbers are rounded the way a label rounds: calories to whole numbers, grams to whole grams (one decimal under 1 g).
"""

import argparse
import csv
import io
import os
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ZIP_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"
NUTRIENTS = {"1008": "kcal", "1003": "protein", "1004": "fat", "1005": "carbs", "1079": "fiber", "2000": "sugars",
             "1093": "sodium_mg"}


def cache_dir():
    for d in [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]:
        if (d / "research_app").is_dir():
            return d / "data" / "usda"
    return Path(os.path.expanduser("~/.cache/usda"))


def table(name):
    folder = cache_dir()
    path = next(folder.glob(f"*/{name}.csv"), None) if folder.exists() else None
    if not path:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"downloading USDA SR Legacy to {folder} ...", file=sys.stderr)
        with urllib.request.urlopen(ZIP_URL, timeout=120) as resp:
            zipfile.ZipFile(io.BytesIO(resp.read())).extractall(folder)
        path = next(folder.glob(f"*/{name}.csv"))
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def search(args):
    words = [w for w in re.findall(r"[a-z0-9]+", args.query.lower())]
    hits = []
    for row in table("food"):
        desc = row["description"].lower()
        if all(w in desc for w in words):
            hits.append((len(desc), row["fdc_id"], row["description"]))
    for _, fdc, desc in sorted(hits)[: args.limit]:
        print(f"{fdc}  {desc}")
    if not hits:
        print("no match; try fewer or different words (USDA writes 'Yogurt, Greek, plain, nonfat')")


def label_round(name, value):
    if name in ("kcal", "sodium_mg"):
        return round(value)
    return round(value) if value >= 1 else round(value, 1)


def show(args):
    fdc = str(args.fdc_id)
    food = next((r for r in table("food") if r["fdc_id"] == fdc), None)
    if not food:
        raise SystemExit(f"No SR Legacy food with fdc id {fdc}")
    found = {NUTRIENTS[r["nutrient_id"]]: float(r["amount"]) for r in table("food_nutrient")
             if r["fdc_id"] == fdc and r["nutrient_id"] in NUTRIENTS}
    per100 = {name: found[name] for name in NUTRIENTS.values() if name in found}
    portions = [(f"{r['amount']} {r['modifier'] or r.get('portion_description') or ''}".strip(), float(r["gram_weight"]))
                for r in table("food_portion") if r["fdc_id"] == fdc and r["gram_weight"]]
    print(f"{fdc}  {food['description']}  (USDA FoodData Central, SR Legacy 2018)")
    print("per 100 g: " + ", ".join(f"{k} {v}" for k, v in per100.items()))
    servings = [(f"{args.grams} g (yours)", args.grams)] if args.grams else []
    for label, grams in servings + portions:
        vals = ", ".join(f"{k} {label_round(k, v * grams / 100)}" for k, v in per100.items())
        print(f"per {label} = {grams:g} g: {vals}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=15)
    p.set_defaults(fn=search)
    p = sub.add_parser("show")
    p.add_argument("fdc_id", type=int)
    p.add_argument("--grams", type=float)
    p.set_defaults(fn=show)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
