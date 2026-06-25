#!/usr/bin/env python3
"""setup-signing.py — auto-create the macOS signing setup from an App Store
Connect API key.

From an ASC API key (.p8 + key id + issuer) it:
  1. generates a private key + CSR (openssl),
  2. creates a **Developer ID Application** certificate via the ASC API,
  3. imports cert+key into the login keychain and exports .signing/DeveloperID.p12,
  4. writes .signing/signing.env (signing identity, team id, cert path/password,
     and the same API key for notarization).

Then `bash scripts/build.sh` signs + notarizes automatically.

Run:
    python3 scripts/setup-signing.py            # reads creds from .signing/signing.env or env
    ASC_KEY_ID=... ASC_ISSUER_ID=... ASC_KEY_P8=path.p8 python3 scripts/setup-signing.py

Requirements: Apple Developer Program membership; an API key with Admin / Account
Holder access (Developer ID certs may require the Account Holder). pip: pyjwt.
Max Developer ID Application certs per account is limited (reuse if you hit it).
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))   # → desktop/
SIGN = os.path.join(HERE, ".signing")
API = "https://api.appstoreconnect.apple.com"


def parse_env(path):
    d = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def sh(*args, **kw):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kw)


def asc_jwt(key_id, issuer, p8_text):
    try:
        import jwt
    except ImportError:
        sys.exit("✗ PyJWT missing — run: pip install pyjwt cryptography")
    now = int(time.time())
    return jwt.encode(
        {"iss": issuer, "iat": now, "exp": now + 1100, "aud": "appstoreconnect-v1"},
        p8_text, algorithm="ES256", headers={"kid": key_id, "typ": "JWT"})


def api(method, path, tok, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"✗ ASC API {method} {path} → HTTP {e.code}\n{e.read().decode('utf-8','replace')[:600]}")


def main():
    env = {**parse_env(os.path.join(SIGN, "signing.env")), **os.environ}
    key_id = env.get("ASC_KEY_ID") or env.get("APPLE_API_KEY")
    issuer = env.get("ASC_ISSUER_ID") or env.get("APPLE_API_ISSUER")
    p8 = env.get("ASC_KEY_P8_B64")
    p8_text = base64.b64decode(p8).decode() if p8 else (
        open(os.path.expandvars(env["ASC_KEY_P8"])).read() if env.get("ASC_KEY_P8") else None)
    if not (key_id and issuer and p8_text):
        sys.exit("✗ Need ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8(_B64). Put them in "
                 ".signing/signing.env or pass as env vars.")
    os.makedirs(SIGN, exist_ok=True)
    key = os.path.join(SIGN, "DeveloperID.key")
    csr = os.path.join(SIGN, "DeveloperID.csr")
    p12 = os.path.join(SIGN, "DeveloperID.p12")
    p12_pw = base64.urlsafe_b64encode(os.urandom(12)).decode().rstrip("=")

    print("→ generating private key + CSR")
    sh("openssl", "genrsa", "-out", key, "2048")
    sh("openssl", "req", "-new", "-key", key, "-out", csr,
       "-subj", "/CN=AppPreview Developer ID/O=FightTech")
    csr_pem = open(csr).read()

    tok = asc_jwt(key_id, issuer, p8_text)
    print("→ requesting Developer ID Application certificate from App Store Connect")
    cert = None
    for ctype in ("DEVELOPER_ID_APPLICATION_G2", "DEVELOPER_ID_APPLICATION"):
        try:
            resp = api("POST", "/v1/certificates", tok, {
                "data": {"type": "certificates",
                         "attributes": {"certificateType": ctype, "csrContent": csr_pem}}})
            cert = resp["data"]["attributes"]
            print(f"  created ({ctype})")
            break
        except SystemExit as e:
            print(f"  {ctype} not available, trying next…")
            tok = asc_jwt(key_id, issuer, p8_text)
    if not cert:
        sys.exit("✗ could not create a Developer ID certificate (check API key role / cert limit)")

    cer = os.path.join(SIGN, "DeveloperID.cer")
    pem = os.path.join(SIGN, "DeveloperID.pem")
    open(cer, "wb").write(base64.b64decode(cert["certificateContent"]))
    sh("openssl", "x509", "-inform", "DER", "-in", cer, "-out", pem)

    subj = sh("openssl", "x509", "-in", pem, "-noout", "-subject").stdout
    cn = re.search(r"CN ?= ?([^,/\n]+)", subj)
    ou = re.search(r"OU ?= ?([A-Z0-9]+)", subj)
    identity = cn.group(1).strip() if cn else "Developer ID Application"
    team = ou.group(1).strip() if ou else (env.get("APPLE_TEAM_ID") or "")

    print("→ exporting .p12 + importing into the login keychain")
    sh("openssl", "pkcs12", "-export", "-out", p12, "-inkey", key, "-in", pem,
       "-passout", f"pass:{p12_pw}")
    subprocess.run(["security", "import", p12, "-P", p12_pw, "-T", "/usr/bin/codesign"],
                   capture_output=True, text=True)   # ok if already present

    out = os.path.join(SIGN, "signing.env")
    lines = [l for l in (open(out).read().splitlines() if os.path.exists(out) else [])
             if not re.match(r"^\s*(APPLE_SIGNING_IDENTITY|APPLE_TEAM_ID|APPLE_CERTIFICATE_PATH|"
                             r"APPLE_CERTIFICATE_PASSWORD|APPLE_API_ISSUER|APPLE_API_KEY|APPLE_API_KEY_PATH)=", l)]
    p8_path = os.path.expandvars(env.get("ASC_KEY_P8") or os.path.join(SIGN, f"AuthKey_{key_id}.p8"))
    if p8 and not os.path.exists(p8_path):
        open(p8_path, "w").write(p8_text)
    lines += [
        f'APPLE_SIGNING_IDENTITY="{identity}"',
        f'APPLE_TEAM_ID="{team}"',
        f'APPLE_CERTIFICATE_PATH="./.signing/DeveloperID.p12"',
        f'APPLE_CERTIFICATE_PASSWORD="{p12_pw}"',
        f'APPLE_API_ISSUER="{issuer}"',
        f'APPLE_API_KEY="{key_id}"',
        f'APPLE_API_KEY_PATH="{p8_path}"',
    ]
    open(out, "w").write("\n".join(lines) + "\n")
    os.chmod(out, 0o600)

    print("\n✓ Done.")
    print(f"  identity : {identity}")
    print(f"  team id  : {team}")
    print(f"  wrote    : {out}  (+ DeveloperID.p12)")
    print("Next: cd desktop && bash scripts/build.sh   → signed + notarized .dmg")


if __name__ == "__main__":
    main()
