#!/usr/bin/env python3
"""build-new.py — build listing.json for the **New** variant from screenshots you
dropped into assets/new/.

Place store screenshots in assets/new/ named:
    iphone-01.png … iphone-05.png   (App Store iPhone 6.9", 1320×2868)
    ipad-01.png   … ipad-05.png     (App Store iPad 13",  2064×2752)
    phone-01.png  … phone-05.png    (Google Play phone,   1344×2688)
    tablet-01.png … (optional)
then run:  python3 scripts/build-new.py
The New variant will show them at http://localhost:8092/playground/ (reload).
"""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NEW = os.path.join(ROOT, "assets", "new")
GAL = {"iphone": "1320×2868", "ipad": "2064×2752", "phone": "1344×2688", "tablet": "2048×2732"}
LABELS = ["Discover", "Play", "Zip", "Patch", "Sudoku"]


def scaffold():
    """App/locale/graphics text from a populated listing — template or current."""
    for f in ("listing-template.json", "listing.json"):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            d = json.load(open(p, encoding="utf-8"))
            if not d.get("_empty"):
                return d
    return {"app": {"name": "My App", "locales": ["en-US"]},
            "limits": {"appstore": {"name": 30, "subtitle": 30, "keywords": 100, "description": 4000},
                        "googleplay": {"title": 30, "shortDescription": 80, "fullDescription": 4000}},
            "locales": {"en-US": {"displayName": "English (US)", "appstore": {}, "googleplay": {}}},
            "graphics": {"appIcon": {"file": "assets/app-icon.svg", "spec": "1024×1024"},
                          "featureGraphic": {"file": "assets/feature-graphic.svg", "spec": "1024×500"}}}


def scan():
    out = {"iphone": [], "ipad": [], "phone": [], "tablet": []}
    if os.path.isdir(NEW):
        files = sorted(os.listdir(NEW))
        for key, size in GAL.items():
            for f in files:
                if re.match(rf"{key}-(\d+)\.(png|jpe?g|webp|svg)$", f, re.I):
                    i = int(re.search(r"-(\d+)\.", f).group(1))
                    out[key].append({"file": f"assets/new/{f}",
                                     "label": LABELS[i - 1] if 0 < i <= len(LABELS) else "",
                                     "size": size})
    return out


def main():
    d = scaffold()
    d["screenshots"] = scan()
    for k in ("_empty", "_note", "_demo"):
        d.pop(k, None)
    if isinstance(d.get("app"), dict):
        d["app"].pop("_empty", None)
        d["app"].pop("_variant", None)
    with open(os.path.join(ROOT, "listing.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    n = sum(len(v) for v in d["screenshots"].values())
    if not n:
        print("⚠️  no screenshots found in assets/new/ — add iphone-0N.png / ipad-0N.png / phone-0N.png first")
    else:
        print("✓ listing.json built from assets/new/ — " +
              ", ".join(f"{k} {len(v)}" for k, v in d["screenshots"].items() if v))
    print("  open http://localhost:8092/playground/ (New variant) to preview")


if __name__ == "__main__":
    main()
