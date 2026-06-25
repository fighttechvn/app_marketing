"""App Store Connect + Google Play.

/api/sync pulls the LIVE listing (iPhone/iPad/phone screenshots + metadata) into
assets/current/ and rewrites listing-current.json, so the "Current" tab reflects
what is actually on the stores right now. /api/test verifies imported creds, and
env_dump() exports the minimal key set the Sync flow needs.
"""
import os, json, time, re, base64, urllib.request, urllib.error
from . import context
from .envfile import parse_env, parse_env_text
from .util import download, num
from .credentials import asc_p8_text, asc_p8_from, play_sa, load_creds

LABELS = {1: "Discover hub", 2: "go2048", 3: "Zip", 4: "Patch", 5: "Sudoku"}


# ---- App Store Connect ----
def asc_token():
    import jwt
    now = int(time.time())
    return jwt.encode({"iss": os.environ["ASC_ISSUER_ID"], "iat": now, "exp": now + 1100,
                       "aud": "appstoreconnect-v1"}, asc_p8_text(),
                      algorithm="ES256", headers={"kid": os.environ["ASC_KEY_ID"], "typ": "JWT"})


def asc_get(tok, path):
    r = urllib.request.Request("https://api.appstoreconnect.apple.com" + path,
                               headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(r, timeout=40) as resp:
        return json.load(resp)


def fetch_appstore():
    tok = asc_token()
    bundle = os.environ.get("BUNDLE_ID", "vn.fighttech.go2048")
    app = asc_get(tok, f"/v1/apps?filter[bundleId]={bundle}")["data"][0]
    aid = app["id"]
    ver = asc_get(tok, f"/v1/apps/{aid}/appStoreVersions?limit=1")["data"][0]
    vid, vstr = ver["id"], ver["attributes"]["versionString"]
    # app info localizations (name / subtitle)
    ai = asc_get(tok, f"/v1/apps/{aid}/appInfos?include=appInfoLocalizations&limit=1")
    names = {x["attributes"]["locale"]: x["attributes"] for x in ai.get("included", []) if x["type"] == "appInfoLocalizations"}
    out = {"versionName": vstr, "locales": {}, "iphone": [], "ipad": []}
    locs = asc_get(tok, f"/v1/appStoreVersions/{vid}/appStoreVersionLocalizations?limit=50")["data"]
    DISPLAY = {"APP_IPHONE_67": "iphone", "APP_IPAD_PRO_3GEN_129": "ipad"}
    for L in locs:
        a = L["attributes"]; loc = a["locale"]
        nm = names.get(loc, {})
        out["locales"][loc] = {
            "name": nm.get("name", ""), "subtitle": nm.get("subtitle", ""),
            "keywords": a.get("keywords", ""), "promotionalText": a.get("promotionalText", ""),
            "description": a.get("description", ""), "whatsNew": a.get("whatsNew", ""),
        }
        # screenshots only from the default locale (galleries are single-set)
        if loc != "en-US":
            continue
        sets = asc_get(tok, f"/v1/appStoreVersionLocalizations/{L['id']}/appScreenshotSets?limit=20")["data"]
        for s in sets:
            gal = DISPLAY.get(s["attributes"]["screenshotDisplayType"])
            if not gal:
                continue
            shots = asc_get(tok, f"/v1/appScreenshotSets/{s['id']}/appScreenshots?limit=30")["data"]
            shots = [x for x in shots if x["attributes"].get("imageAsset")]
            shots.sort(key=lambda x: num(x["attributes"].get("fileName")))
            for i, sh in enumerate(shots, 1):
                asset = sh["attributes"]["imageAsset"]
                w = asset["width"]; h = asset["height"]
                scale = 520.0 / w
                url = asset["templateUrl"].replace("{w}", str(int(w*scale))).replace("{h}", str(int(h*scale))).replace("{f}", "png")
                fn = f"{gal}-0{i}.png"
                download(url, os.path.join(context.cur(), fn))
                out[gal].append({"file": f"assets/current/{fn}", "label": LABELS.get(i, ""),
                                 "size": f"{w}×{h}"})
    return out


# ---- Google Play ----
def fetch_play():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    pkg = os.environ["PLAYSTORE_PACKAGE_NAME"]
    SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]
    info, path = play_sa()
    creds = (service_account.Credentials.from_service_account_info(info, scopes=SCOPES) if info
             else service_account.Credentials.from_service_account_file(path, scopes=SCOPES))
    svc = build("androidpublisher", "v3", credentials=creds, cache_discovery=False)
    eid = svc.edits().insert(packageName=pkg, body={}).execute()["id"]
    out = {"locales": {}, "phone": []}
    langs = [l["language"] for l in svc.edits().listings().list(packageName=pkg, editId=eid).execute().get("listings", [])]
    for lang in langs:
        L = svc.edits().listings().get(packageName=pkg, editId=eid, language=lang).execute()
        out["locales"][lang] = {"title": L.get("title", ""), "shortDescription": L.get("shortDescription", ""),
                                 "fullDescription": L.get("fullDescription", "")}
        if lang == "en-US":
            imgs = svc.edits().images().list(packageName=pkg, editId=eid, language=lang, imageType="phoneScreenshots").execute().get("images", [])
            for i, im in enumerate(imgs, 1):
                fn = f"phone-0{i}.png"
                download(im["url"], os.path.join(context.cur(), fn))
                out["phone"].append({"file": f"assets/current/{fn}", "label": LABELS.get(i, ""), "size": "phone"})
    svc.edits().delete(packageName=pkg, editId=eid).execute()
    return out


def sync():
    load_creds()
    os.makedirs(context.cur(), exist_ok=True)
    # clear old current gallery images
    for f in os.listdir(context.cur()):
        if re.match(r"(iphone|ipad|phone)-\d+\.png$", f):
            os.remove(os.path.join(context.cur(), f))
    a = fetch_appstore()
    p = fetch_play()
    LOC_DISPLAY = {"en-US": "English (US)", "vi": "Tiếng Việt", "ko": "한국어", "zh": "中文", "ja": "日本語", "ar": "العربية"}
    locs = sorted(set(list(a["locales"]) + list(p["locales"])), key=lambda x: (x != "en-US", x))
    locales = {}
    for loc in locs:
        av = a["locales"].get(loc, {}); pv = p["locales"].get(loc, {})
        locales[loc] = {
            "displayName": LOC_DISPLAY.get(loc, loc),
            "appstore": {"name": av.get("name", ""), "subtitle": av.get("subtitle", ""),
                          "keywords": av.get("keywords", ""), "promotionalText": av.get("promotionalText", "")},
            "googleplay": {"title": pv.get("title", ""), "shortDescription": pv.get("shortDescription", "")},
            "fullDescription": pv.get("fullDescription") or av.get("description", ""),
            "whatsNew": av.get("whatsNew", ""),
        }
    enUS = locales.get("en-US", {})
    data = {
        "app": {
            "name": enUS.get("appstore", {}).get("name") or enUS.get("googleplay", {}).get("title") or "GoBrain",
            "androidPackage": os.environ.get("PLAYSTORE_PACKAGE_NAME", "vn.fighttech.go2048"),
            "iosBundleId": os.environ.get("BUNDLE_ID", "vn.fighttech.go2048"),
            "versionName": a.get("versionName", ""), "versionCode": 0,
            "icon": "assets/icon.png", "developer": "FightTech",
            "rating": "", "downloads": "", "age": "4+", "ageShort": "4+",
            "contentAdvisory": "No ads · No tracking", "defaultLocale": "en-US",
            "locales": locs, "playCategory": "Puzzle", "appStoreCategory": "Games",
            "appStoreSecondaryCategory": "Puzzle", "contentRating": "Everyone / 4+",
            "marketingUrl": "https://fighttechvn.github.io/play2048/",
            "supportUrl": "https://fighttechvn.github.io/play2048/support/",
            "_variant": "CURRENT — live on store (synced via API)",
        },
        "limits": {"appstore": {"name": 30, "subtitle": 30, "keywords": 100, "promotionalText": 170, "description": 4000, "whatsNew": 4000},
                    "googleplay": {"title": 30, "shortDescription": 80, "fullDescription": 4000, "changelog": 500}},
        "locales": locales,
        "screenshots": {"iphone": a["iphone"], "ipad": a["ipad"], "phone": p["phone"], "tablet": []},
        "graphics": {"appIcon": {"status": "uploaded", "spec": "Play 512×512 · App Store 1024×1024", "file": "assets/icon.png", "size": "512×512"},
                      "featureGraphic": {"status": "uploaded", "spec": "Play 1024×500", "file": "assets/feature-graphic.png", "size": "1024×500"}},
    }
    with open(os.path.join(context.root(), "listing-current.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"ok": True, "appstore": {"iphone": len(a["iphone"]), "ipad": len(a["ipad"])},
            "googleplay": {"phone": len(p["phone"])}, "locales": locs, "versionName": a.get("versionName", "")}


# ---- credential verification (test an imported .env WITHOUT saving it) ----
def test_appstore(env):
    for k in ("ASC_KEY_ID", "ASC_ISSUER_ID"):
        if not env.get(k): return {"ok": False, "detail": f"missing {k}"}
    if not (env.get("ASC_KEY_P8_B64") or env.get("ASC_KEY_P8")):
        return {"ok": False, "detail": "missing ASC_KEY_P8_B64 / ASC_KEY_P8"}
    try:
        import jwt
        now = int(time.time())
        tok = jwt.encode({"iss": env["ASC_ISSUER_ID"], "iat": now, "exp": now + 1100,
                          "aud": "appstoreconnect-v1"}, asc_p8_from(env),
                         algorithm="ES256", headers={"kid": env["ASC_KEY_ID"], "typ": "JWT"})
        bundle = env.get("BUNDLE_ID", "vn.fighttech.go2048")
        data = asc_get(tok, f"/v1/apps?filter[bundleId]={bundle}&limit=1")
        apps = data.get("data", [])
        if not apps:
            return {"ok": True, "detail": f"Auth OK — but no app found for bundle {bundle}"}
        return {"ok": True, "detail": f"OK — {apps[0]['attributes'].get('name','?')} ({bundle})"}
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:200] if hasattr(e, "read") else str(e)
        return {"ok": False, "detail": f"HTTP {e.code} — {msg}"}
    except Exception as e:
        return {"ok": False, "detail": f"{type(e).__name__}: {str(e)[:200]}"}


def test_play(env):
    pkg = env.get("PLAYSTORE_PACKAGE_NAME")
    if not pkg: return {"ok": False, "detail": "missing PLAYSTORE_PACKAGE_NAME"}
    b64 = env.get("PLAYSTORE_SERVICE_ACCOUNT_JSON_B64")
    path = os.path.expandvars(env.get("PLAYSTORE_SERVICE_ACCOUNT_JSON") or "")
    if not (b64 or path):
        return {"ok": False, "detail": "missing PLAYSTORE_SERVICE_ACCOUNT_JSON(_B64)"}
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]
        if b64:
            info = json.loads(base64.b64decode(b64).decode("utf-8"))
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            sa = info.get("client_email", "?")
        else:
            creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
            sa = json.load(open(path)).get("client_email", "?")
        svc = build("androidpublisher", "v3", credentials=creds, cache_discovery=False)
        eid = svc.edits().insert(packageName=pkg, body={}).execute()["id"]   # verifies app access
        svc.edits().delete(packageName=pkg, editId=eid).execute()
        return {"ok": True, "detail": f"OK — edit access to {pkg} (SA {sa})"}
    except Exception as e:
        return {"ok": False, "detail": f"{type(e).__name__}: {str(e)[:200]}"}


def test_creds(text):
    env = parse_env_text(text)
    asc = test_appstore(env)
    play = test_play(env)
    return {"ok": bool(asc["ok"] or play["ok"]), "appstore": asc, "googleplay": play}


def env_dump():
    """RAW values for ONLY the ASC/Play API keys the Sync button needs, so the
    Export ▸ Env tab can write a minimal self-contained .env. File-content keys
    (.p8, service-account JSON) are emitted base64 on a single line. Localhost only."""
    local = parse_env(os.path.join(context.root(), ".env"))
    dist = os.path.abspath(os.path.join(context.root(), local.get("APP_DIST") or os.environ.get("APP_DIST", "../../.app_dist")))
    os.environ["APP_DIST"] = dist
    prod = parse_env(os.path.join(dist, ".env.prod"))
    merged = {}
    for k in context.SYNC_KEYS:
        if k in prod:    v = os.path.expandvars(prod[k])   # .env.prod wins; expand ${APP_DIST}
        elif k in local: v = local[k]
        else: continue
        if k in context.FILE_B64:                          # value is a path → embed base64 of the file
            if os.path.exists(v):
                merged[context.FILE_B64[k]] = base64.b64encode(open(v, "rb").read()).decode("ascii")
            elif local.get(context.FILE_B64[k]):           # already a *_B64 in the imported .env
                merged[context.FILE_B64[k]] = local[context.FILE_B64[k]]
        else:
            merged[k] = v
    # carry through any *_B64 already present (imported env without path keys)
    for fk in context.FILE_B64.values():
        if fk not in merged and local.get(fk):
            merged[fk] = local[fk]
    return {"ok": True, "env": merged, "appDist": dist,
            "hasProd": os.path.exists(os.path.join(dist, ".env.prod"))}
