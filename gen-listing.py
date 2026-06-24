#!/usr/bin/env python3
"""Generate listing.json (new) + listing-current.json (live) for the store-preview
tool, reading real metadata from ../../../.app_dist/fastlane.

  new     -> assets/new/*      (fresh develop-build screenshots, pending upload)
  current -> assets/current/*  (screenshots committed in .app_dist = live now)

Only the screenshots differ between the two variants; the listing copy + version
(1.1.2 build 20) are identical, since this release is a screenshot refresh.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
# repo root is two levels up: .app_marketing/store-preview -> repo root
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
# APP_DIST may be set in .env (relative to this folder); fall back to repo root.
_dist = os.environ.get("APP_DIST", "").strip()
APP_DIST = os.path.abspath(os.path.join(HERE, _dist)) if _dist else os.path.join(ROOT, ".app_dist")
FL = os.path.join(APP_DIST, "fastlane")

def env(key, default=""):
    return os.environ.get(key, default).strip() or default

def rd(*p):
    fp = os.path.join(FL, *p)
    with open(fp, encoding="utf-8") as f:
        return f.read().strip()

LOCALES = [x.strip() for x in env("LOCALES", "en-US,vi").split(",") if x.strip()]
DISPLAY = {"en-US": "English (US)", "vi": "Tiếng Việt", "ko": "한국어", "zh": "中文", "ja": "日本語", "ar": "العربية"}

def locale_block(loc):
    return {
        "displayName": DISPLAY[loc],
        "appstore": {
            "name": rd("ios", "metadata", loc, "name.txt"),
            "subtitle": rd("ios", "metadata", loc, "subtitle.txt"),
            "keywords": rd("ios", "metadata", loc, "keywords.txt"),
            "promotionalText": rd("ios", "metadata", loc, "promotional_text.txt"),
        },
        "googleplay": {
            "title": rd("android", "metadata", "android", loc, "title.txt"),
            "shortDescription": rd("android", "metadata", "android", loc, "short_description.txt"),
        },
        # iOS description + Android full_description are identical here; use the iOS one.
        "fullDescription": rd("ios", "metadata", loc, "description.txt"),
        "whatsNew": rd("ios", "metadata", loc, "release_notes.txt"),
    }

LABELS = ["Discover hub", "go2048", "Zip", "Patch", "Sudoku"]

def screenshots(variant):
    base = f"assets/{variant}"
    # gallery -> (filename prefix, store display size). Only include shots whose
    # asset file actually exists, so a variant with fewer screens still renders.
    galleries = {
        "iphone": ("iphone", "1320×2868"),
        "ipad":   ("ipad",   "2064×2752"),
        "phone":  ("phone",  "1344×2688"),
    }
    out = {"iphone": [], "ipad": [], "phone": [], "tablet": []}
    for key, (prefix, size) in galleries.items():
        for i in range(len(LABELS)):
            rel = f"{base}/{prefix}-0{i+1}.png"
            if os.path.exists(os.path.join(HERE, rel)):
                out[key].append({"file": rel, "label": LABELS[i], "size": size})
    return out

def build(variant):
    return {
        "app": {
            "name": env("APP_NAME", "GoBrain: Puzzles Brain Games"),
            "androidPackage": env("ANDROID_PACKAGE", "vn.fighttech.go2048"),
            "iosBundleId": env("IOS_BUNDLE_ID", "vn.fighttech.go2048"),
            "versionName": env("VERSION_NAME", "1.1.2"),
            "versionCode": int(env("VERSION_CODE", "28")),
            "icon": "assets/icon.png",
            "developer": env("DEVELOPER", "FightTech"),
            "rating": "",
            "downloads": "",
            "age": env("AGE", "4+"),
            "ageShort": env("AGE", "4+"),
            "contentAdvisory": env("CONTENT_ADVISORY", "No ads · No tracking"),
            "defaultLocale": env("DEFAULT_LOCALE", "en-US"),
            "locales": LOCALES,
            "playCategory": env("PLAY_CATEGORY", "Puzzle"),
            "appStoreCategory": env("APPSTORE_CATEGORY", "Games"),
            "appStoreSecondaryCategory": env("APPSTORE_SECONDARY_CATEGORY", "Puzzle"),
            "contentRating": env("CONTENT_RATING", "Everyone / 4+"),
            "marketingUrl": env("MARKETING_URL", "https://fighttechvn.github.io/play2048/"),
            "supportUrl": env("SUPPORT_URL", "https://fighttechvn.github.io/play2048/support/"),
            "_variant": "NEW — pending upload (fresh develop screenshots)" if variant == "new"
                         else "CURRENT — live on store now",
        },
        "limits": {
            "appstore": {"name": 30, "subtitle": 30, "keywords": 100,
                          "promotionalText": 170, "description": 4000, "whatsNew": 4000},
            "googleplay": {"title": 30, "shortDescription": 80,
                            "fullDescription": 4000, "changelog": 500},
        },
        "locales": {loc: locale_block(loc) for loc in LOCALES},
        "screenshots": screenshots(variant),
        "graphics": {
            "appIcon": {"status": "uploaded", "spec": "Play 512×512 · App Store 1024×1024 (no alpha)",
                         "file": "assets/icon.png", "size": "512×512"},
            "featureGraphic": {"status": "uploaded", "spec": "Play 1024×500 PNG/JPG",
                                "file": "assets/feature-graphic.png", "size": "1024×500"},
        },
    }

for variant, fname in (("new", "listing.json"), ("current", "listing-current.json")):
    with open(os.path.join(HERE, fname), "w", encoding="utf-8") as f:
        json.dump(build(variant), f, ensure_ascii=False, indent=2)
    print("wrote", fname)
