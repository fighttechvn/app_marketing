---
title: Remote iOS control & Runners
description: Drive a Mac's iOS simulators from a non-Mac host (e.g. Windows) over SSH. How to add a machine (password or SSH key), test the connection, mirror & control the simulator, plus the runner data format — localStorage, export/import JSON, and the /api/ios/* endpoints.
sidebar:
  order: 5
---

iOS simulators only run on **macOS**. To use the Playground's iPhone mirror &
control from a non-Mac host (Windows, Linux), register that Mac as a **runner**
and connect to it over **SSH**. The server opens local port-forward tunnels so
the Mac's WebDriverAgent appears on `127.0.0.1` here — the existing localhost
device-control code (see [Device preview & control](/reference/device-preview/))
then works unchanged through the tunnel.

> **One-line summary.** A *runner* = a remote machine you SSH into. For iOS it's a
> Mac; the tool runs `simctl`/`xcodebuild` there over SSH, pulls screenshots back
> via SFTP, and tunnels WebDriverAgent's `8100`/`9100` ports to this host.

## Requirements

**On the Mac (the runner):**

- macOS with Xcode / `xcrun simctl` (and a booted simulator to mirror).
- **Remote Login (SSH) enabled** — System Settings → General → Sharing → *Remote
  Login = On*. Without it, port 22 refuses/times out.
- For **tap / swipe** (not just viewing): **WebDriverAgent** via Appium's xcuitest
  driver — `npm i -g appium && appium driver install xcuitest`. Mirror-only
  (screenshots) needs no WDA.

**Network:** the Mac must be reachable from this host on the SSH port (default
`22`) — same LAN, VPN, or a forwarded port.

## How to use

1. Open **⚙ Settings → 🖥 Runners**.
2. **Add a machine** — fill in:
   - **Tên / Name** — a label.
   - **Host / IP** — e.g. `192.168.1.138`.
   - **Port (SSH)** — default `22`.
   - **Username** — the macOS account.
   - **Xác thực / Auth** — choose **Mật khẩu (Password)** *or* **SSH key**:
     - *Password*: type the account password.
     - *SSH key*: paste the **private key** text (`~/.ssh/id_ed25519` or `id_rsa`)
       and a **passphrase** if the key has one.
3. **🔌 Test connection** — validates the credentials without saving or
   connecting for real. It reports whether the box has `xcrun` and how many
   simulators are **booted** (e.g. *"Kết nối OK · xcrun có · 1 simulator đang
   chạy"*). A wrong password shows *"Authentication failed"*.
4. **＋ Thêm máy / Save** the machine. Use **Chọn** to mark it active (optional).
5. **📱 iOS** on the machine's row — SSH-connects and opens the iPhone preview
   tab mirroring the Mac's simulator.
6. **Control:** click the mirror to **tap**, drag to **swipe**. If WDA isn't
   running yet, press **▶ Start WDA** in the panel (first build ~1–3 min).
7. **Ngắt / Disconnect** (banner button) closes the SSH connection.

**Export / Import.** The Runners footer has **⤓ Export** (downloads
`runners.json`) and **⤒ Import** (loads a `.json` file and appends machines).

## Data format

Runners live **only in this browser's `localStorage`** (key **`sp-runners-v1`**) —
nothing is persisted server-side. Credentials are sent to the local server only
when you **Test** or **Connect**.

### `localStorage` shape

```json
{
  "runners": [ /* Runner objects, see below */ ],
  "activeId": "rn-abc123"
}
```

### Runner object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Auto-generated (`rn-<base36>`). Stable per machine. |
| `name` | string | yes | Display label. |
| `host` | string | yes | Hostname or IP. |
| `port` | number | — | SSH port; defaults to `22`. |
| `user` | string | yes | SSH username (macOS account). |
| `auth` | `"password"` \| `"key"` | yes | Which auth fields apply. |
| `pass` | string | when `auth="password"` | Account password (plaintext). |
| `key` | string | when `auth="key"` | PEM/OpenSSH **private key** text. Ed25519/ECDSA/RSA/DSA. |
| `passphrase` | string | — | Passphrase protecting `key`, if any. |

Saving an entry keeps only the fields for the selected `auth` (no stale
`pass`/`key` from the other mode).

### Export / Import JSON

**Export** writes:

```json
{
  "version": 1,
  "runners": [
    {
      "id": "rn-mq1a",
      "name": "Mac mini",
      "host": "192.168.1.138",
      "port": 22,
      "user": "trantrunghieu",
      "auth": "password",
      "pass": "••••••"
    },
    {
      "id": "rn-mq1b",
      "name": "Build Mac",
      "host": "10.0.0.9",
      "port": 22,
      "user": "ci",
      "auth": "key",
      "key": "-----BEGIN OPENSSH PRIVATE KEY-----\n…\n-----END OPENSSH PRIVATE KEY-----",
      "passphrase": ""
    }
  ]
}
```

**Import** accepts either the `{ "version": 1, "runners": [...] }` envelope **or**
a bare `[ … ]` array. Each entry needs at least `host` and `user`; `port` defaults
to `22`, `auth` to `"password"`. Imported machines get **fresh ids** and are
**appended** to the existing list (import never wipes what you already have).

## API endpoints

All bound to `127.0.0.1` only. Bodies are JSON.

| Endpoint | Body | Returns |
|----------|------|---------|
| `POST /api/ios/test` | `{host, port, user, pass?, key?, passphrase?}` | `{ok, host, xcrun, booted}` — throwaway connect, **not** stored. `{ok:false, error}` on failure. |
| `POST /api/ios/connect` | `{host, port, user, pass?, key?, passphrase?}` | `{ok, connected, host, user, paramiko, ios:{…sims}}` — opens the SSH connection + tunnels. |
| `POST /api/ios/disconnect` | — | `{ok, connected:false, …}` |
| `GET /api/ios/remote` | — | `{ok, connected, host, user, paramiko}` — current state. |

Once connected, the existing **`/api/wda/*`** and **`/api/adb/*`** routes become
remote-aware automatically (the panel UI is unchanged). See
[Device preview & control](/reference/device-preview/) for those.

## How it works

```
index.html  ── Runners dialog (localStorage) + preview panel
                 │  POST /api/ios/connect {host,user,pass|key…}
                 ▼
server/remote.py  ── paramiko SSH client
                       • exec()      → run simctl/xcodebuild on the Mac
                       • read_file() → SFTP-pull simulator screenshots
                       • _Tunnel     → local-forward 8100 (WDA HTTP) + 9100 (MJPEG)
server/ios.py     ── when connected, routes simctl/xcodebuild over SSH;
                      WDA HTTP/MJPEG/tap/swipe reach the Mac via the tunnel
                      (so the 127.0.0.1 WDA code is unchanged)
```

- **Mirror.** Simulators are mirrored with **screenshot polling** (WDA/`simctl`
  screenshot pulled back over SFTP), not MJPEG — WDA's MJPEG server returns HTML
  for simulators over the tunnel and would hang the `<img>`. Real USB devices keep
  MJPEG.
- **Tap.** Uses WDA's **W3C pointer-actions** API (`/session/{id}/actions`); the
  legacy `/wda/tap/0` endpoint returns HTTP 500 on iOS 18+/26. Swipe uses
  `/wda/dragfromtoforduration`. Coordinates map to logical **points** from
  `/api/wda/status` `size`.
- **Auth.** `remote._open()` connects with a password, or a pasted private key
  parsed as Ed25519/ECDSA/RSA/DSA (with optional passphrase).

## Security notes

- Runner credentials (passwords **and** private keys) are stored **in plaintext**
  in this browser's `localStorage`, and the **Export** file contains them too —
  only use trusted machines and keep the export file safe.
- Credentials are sent **only to the local `127.0.0.1` server** on Test/Connect,
  never to a third party.
- The SSH client uses `AutoAddPolicy` (it accepts the host key on first connect
  without prior pinning) — fine on a trusted LAN; avoid over untrusted networks.
- `paramiko` is bundled into the desktop sidecar; if it's missing the server
  reports *"SSH support (paramiko) not installed"*.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Test → connection times out | Mac asleep/off, wrong IP, or **Remote Login** not enabled. Enable SSH and verify the IP (`ipconfig getifaddr en0`). |
| "Authentication failed" | Wrong password, or wrong key/passphrase. |
| Connected but iOS panel is **blank** | No booted simulator — boot one on the Mac, or press **▶ Boot** / **⟳** in the panel. |
| Mirror works but **tap/swipe** do nothing | WebDriverAgent isn't running — press **▶ Start WDA** (needs the Appium xcuitest driver installed on the Mac). |
| "no iPhone or simulator" after connect | The Mac has no booted/available simulator, or `xcrun` is missing (not a Mac / no Xcode). |
| "SSH support (paramiko) not installed" | Rebuild the desktop sidecar (`build-sidecar.sh` bundles `paramiko`), or `pip install paramiko` for a local `serve.py`. |
