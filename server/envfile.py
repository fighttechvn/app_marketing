"""Tiny .env parser (no python-dotenv dependency)."""
import os


def parse_env(path):
    return parse_env_text(open(path, encoding="utf-8").read()) if os.path.exists(path) else {}


def parse_env_text(text):
    d = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip()] = v.strip().strip('"').strip("'")
    return d
