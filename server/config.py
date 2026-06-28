"""Read/write the app's local config file ``~/.apppreview`` (YAML).

This is the single on-disk store the app's features CRUD against — the runner
list, the active runner, and app settings (e.g. the release checklist). It
replaces the old browser-localStorage store so the data survives reloads and is
shared across browsers/the desktop app.

The same file may ALSO carry hand-authored build/release notes (machines,
signing, release, gotchas) with comments. We round-trip with ruamel.yaml when
available so those sections AND their comments survive an app write; only the
app-managed keys are ever touched: ``runners``, ``active_runner``, ``settings``.

Secrets (runner passwords / private keys) are stored in plaintext here, exactly
as the previous localStorage store did. The file is created mode 0600.
"""
import os, threading
from . import context

# Default to ~/.apppreview; override for tests via APPPREVIEW_CONFIG.
CONFIG_PATH = os.environ.get("APPPREVIEW_CONFIG") or \
    os.path.join(os.path.expanduser("~"), ".apppreview")

_LOCK = threading.RLock()

# App-managed keys (everything else in the file is left untouched).
_K_RUNNERS = "runners"
_K_ACTIVE = "active_runner"
_K_SETTINGS = "settings"

# Prefer ruamel (round-trip: keeps comments + key order); fall back to PyYAML.
try:
    from ruamel.yaml import YAML
    _yaml = YAML()
    _yaml.preserve_quotes = True
    _yaml.width = 4096                       # don't wrap long values (signatures, paths)
    _RUAMEL = True
except Exception:                            # pragma: no cover
    _RUAMEL = False
    try:
        import yaml as _pyyaml
    except Exception:
        _pyyaml = None


def _new_doc():
    if _RUAMEL:
        from ruamel.yaml.comments import CommentedMap
        return CommentedMap()
    return {}


def _load_doc():
    """Load the whole config document (or an empty one if absent/unreadable)."""
    if not os.path.exists(CONFIG_PATH):
        return _new_doc()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            if _RUAMEL:
                d = _yaml.load(fh)
                return d if d is not None else _new_doc()
            if _pyyaml:
                d = _pyyaml.safe_load(fh)
                return d if isinstance(d, dict) else _new_doc()
    except Exception:
        # A malformed/foreign file shouldn't crash the app — start fresh in memory.
        return _new_doc()
    return _new_doc()


def _dump_doc(doc):
    """Write the document back, 0600, atomically (temp file + replace)."""
    d = os.path.dirname(CONFIG_PATH) or "."
    os.makedirs(d, exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            if _RUAMEL:
                _yaml.dump(doc, fh)
            elif _pyyaml:
                _pyyaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)
            else:
                raise RuntimeError("no YAML library available to write config")
        os.replace(tmp, CONFIG_PATH)
        try: os.chmod(CONFIG_PATH, 0o600)
        except Exception: pass
    finally:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except Exception: pass


def _plain(v):
    """Convert ruamel containers to plain dict/list/str for JSON serialisation."""
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    return v


# ── public API ───────────────────────────────────────────────────────────────

def get_state():
    """Return the app-managed slice as plain JSON-able data."""
    with _LOCK:
        doc = _load_doc()
        runners = _plain(doc.get(_K_RUNNERS) or [])
        active = doc.get(_K_ACTIVE) or ""
        settings = _plain(doc.get(_K_SETTINGS) or {})
    if not isinstance(runners, list):
        runners = []
    return {"runners": runners, "activeId": str(active or ""),
            "settings": settings if isinstance(settings, dict) else {}}


def save_state(state):
    """Persist the app keys, preserving everything else (incl. comments).

    Only keys present in ``state`` are written: ``runners``/``activeId`` are set
    when given; ``settings`` is merged shallowly so a partial save (e.g. just the
    checklist) doesn't drop other settings.
    """
    state = state or {}
    with _LOCK:
        doc = _load_doc()
        if "runners" in state:
            doc[_K_RUNNERS] = state.get("runners") or []
        if "activeId" in state:
            doc[_K_ACTIVE] = state.get("activeId") or ""
        if "settings" in state and isinstance(state.get("settings"), dict):
            cur = doc.get(_K_SETTINGS)
            if not isinstance(cur, dict):
                cur = _new_doc()
                doc[_K_SETTINGS] = cur
            for k, v in state["settings"].items():
                cur[k] = v
        _dump_doc(doc)
    return get_state()


# Granular runner CRUD (used by /api/config/runner) — operate on the file directly
# so concurrent callers can't clobber each other's whole-state writes.

def _runners(doc):
    r = doc.get(_K_RUNNERS)
    if not isinstance(r, list):
        r = []
        doc[_K_RUNNERS] = r
    return r


def upsert_runner(runner):
    """Add (no id) or update (matching id) one runner; returns the saved record."""
    runner = dict(runner or {})
    rid = str(runner.get("id") or "").strip()
    with _LOCK:
        doc = _load_doc()
        runners = _runners(doc)
        if not rid:
            # new id: r<n> not already used
            n = 1
            used = {str(x.get("id")) for x in runners if isinstance(x, dict)}
            while ("r%d" % n) in used:
                n += 1
            rid = "r%d" % n
            runner["id"] = rid
            runners.append(runner)
        else:
            for i, x in enumerate(runners):
                if isinstance(x, dict) and str(x.get("id")) == rid:
                    runners[i] = runner
                    break
            else:
                runners.append(runner)
        _dump_doc(doc)
    return _plain(runner)


def delete_runner(rid):
    """Remove a runner by id; clears active_runner if it pointed at it."""
    rid = str(rid or "")
    with _LOCK:
        doc = _load_doc()
        runners = _runners(doc)
        doc[_K_RUNNERS] = [x for x in runners if not (isinstance(x, dict) and str(x.get("id")) == rid)]
        if str(doc.get(_K_ACTIVE) or "") == rid:
            doc[_K_ACTIVE] = ""
        _dump_doc(doc)
    return get_state()


# ── Tool paths + screenshot dir (Config / Paths dialog) ───────────────────────
# Stored under a top-level ``paths`` key in the SAME ~/.apppreview file, so the
# whole app config lives in one place. The device modules (android/ios) read an
# override via get(); blank means "auto-detect on PATH/SDK".
_K_PATHS = "paths"
PATH_KEYS = ("adb", "aapt", "scrcpy", "emulator", "iproxy", "go_ios", "wda_project", "uxplay", "screenshot_dir")


def _paths_doc():
    d = _load_doc().get(_K_PATHS)
    return d if isinstance(d, dict) else {}


def get(key, default=""):
    """Effective override for a tool path (stripped). Blank → ``default``."""
    v = str(_paths_doc().get(key) or "").strip()
    return v or default


def save_paths(d):
    """Persist tool-path / screenshot-dir overrides under the ``paths`` key.
    Blank values are removed (back to auto-detect). Returns paths_dump()."""
    d = d or {}
    with _LOCK:
        doc = _load_doc()
        cur = doc.get(_K_PATHS)
        if not isinstance(cur, dict):
            cur = _new_doc()
            doc[_K_PATHS] = cur
        for k in PATH_KEYS:
            if k in d:
                val = (d.get(k) or "").strip()
                if val:
                    cur[k] = val
                elif k in cur:
                    del cur[k]
        if not cur:                       # drop an empty paths map entirely
            try: del doc[_K_PATHS]
            except Exception: pass
        _dump_doc(doc)
    return paths_dump()


def screenshot_dir():
    """Default save dir for captured screenshots (created on demand)."""
    d = os.path.expanduser(get("screenshot_dir") or os.path.join(context.HERE, "screenshots"))
    os.makedirs(d, exist_ok=True)
    return d


def paths_dump():
    """Everything the Config / Paths dialog needs: each tool's resolved path +
    found-state + current override, plus the screenshot dir and config path."""
    from . import android, ios, airplay   # lazy to avoid an import cycle
    from .util import have
    cfg = _paths_doc()

    def row(key, label, resolved, hint):
        return {"key": key, "label": label, "resolved": resolved or "",
                "found": have(resolved), "override": str(cfg.get(key, "") or ""), "hint": hint}

    tools = [
        row("adb", "adb (Android Debug Bridge)", android.adb_bin(),
            "Mirror + điều khiển Android, cài APK (adb install)"),
        row("aapt", "aapt / aapt2 (Android build-tools)", android.aapt_bin(),
            "Đọc package name của APK để tự mở app sau khi cài"),
        row("scrcpy", "scrcpy", android.scrcpy_bin(),
            "Cửa sổ mirror native tốc độ cao"),
        row("emulator", "Android emulator", android.emulator_bin(),
            "Khởi động AVD (máy ảo Android)"),
        row("iproxy", "iproxy (libimobiledevice)", ios.iproxy_bin(),
            "Tunnel USB cho WebDriverAgent (iOS thật)"),
        row("go_ios", "go-ios (ios CLI)", ios.go_ios_bin(),
            "Cài .ipa lên iPhone thật (ios install)"),
        row("wda_project", "WebDriverAgent.xcodeproj", ios.wda_project_path(),
            "Build WDA để điều khiển iOS"),
        row("uxplay", "UxPlay (AirPlay receiver)", airplay.uxplay_bin(),
            "Mirror iPhone không dây qua AirPlay (cần GStreamer)"),
    ]
    return {"ok": True, "configPath": CONFIG_PATH, "screenshotDir": screenshot_dir(),
            "config": _plain(cfg), "tools": tools}
