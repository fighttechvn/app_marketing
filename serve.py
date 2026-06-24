#!/usr/bin/env python3
"""Static server for the store-preview tool + a /api/sync endpoint.

/api/sync pulls the LIVE listing from App Store Connect (iPhone/iPad screenshots
+ metadata) and Google Play (phone screenshots + metadata) into assets/current/
and rewrites listing-current.json, so the "Current" tab reflects what is actually
on the stores right now.

Creds come from .app_dist/.env.prod (path via APP_DIST), same as the fastlane
lanes: ASC_KEY_ID / ASC_ISSUER_ID / ASC_KEY_P8, PLAYSTORE_SERVICE_ACCOUNT_JSON,
PLAYSTORE_PACKAGE_NAME, BUNDLE_ID.
"""
import os, sys, json, time, re, base64, shutil, http.server, urllib.request, urllib.error

# File-content env keys: exported base64 (single line) so the .env is self-contained
# (no need to copy the .p8 / service-account JSON separately). Decoded on use.
FILE_B64 = {"ASC_KEY_P8": "ASC_KEY_P8_B64",
            "PLAYSTORE_SERVICE_ACCOUNT_JSON": "PLAYSTORE_SERVICE_ACCOUNT_JSON_B64"}

def _asc_p8_text():
    b64 = os.environ.get("ASC_KEY_P8_B64")
    if b64: return base64.b64decode(b64).decode("utf-8")
    return open(os.environ["ASC_KEY_P8"], encoding="utf-8").read()

def _play_sa():
    """(info_dict, None) from base64, or (None, path) from a file."""
    b64 = os.environ.get("PLAYSTORE_SERVICE_ACCOUNT_JSON_B64")
    if b64: return json.loads(base64.b64decode(b64).decode("utf-8")), None
    return None, os.environ.get("PLAYSTORE_SERVICE_ACCOUNT_JSON")

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else "8092"))
CUR = os.path.join(HERE, "assets", "current")
LABELS = {1: "Discover hub", 2: "go2048", 3: "Zip", 4: "Patch", 5: "Sudoku"}

def num(s):
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else 99

# ---- credentials (.app_dist/.env.prod with ${APP_DIST} expansion) ----
def load_creds():
    local = _parse_env(os.path.join(HERE, ".env"))
    dist = os.path.abspath(os.path.join(HERE, local.get("APP_DIST") or os.environ.get("APP_DIST", "../../.app_dist")))
    os.environ["APP_DIST"] = dist
    # local .env first (imported creds, incl *_B64), then .app_dist/.env.prod overrides.
    for k, v in local.items():
        os.environ.setdefault(k, v)
    envp = os.path.join(dist, ".env.prod")
    if os.path.exists(envp):
        for line in open(envp, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = os.path.expandvars(v.strip().strip('"').strip("'"))
    return dist

# ---- App Store Connect ----
def asc_token():
    import jwt
    now = int(time.time())
    return jwt.encode({"iss": os.environ["ASC_ISSUER_ID"], "iat": now, "exp": now + 1100,
                       "aud": "appstoreconnect-v1"}, _asc_p8_text(),
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
                _download(url, os.path.join(CUR, fn))
                out[gal].append({"file": f"assets/current/{fn}", "label": LABELS.get(i, ""),
                                 "size": f"{w}×{h}"})
    return out

# ---- Google Play ----
def fetch_play():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    pkg = os.environ["PLAYSTORE_PACKAGE_NAME"]
    SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]
    info, path = _play_sa()
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
                _download(im["url"], os.path.join(CUR, fn))
                out["phone"].append({"file": f"assets/current/{fn}", "label": LABELS.get(i, ""), "size": "phone"})
    svc.edits().delete(packageName=pkg, editId=eid).execute()
    return out

def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "store-preview-sync"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())

def sync():
    load_creds()
    os.makedirs(CUR, exist_ok=True)
    # clear old current gallery images
    for f in os.listdir(CUR):
        if re.match(r"(iphone|ipad|phone)-\d+\.png$", f):
            os.remove(os.path.join(CUR, f))
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
    with open(os.path.join(HERE, "listing-current.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"ok": True, "appstore": {"iphone": len(a["iphone"]), "ipad": len(a["ipad"])},
            "googleplay": {"phone": len(p["phone"])}, "locales": locs, "versionName": a.get("versionName", "")}

def _parse_env(path):
    return _parse_env_text(open(path, encoding="utf-8").read()) if os.path.exists(path) else {}

def _parse_env_text(text):
    d = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip()] = v.strip().strip('"').strip("'")
    return d

# ---- credential verification (test an imported .env WITHOUT saving it) ----
def _asc_p8_from(env):
    b64 = env.get("ASC_KEY_P8_B64")
    if b64: return base64.b64decode(b64).decode("utf-8")
    p = os.path.expandvars(env.get("ASC_KEY_P8") or "")
    if p and os.path.exists(p): return open(p, encoding="utf-8").read()
    raise ValueError("missing ASC_KEY_P8_B64 / ASC_KEY_P8")

def test_appstore(env):
    for k in ("ASC_KEY_ID", "ASC_ISSUER_ID"):
        if not env.get(k): return {"ok": False, "detail": f"missing {k}"}
    if not (env.get("ASC_KEY_P8_B64") or env.get("ASC_KEY_P8")):
        return {"ok": False, "detail": "missing ASC_KEY_P8_B64 / ASC_KEY_P8"}
    try:
        import jwt
        now = int(time.time())
        tok = jwt.encode({"iss": env["ASC_ISSUER_ID"], "iat": now, "exp": now + 1100,
                          "aud": "appstoreconnect-v1"}, _asc_p8_from(env),
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
    env = _parse_env_text(text)
    asc = test_appstore(env)
    play = test_play(env)
    return {"ok": bool(asc["ok"] or play["ok"]), "appstore": asc, "googleplay": play}

# ---- Try template: copy the bundled demo (assets/template + listing-template.json)
# into the editable "New" variant (assets/new + listing.json) ----
def apply_template():
    tj = os.path.join(HERE, "listing-template.json")
    if not os.path.exists(tj):
        return {"ok": False, "error": "no listing-template.json bundled"}
    src = os.path.join(HERE, "assets", "template")
    dst = os.path.join(HERE, "assets", "new")
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(dst):                       # clear any existing New screenshots
        p = os.path.join(dst, f)
        if os.path.isfile(p): os.remove(p)
    copied = 0
    if os.path.isdir(src):
        for f in os.listdir(src):
            sp = os.path.join(src, f)
            if os.path.isfile(sp):
                shutil.copy2(sp, os.path.join(dst, f)); copied += 1
    # listing.json points at assets/new (template content rebased from assets/template)
    data = open(tj, encoding="utf-8").read().replace("assets/template/", "assets/new/")
    with open(os.path.join(HERE, "listing.json"), "w", encoding="utf-8") as f:
        f.write(data)
    return {"ok": True, "copied": copied}

# Only the keys the Sync flow needs to call App Store Connect + Google Play to
# load screenshots + metadata text. Signing/keystore/Firebase secrets are NEVER
# exported (kept server-side).
SYNC_KEYS = ["PORT",
             "ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_KEY_P8", "BUNDLE_ID",
             "PLAYSTORE_PACKAGE_NAME", "PLAYSTORE_SERVICE_ACCOUNT_JSON"]

def env_dump():
    """RAW values for ONLY the ASC/Play API keys the Sync button needs, so the
    Export ▸ Env tab can write a minimal self-contained .env. File-content keys
    (.p8, service-account JSON) are emitted base64 on a single line. Localhost only."""
    local = _parse_env(os.path.join(HERE, ".env"))
    dist = os.path.abspath(os.path.join(HERE, local.get("APP_DIST") or os.environ.get("APP_DIST", "../../.app_dist")))
    os.environ["APP_DIST"] = dist
    prod = _parse_env(os.path.join(dist, ".env.prod"))
    merged = {}
    for k in SYNC_KEYS:
        if k in prod:    v = os.path.expandvars(prod[k])   # .env.prod wins; expand ${APP_DIST}
        elif k in local: v = local[k]
        else: continue
        if k in FILE_B64:                                  # value is a path → embed base64 of the file
            if os.path.exists(v):
                merged[FILE_B64[k]] = base64.b64encode(open(v, "rb").read()).decode("ascii")
            elif local.get(FILE_B64[k]):                   # already a *_B64 in the imported .env
                merged[FILE_B64[k]] = local[FILE_B64[k]]
        else:
            merged[k] = v
    # carry through any *_B64 already present (imported env without path keys)
    for fk in FILE_B64.values():
        if fk not in merged and local.get(fk):
            merged[fk] = local[fk]
    return {"ok": True, "env": merged, "appDist": dist,
            "hasProd": os.path.exists(os.path.join(dist, ".env.prod"))}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kw):
        super().__init__(*args, directory=HERE, **kw)
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        route = self.path.split("?")[0]
        if route == "/api/sync":
            try: self._json(200, sync())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/env":
            try: self._json(200, env_dump())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        return super().do_GET()
    def do_POST(self):
        route = self.path.split("?")[0]
        if route == "/api/apply-template":
            try: self._json(200, apply_template())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/test":
            # Verify the credentials in the posted .env text WITHOUT saving them —
            # auth against App Store Connect + Google Play and report per-store.
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(n).decode("utf-8")
                self._json(200, test_creds(body))
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/env":
            # Save an imported .env to local — first-time only (won't clobber an
            # existing .env unless ?force=1). Localhost only.
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(n).decode("utf-8")
                force = "force=1" in (self.path.split("?", 1)[1] if "?" in self.path else "")
                dest = os.path.join(HERE, ".env")
                existed = os.path.exists(dest)
                if existed and not force:
                    self._json(200, {"ok": True, "saved": False, "existed": True, "path": dest})
                else:
                    with open(dest, "w", encoding="utf-8") as f: f.write(body)
                    self._json(200, {"ok": True, "saved": True, "existed": existed, "path": dest})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return
        self.send_response(404); self.end_headers()
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

if __name__ == "__main__":
    # Bind localhost only — /api/env and /api/sync expose store credentials,
    # so never serve them on 0.0.0.0 / the LAN.
    print(f"→ store-preview server (/api/sync, /api/env) on http://localhost:{PORT}/")
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
