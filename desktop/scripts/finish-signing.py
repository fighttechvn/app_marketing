#!/usr/bin/env python3
"""finish-signing.py — finish the Developer ID setup from a MANUALLY downloaded cert.

Use this when setup-signing.py hit the 403 "Account Holder required" wall (an
Admin/App-Manager ASC API key cannot mint a Developer ID Application cert). The
CSR + private key it already generated (.signing/DeveloperID.{csr,key}) are reused.

One-time manual step (Account Holder, ~1 min):
  1. https://developer.apple.com/account/resources/certificates/add
  2. Choose **Developer ID Application** → Continue.
  3. Upload  desktop/.signing/DeveloperID.csr  (the CSR we already made).
  4. Download the resulting .cer and save it as  desktop/.signing/DeveloperID.cer

Then run:
    cd desktop && python3 scripts/finish-signing.py

It converts the cert, exports DeveloperID.p12, imports it into the login keychain
for codesign, and fills the APPLE_* values in .signing/signing.env (signing identity,
team id, cert path/password, plus the same ASC API key for notarization).
Afterwards: bash scripts/build.sh  → signed + notarized .dmg.
"""
import base64
import os
import re
import subprocess
import sys

HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))   # → desktop/
SIGN = os.path.join(HERE, ".signing")


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


def main():
    key = os.path.join(SIGN, "DeveloperID.key")
    cer = os.path.join(SIGN, "DeveloperID.cer")
    pem = os.path.join(SIGN, "DeveloperID.pem")
    p12 = os.path.join(SIGN, "DeveloperID.p12")

    if not os.path.exists(key):
        sys.exit("✗ .signing/DeveloperID.key missing — run setup-signing.py first to\n"
                 "  generate the key + CSR, then upload the CSR to the portal.")
    if not os.path.exists(cer):
        sys.exit("✗ .signing/DeveloperID.cer missing.\n"
                 "  Upload .signing/DeveloperID.csr at\n"
                 "    https://developer.apple.com/account/resources/certificates/add\n"
                 "  (type: Developer ID Application), download the .cer, save it as\n"
                 "    desktop/.signing/DeveloperID.cer  and rerun.")

    # DER (.cer) → PEM. (Re-encoding a PEM is harmless.)
    try:
        sh("openssl", "x509", "-inform", "DER", "-in", cer, "-out", pem)
    except subprocess.CalledProcessError:
        sh("openssl", "x509", "-in", cer, "-out", pem)

    subj = sh("openssl", "x509", "-in", pem, "-noout", "-subject").stdout
    if "Developer ID Application" not in subj:
        print(f"⚠️  cert subject is not a Developer ID Application cert:\n   {subj.strip()}")
        print("   (DMGs distributed outside the App Store need exactly this type.)")
    cn = re.search(r"CN ?= ?([^,/\n]+)", subj)
    ou = re.search(r"OU ?= ?([A-Z0-9]+)", subj)
    env = {**parse_env(os.path.join(SIGN, "signing.env")), **os.environ}
    identity = cn.group(1).strip() if cn else "Developer ID Application"
    team = (ou.group(1).strip() if ou else None) or env.get("APPLE_TEAM_ID") or ""

    p12_pw = base64.urlsafe_b64encode(os.urandom(12)).decode().rstrip("=")
    print("→ exporting .p12 + importing into the login keychain")
    sh("openssl", "pkcs12", "-export", "-out", p12, "-inkey", key, "-in", pem,
       "-passout", f"pass:{p12_pw}")
    subprocess.run(["security", "import", p12, "-P", p12_pw, "-T", "/usr/bin/codesign"],
                   capture_output=True, text=True)   # ok if already present

    key_id = env.get("ASC_KEY_ID") or env.get("APPLE_API_KEY") or ""
    issuer = env.get("ASC_ISSUER_ID") or env.get("APPLE_API_ISSUER") or ""
    p8_path = env.get("ASC_KEY_P8") or env.get("APPLE_API_KEY_PATH") \
        or (f"./.signing/AuthKey_{key_id}.p8" if key_id else "")

    out = os.path.join(SIGN, "signing.env")
    lines = [l for l in (open(out).read().splitlines() if os.path.exists(out) else [])
             if not re.match(r"^\s*(APPLE_SIGNING_IDENTITY|APPLE_TEAM_ID|APPLE_CERTIFICATE_PATH|"
                             r"APPLE_CERTIFICATE_PASSWORD|APPLE_API_ISSUER|APPLE_API_KEY|APPLE_API_KEY_PATH)=", l)]
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
