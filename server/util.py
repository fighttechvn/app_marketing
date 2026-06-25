"""Cross-cutting helpers: CLI discovery, subprocess, downloads."""
import os, re, shutil, subprocess, urllib.request


def find_bin(name, env_key, extra=()):
    """Locate a CLI tool. GUI-launched apps (Tauri) often have a minimal PATH that
    omits the Android SDK and Homebrew, so fall back to common install locations."""
    v = os.environ.get(env_key)
    if v and (os.path.exists(v) or shutil.which(v)):
        return v
    w = shutil.which(name)
    if w:
        return w
    home = os.path.expanduser("~")
    cands = list(extra)
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk:
        cands.append(os.path.join(sdk, "platform-tools", name))
    cands += [os.path.join(home, "Library/Android/sdk/platform-tools", name),
              os.path.join(home, "Android/Sdk/platform-tools", name),
              "/opt/homebrew/bin/" + name, "/usr/local/bin/" + name, "/usr/bin/" + name]
    for c in cands:
        if os.path.exists(c):
            return c
    return name


def have(p):
    return bool(p and (os.path.exists(p) or shutil.which(p)))


def run(cmd, timeout=20, binary=False):
    """Run a command. Returns (stdout, stderr, rc); stdout is bytes when binary."""
    p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    out = p.stdout if binary else p.stdout.decode("utf-8", "replace")
    return out, p.stderr.decode("utf-8", "replace"), p.returncode


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "store-preview-sync"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())


def num(s):
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else 99
