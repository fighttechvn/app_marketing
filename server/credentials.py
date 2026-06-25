"""Store-API credential loading + key decoding.

Creds come from the project .env plus .app_dist/.env.prod (path via APP_DIST),
same as the fastlane lanes: ASC_KEY_ID / ASC_ISSUER_ID / ASC_KEY_P8,
PLAYSTORE_SERVICE_ACCOUNT_JSON, PLAYSTORE_PACKAGE_NAME, BUNDLE_ID.
"""
import os, json, base64
from . import context
from .envfile import parse_env


def asc_p8_text():
    """The App Store Connect .p8 private key from the live environment."""
    b64 = os.environ.get("ASC_KEY_P8_B64")
    if b64:
        return base64.b64decode(b64).decode("utf-8")
    return open(os.environ["ASC_KEY_P8"], encoding="utf-8").read()


def asc_p8_from(env):
    """Same, but from a parsed env dict (used to test imported creds un-saved)."""
    b64 = env.get("ASC_KEY_P8_B64")
    if b64:
        return base64.b64decode(b64).decode("utf-8")
    p = os.path.expandvars(env.get("ASC_KEY_P8") or "")
    if p and os.path.exists(p):
        return open(p, encoding="utf-8").read()
    raise ValueError("missing ASC_KEY_P8_B64 / ASC_KEY_P8")


def play_sa():
    """Google Play service account: (info_dict, None) from base64, or (None, path)."""
    b64 = os.environ.get("PLAYSTORE_SERVICE_ACCOUNT_JSON_B64")
    if b64:
        return json.loads(base64.b64decode(b64).decode("utf-8")), None
    return None, os.environ.get("PLAYSTORE_SERVICE_ACCOUNT_JSON")


def load_creds():
    """Populate os.environ from the active project's .env + .app_dist/.env.prod
    (with ${APP_DIST} expansion). Returns the resolved APP_DIST path."""
    local = parse_env(os.path.join(context.root(), ".env"))
    dist = os.path.abspath(os.path.join(context.root(), local.get("APP_DIST") or os.environ.get("APP_DIST", "../../.app_dist")))
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
