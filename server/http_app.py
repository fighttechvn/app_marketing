"""The HTTP server: static routing for the umbrella site + the /api/* endpoints.

Binds localhost only — /api/env and /api/sync expose store credentials, and the
adb/WDA/preview endpoints shell out / read local files, so this must never be
served on 0.0.0.0 / the LAN.
"""
import os, sys, json, tempfile, http.server, urllib.parse, socket, getpass
from . import context
from . import stores, project, android, ios, airplay, preview, logs, remote, config


def host_info():
    """This machine's SSH-target info, for the 'Initial Runner' share button —
    so another host can register THIS box as a runner and SSH into it."""
    name = socket.gethostname()
    ips = []
    try:  # primary LAN IP (UDP connect trick — no traffic sent)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ips.append(s.getsockname()[0]); s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(name, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    try:
        user = getpass.getuser()
    except Exception:
        user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    ssh_up = False
    try:
        t = socket.socket(); t.settimeout(0.3)
        ssh_up = t.connect_ex(("127.0.0.1", 22)) == 0; t.close()
    except Exception:
        pass
    return {"ok": True, "hostname": name, "user": user, "platform": sys.platform,
            "ips": ips, "sshPort": 22, "sshRunning": ssh_up}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kw):
        # context.root() is read per-request so an /api/open folder switch is live.
        super().__init__(*args, directory=context.root(), **kw)

    def translate_path(self, path):
        # Umbrella routing: / → landing, /docs/ → built Astro, /playground/ → the
        # store-preview tool, everything else → the tool dir. Each mount is guarded
        # by existence so the canonical (tool-only) deploy still serves "/" = tool.
        p = urllib.parse.unquote(urllib.parse.urlparse(path).path)
        if p in ("/", "") and os.path.exists(context.home_html()):
            return context.home_html()
        if (p == "/docs" or p.startswith("/docs/")) and os.path.isdir(context.docs_dist()):
            rest = p[len("/docs"):].lstrip("/")
            return os.path.join(context.docs_dist(), *rest.split("/")) if rest else context.docs_dist()
        low = p.lower()
        if low == "/playground" or low.startswith("/playground/"):
            rest = p[len("/playground"):].lstrip("/")
            return os.path.join(context.root(), *rest.split("/")) if rest else context.root()
        return super().translate_path(path)

    # ---- response helpers ----
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bin(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _query(self, key, default=None):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        return (q.get(key) or [default])[0]

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n).decode("utf-8")

    def _json_body(self):
        return json.loads(self._body() or "{}")

    def _raw_body(self):
        """Read the request body as raw bytes (binary uploads — APK/IPA)."""
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n) if n else b""

    def _install(self, kind):
        """Shared install handler for Android (adb) + iOS. Two source modes:
          • JSON  {serial|udid, path}  — a local file the server can read
            (the desktop native drop bridges a real path here, no upload).
          • raw upload  ?serial|udid=…&name=foo.apk  with the bytes as the body
            (browser drag/file-picker) — written to a temp file, then installed.
        """
        ident_key = "serial" if kind == "android" else "udid"
        ctype = (self.headers.get("Content-Type") or "").lower()
        tmp = None
        try:
            if "application/json" in ctype:
                b = self._json_body()
                ident, path = b.get(ident_key) or None, b.get("path", "")
            else:
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                ident = (q.get(ident_key) or [None])[0]
                name = (q.get("name") or ["build"])[0]
                data = self._raw_body()
                if not data:
                    return self._json(400, {"ok": False, "error": "empty upload"})
                suffix = os.path.splitext(name)[1] or ".bin"
                fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="sp-build-")
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                path = tmp
            fn = android.adb_install if kind == "android" else ios.ios_install
            self._json(200, fn(ident, path))
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})
        finally:
            if tmp:
                try: os.remove(tmp)
                except OSError: pass

    def _proxy_mjpeg(self, udid):
        """Relay WDA's MJPEG screen stream (device :9100) to the browser <img>."""
        try:
            up = ios.ios_mjpeg_open(udid)
        except Exception as e:
            self._json(502, {"ok": False, "error": "MJPEG unavailable — is WDA running? " + str(e)[:120]})
            return
        ctype = up.headers.get("Content-Type", "multipart/x-mixed-replace; boundary=--BoundaryString")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        try:
            while True:
                chunk = up.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except Exception:
            pass   # client closed the stream (switched tabs / device); stop relaying

    def _proxy_airplay_mjpeg(self):
        """Relay UxPlay's local MJPEG stream (AirPlay mirror) to the browser <img>."""
        try:
            sock = airplay.airplay_open_mjpeg()
        except Exception as e:
            self._json(502, {"ok": False, "error": "AirPlay stream unavailable — " + str(e)[:120]})
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=" + airplay.MJPEG_BOUNDARY)
        self.end_headers()
        try:
            while True:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except Exception:
            pass   # client closed the stream (switched tabs / stopped) — stop relaying
        finally:
            try: sock.close()
            except Exception: pass

    def _stream_logs(self, kind, ident, level):
        """Relay a device/sim log stream to the browser as chunked text/plain.
        The subprocess is killed when the client disconnects (tab switch/close)."""
        try:
            proc = logs.log_open(kind, ident, level)
        except Exception as e:
            self._json(400, {"ok": False, "error": str(e)})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("X-Accel-Buffering", "no")   # don't let any proxy buffer the stream
        self.end_headers()
        try:
            for line in iter(proc.stdout.readline, b""):
                self.wfile.write(line)
                self.wfile.flush()
        except Exception:
            pass   # client closed the stream — fall through to terminate the process
        finally:
            try: proc.terminate()
            except Exception: pass

    def do_GET(self):
        route = self.path.split("?")[0]
        if route == "/api/sync":
            try: self._json(200, stores.sync())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/scan":
            # auto-check the active root (or ?path=…) without switching
            try: self._json(200, {"ok": True, **project.scan(self._query("path"))})
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/env":
            try: self._json(200, stores.env_dump())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/paths":
            # Product tool paths (adb/scrcpy/…) resolved + found-state + screenshot
            # dir, for the Config / Paths dialog. (Distinct from /api/config, which
            # carries the app's runners/settings.)
            try: self._json(200, config.paths_dump())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        # ---- Preview panel: Android (adb) + local file preview ----
        if route == "/api/adb/devices":
            try: self._json(200, android.adb_devices())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/screen":
            try: self._bin(200, android.adb_screen(self._query("serial")), "image/png")
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/emu/avds":
            try: self._json(200, android.emu_avds())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/preview-file":
            try:
                body, ctype = preview.preview_file(self._query("path", ""))
                self._bin(200, body, ctype)
            except FileNotFoundError as e:
                self._json(404, {"ok": False, "error": f"not found: {e}"})
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        # ---- Preview panel: iOS (WebDriverAgent) ----
        if route == "/api/ios/remote":
            # Status of the SSH connection to a Mac runner (for remote iOS control).
            try: self._json(200, {"ok": True, **remote.status()})
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/host-info":
            # This machine's SSH-target info (for the "Initial Runner" share button).
            try: self._json(200, host_info())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/config":
            # App config from ~/.apppreview: {runners, activeId, settings}.
            try: self._json(200, {"ok": True, **config.get_state()})
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/wda/devices":
            try: self._json(200, ios.ios_devices())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/wda/status":
            try: self._json(200, ios.ios_status(self._query("udid")))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/wda/screen":
            try: self._bin(200, ios.ios_screen(self._query("udid")), "image/png")
            except Exception as e: self._json(502, {"ok": False, "error": str(e)})
            return
        if route == "/api/wda/mjpeg":
            self._proxy_mjpeg(self._query("udid"))
            return
        if route == "/api/airplay/status":
            try: self._json(200, airplay.airplay_status())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/airplay/mjpeg":
            self._proxy_airplay_mjpeg()
            return
        if route == "/api/airplay/view":
            # Standalone viewer page (the "⤢ separate window" button opens this) —
            # a full-bleed <img> on the live MJPEG mirror.
            html = ("<!doctype html><meta charset=utf-8><title>AirPlay — AppPreview</title>"
                    "<style>html,body{margin:0;height:100%;background:#000;overflow:hidden}"
                    "img{width:100%;height:100%;object-fit:contain;display:block}</style>"
                    "<img src='/api/airplay/mjpeg' alt='AirPlay mirror'>").encode()
            self._bin(200, html, "text/html; charset=utf-8")
            return
        # ---- Preview panel: live logs (logcat / syslog / simctl log stream) ----
        if route == "/api/logs/targets":
            try: self._json(200, logs.log_targets())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/logs/stream":
            self._stream_logs(self._query("kind"), self._query("id"), self._query("level"))
            return
        return super().do_GET()

    def do_POST(self):
        route = self.path.split("?")[0]
        if route == "/api/config":
            # Save the app-managed slice into ~/.apppreview (preserves other keys).
            # Body: {runners?, activeId?, settings?} — only present keys are written.
            try: self._json(200, {"ok": True, **config.save_state(self._json_body())})
            except Exception as e: self._json(500, {"ok": False, "error": str(e)[:200]})
            return
        if route == "/api/config/runner":
            # Add (no id) or update (with id) one runner. Body = the runner record.
            try: self._json(200, {"ok": True, "runner": config.upsert_runner(self._json_body())})
            except Exception as e: self._json(500, {"ok": False, "error": str(e)[:200]})
            return
        if route == "/api/config/runner/delete":
            # Delete a runner by id. Body: {"id": "..."}.
            try: self._json(200, {"ok": True, **config.delete_runner(self._json_body().get("id"))})
            except Exception as e: self._json(500, {"ok": False, "error": str(e)[:200]})
            return
        if route == "/api/paths":
            # Save tool-path / screenshot-dir overrides from the Config dialog.
            try: self._json(200, {"ok": True, **config.save_paths(self._json_body())})
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/install":
            self._install("android")
            return
        if route == "/api/adb/capture":
            try: self._json(200, android.adb_capture(self._json_body().get("serial") or None, config.screenshot_dir()))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/ios/install":
            self._install("ios")
            return
        if route == "/api/ios/capture":
            try: self._json(200, ios.ios_capture(self._json_body().get("udid") or None, config.screenshot_dir()))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/open":
            # Switch the active project folder; body = {"path": "..."}.
            try: self._json(200, project.open_folder(self._json_body().get("path", "")))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/apply-template":
            try: self._json(200, project.apply_template())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/input":
            try: self._json(200, android.adb_input(self._json_body()))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/scrcpy":
            try: self._json(200, android.adb_scrcpy(self._json_body().get("serial") or None))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/connect":
            try: self._json(200, android.adb_connect(self._json_body().get("addr")))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/pair":
            try:
                b = self._json_body()
                self._json(200, android.adb_pair(b.get("addr"), b.get("code")))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/tcpip":
            try: self._json(200, android.adb_tcpip(self._json_body().get("serial") or None))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/disconnect":
            try: self._json(200, android.adb_disconnect(self._json_body().get("addr")))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/qr/start":
            try: self._json(200, android.adb_qr_start())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/adb/qr/poll":
            try: self._json(200, android.adb_qr_poll())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/emu/launch":
            try: self._json(200, android.emu_launch(self._json_body().get("name") or ""))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/sim/boot":
            try: self._json(200, ios.ios_sim_boot(self._json_body().get("udid") or None))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/logs/clear":
            try:
                b = self._json_body()
                self._json(200, logs.log_clear(b.get("kind"), b.get("id")))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/wda/input":
            try: self._json(200, ios.ios_input(self._json_body()))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/wda/launch":
            try: self._json(200, ios.ios_launch(self._json_body().get("udid") or None))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/airplay/start":
            try: self._json(200, airplay.airplay_start(self._json_body()))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/airplay/stop":
            try: self._json(200, airplay.airplay_stop())
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/airplay/capture":
            try: self._json(200, airplay.airplay_capture(config.screenshot_dir()))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/ios/connect":
            # Open an SSH connection to a Mac runner so iOS control routes there.
            # Body: {host, port, user, pass} (sent from the Runners dialog).
            try:
                b = self._json_body()
                if not remote.available():
                    self._json(200, {"ok": False, "error": "SSH support (paramiko) not installed on the server"})
                    return
                remote.connect(b.get("host"), b.get("port") or 22, b.get("user"),
                               b.get("pass") or "", b.get("key"), b.get("passphrase"))
                # report what the Mac offers (simctl available + simulator list)
                self._json(200, {"ok": True, **remote.status(), "ios": ios.ios_devices()})
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e)[:200]})
            return
        if route == "/api/ios/test":
            # Validate a runner's SSH creds WITHOUT connecting/tunnelling for real.
            try:
                b = self._json_body()
                if not remote.available():
                    self._json(200, {"ok": False, "error": "SSH support (paramiko) not installed on the server"})
                    return
                self._json(200, remote.test(b.get("host"), b.get("port") or 22, b.get("user"),
                                            b.get("pass") or "", b.get("key"), b.get("passphrase")))
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e)[:200]})
            return
        if route == "/api/ios/disconnect":
            try: remote.disconnect(); self._json(200, {"ok": True, **remote.status()})
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/test":
            # Verify the credentials in the posted .env text WITHOUT saving them.
            try: self._json(200, stores.test_creds(self._body()))
            except Exception as e: self._json(500, {"ok": False, "error": str(e)})
            return
        if route == "/api/env":
            # Save an imported .env to local — first-time only (won't clobber an
            # existing .env unless ?force=1). Localhost only.
            try:
                body = self._body()
                force = "force=1" in (self.path.split("?", 1)[1] if "?" in self.path else "")
                dest = os.path.join(context.root(), ".env")
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

    def log_message(self, *args, **kwargs):
        # Silence per-request stderr logging. In the desktop sidecar the Tauri shell
        # stops actively draining our output once the window is open; on Windows a
        # chatty stderr would fill the pipe buffer and stall/kill the server (→ the
        # webview then shows ERR_CONNECTION_REFUSED). No logging = nothing to block on.
        pass


def run():
    # On Windows the console defaults to cp1252, which can't encode the "→" in the
    # log line below — an unhandled UnicodeEncodeError there would kill the server
    # right after it binds. Force UTF-8 stdout/stderr so logging never crashes it.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    # PORT=0 lets the OS pick a free port (used by the desktop sidecar, which reads
    # the actual port from stdout).
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", context.PORT), Handler)
    actual = httpd.server_address[1]
    print(f"READY http://127.0.0.1:{actual}/", flush=True)   # parsed by the Tauri shell
    print(f"→ store-preview server (/api/sync, /api/env) on http://localhost:{actual}/")
    httpd.serve_forever()
