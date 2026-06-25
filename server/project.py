"""Project-folder operations: Try-template, scan a folder, Open-folder (switch ROOT)."""
import os, shutil
from . import context
from .envfile import parse_env


def apply_template():
    """Copy the bundled demo (assets/template + listing-template.json) into the
    editable "New" variant (assets/new + listing.json)."""
    tj = os.path.join(context.root(), "listing-template.json")
    if not os.path.exists(tj):
        return {"ok": False, "error": "no listing-template.json bundled"}
    src = os.path.join(context.root(), "assets", "template")
    dst = os.path.join(context.root(), "assets", "new")
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
    with open(os.path.join(context.root(), "listing.json"), "w", encoding="utf-8") as f:
        f.write(data)
    return {"ok": True, "copied": copied}


def _count_dir(p):
    return len([f for f in os.listdir(p)]) if os.path.isdir(p) else 0


def scan(path=None):
    """Auto-check a project folder: which env keys are filled, how many assets,
    which listing files exist. `path=None` scans the active ROOT."""
    p = os.path.abspath(os.path.expanduser(path or context.root()))
    # Merge the folder's .env with its .app_dist/.env.prod (same as Sync), so the
    # cred check reflects whether Sync would actually authenticate.
    env = parse_env(os.path.join(p, ".env"))
    dist = os.path.abspath(os.path.join(p, env.get("APP_DIST") or os.environ.get("APP_DIST", "../../.app_dist")))
    prod = parse_env(os.path.join(dist, ".env.prod"))
    env = {**env, **prod}
    asc_ok = bool(env.get("ASC_KEY_ID") and env.get("ASC_ISSUER_ID")
                  and (env.get("ASC_KEY_P8") or env.get("ASC_KEY_P8_B64")))
    play_ok = bool(env.get("PLAYSTORE_PACKAGE_NAME")
                   and (env.get("PLAYSTORE_SERVICE_ACCOUNT_JSON") or env.get("PLAYSTORE_SERVICE_ACCOUNT_JSON_B64")))
    a = os.path.join(p, "assets")
    return {
        "root": p,
        "exists": os.path.isdir(p),
        "hasEnv": bool(env),
        "envKeys": [k for k in env if k in context.SYNC_KEYS or k in context.FILE_B64.values()],
        "creds": {"appstore": asc_ok, "googleplay": play_ok},
        "assets": {"template": _count_dir(os.path.join(a, "template")),
                   "new": _count_dir(os.path.join(a, "new")),
                   "current": _count_dir(os.path.join(a, "current"))},
        "listings": {n: os.path.exists(os.path.join(p, n + ".json"))
                     for n in ("listing", "listing-current", "listing-template")},
    }


def open_folder(path):
    """Switch the active ROOT to `path` (so serving + listings + assets + .env +
    Sync all come from it), then return the scan report."""
    p = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(p):
        return {"ok": False, "error": f"not a folder: {p}"}
    if not (os.path.exists(os.path.join(p, "index.html")) or os.path.exists(os.path.join(p, "listing.json"))):
        return {"ok": False, "error": f"no store-preview project here (need index.html or listing.json): {p}"}
    context.set_root(p)
    return {"ok": True, **scan(p)}
