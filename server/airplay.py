"""iPhone-Mirror over AirPlay — wireless screen mirroring via UxPlay + GStreamer.

Unlike the WDA path (server/ios.py), AirPlay needs NO Xcode/USB: the iPhone's
built-in Screen Mirroring streams to UxPlay, which decodes h264 with GStreamer and
renders into its OWN native window (d3d11videosink on Windows, the GStreamer
default on macOS). This works on macOS AND Windows.

AirPlay is ONE-WAY: there is no per-frame API and no input channel back to the
device, so this module is a *controller* — it starts/stops the UxPlay receiver,
reports connection status from its log, and screenshots for the listing workflow.
For tap/swipe control use the WDA tab instead.
"""
import os, sys, time, socket, signal, tempfile, subprocess, atexit
from .util import find_bin, have, run
from . import config

UXPLAY = find_bin("uxplay", "UXPLAY_BIN", extra=["/opt/homebrew/bin/uxplay", "/usr/local/bin/uxplay"])

# One receiver process at a time. We keep the Popen + its log path so status can
# tail the log (UxPlay prints connection events to stdout) and stop can kill it.
# `port` is the local MJPEG TCP port UxPlay re-encodes the mirror to, so the app
# can embed the video in its panel instead of UxPlay's own window.
_UX = {"proc": None, "log": None, "name": None, "port": None}
_LOG = os.path.join(tempfile.gettempdir(), "sp-uxplay.log")

# Frames are re-encoded to MJPEG and served on a local tcpserversink; the HTTP
# layer relays it to the browser <img> as multipart/x-mixed-replace.
_MJPEG_HOST = "127.0.0.1"
MJPEG_BOUNDARY = "uxpframe"

# UxPlay log markers that mean a device has connected and is streaming.
_CONNECT_MARKERS = ("accepting client", "client connected", "connection request",
                    "raop ", "start mirroring", "video stream", "begin streaming")


def _tools_dir():
    """The desktop app ships a bundled UxPlay + GStreamer under a `tools/` dir
    (Tauri resource); the Rust shell passes its path to the sidecar as SP_TOOLS_DIR.
    Empty/absent when running from source — then we fall back to a system install."""
    d = os.environ.get("SP_TOOLS_DIR")
    return d if d and os.path.isdir(d) else ""


def _bundled_uxplay():
    td = _tools_dir()
    if not td:
        return ""
    cand = os.path.join(td, "uxplay.exe" if sys.platform == "win32" else "uxplay")
    return cand if os.path.exists(cand) else ""


def uxplay_bin():
    # Config override > bundled (desktop app) > system (find_bin / PATH).
    return config.get("uxplay") or _bundled_uxplay() or UXPLAY


def _gst_dir():
    """Bundled GStreamer root inside tools/ (holds bin/ + lib/gstreamer-1.0/)."""
    td = _tools_dir()
    gst = os.path.join(td, "gstreamer") if td else ""
    return gst if gst and os.path.isdir(gst) else ""


def _spawn_env():
    """Environment for the UxPlay child. When GStreamer is bundled, point the dynamic
    loader + the plugin scanner at our copy so UxPlay decodes h264 without a system
    GStreamer. Hardened runtime allows DYLD_* via entitlements (allow-dyld-env-vars)."""
    env = os.environ.copy()
    gst = _gst_dir()
    if not gst:
        return env
    if sys.platform == "darwin":
        libs = os.path.join(gst, "lib")
        plugins = os.path.join(libs, "gstreamer-1.0")
        env["DYLD_LIBRARY_PATH"] = libs + os.pathsep + env.get("DYLD_LIBRARY_PATH", "")
        env["GST_PLUGIN_SYSTEM_PATH_1_0"] = plugins
        env["GST_PLUGIN_PATH_1_0"] = plugins
    elif sys.platform == "win32":
        bind = os.path.join(gst, "bin")
        env["PATH"] = bind + os.pathsep + env.get("PATH", "")
        env["GST_PLUGIN_PATH_1_0"] = os.path.join(gst, "lib", "gstreamer-1.0")
    return env


def _gst_present():
    """GStreamer runtime installed? Bundled copy, or its CLIs on PATH. (Windows
    bundles always carry it, so treat win as present once uxplay is bundled.)"""
    if _gst_dir():
        return True
    return have("gst-inspect-1.0") or have("gst-launch-1.0") or \
        (sys.platform == "win32" and bool(_bundled_uxplay()))


def available():
    return have(uxplay_bin())


def _running():
    p = _UX["proc"]
    return bool(p and p.poll() is None)


def _default_name():
    """Receiver name shown in the iPhone's Screen Mirroring list. Includes this
    machine's hostname so several computers running AppPreview are distinguishable
    (otherwise they'd all advertise the same 'AppPreview')."""
    try:
        host = socket.gethostname().split(".")[0].strip()
    except Exception:
        host = ""
    # ASCII separator only: UxPlay rejects a non-ASCII/non-UTF-8 receiver name
    # ("detected a non-ascii … string"), and on Windows a Unicode arg like "·"
    # reaches uxplay as a non-UTF-8 byte. Keep the name plain ASCII.
    return _ascii_name("AppPreview - " + host) if host else "AppPreview"


def _ascii_name(s):
    """UxPlay only accepts ASCII receiver names. Drop non-ASCII chars (e.g. a
    hostname or user-typed name with diacritics) so `-n` never crashes uxplay."""
    out = (s or "").encode("ascii", "ignore").decode("ascii").strip()
    return out or "AppPreview"


def _primary_ip():
    """The IPv4 of the interface holding the default route — i.e. the LAN the
    iPhone is on and the address it must be able to reach. The UDP-connect trick
    sends no traffic; the kernel just picks the egress interface."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except Exception:
        return ""


def _local_ips():
    """This machine's real LAN IPv4s, best-first: the default-route IP (what the
    iPhone's Screen Mirroring must reach) leads. Excludes loopback and 169.254.*
    (APIPA/link-local — never reachable). A WSL/Hyper-V/VPN NAT address (e.g.
    172.x) can still follow the primary, but never displaces it."""
    primary = _primary_ip()
    ips = [primary] if primary else []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127.") and not ip.startswith("169.254."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def _tail(path, n=20):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return [l.rstrip() for l in f.read().splitlines()][-n:]
    except Exception:
        return []


def _connected(lines):
    low = "\n".join(lines).lower()
    return any(m in low for m in _CONNECT_MARKERS)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _mjpeg_sink(port):
    """A GStreamer videosink pipeline that re-encodes the decoded mirror to MJPEG
    and serves it on a local TCP port. jpegenc + multipartmux + tcpserversink are
    all cross-platform (gst-plugins-good), so this embeds on macOS AND Windows —
    no native window, no d3d11videosink/osxvideosink needed."""
    return ("videoconvert ! jpegenc quality=72 ! multipartmux boundary=%s ! "
            "tcpserversink host=%s port=%d sync=false" % (MJPEG_BOUNDARY, _MJPEG_HOST, port))


def _audio_args(audio):
    """Audio sink: default on macOS, WASAPI on Windows; `-as 0` mutes."""
    if not audio:
        return ["-as", "0"]
    return ["-as", "wasapisink"] if sys.platform == "win32" else []


def airplay_status():
    """Receiver health for the UI: tools present, listening, connection state."""
    lines = _tail(_LOG)
    running = _running()
    ips = _local_ips()
    primary = ips[0] if ips else ""
    return {"ok": True,
            "available": available(),
            "gstreamer": _gst_present(),
            "running": running,
            "connected": running and _connected(lines),
            "name": _UX["name"] or "",
            "defaultName": _default_name(),
            "port": _UX.get("port"),
            "ips": ips,
            "primaryIp": primary,
            # More than one real LAN IP → extra adapters (WSL/Hyper-V/VPN). This
            # build of uxplay has no interface selector, so its mdnsd may advertise
            # the wrong address; the UI warns the user to disable extras if the
            # iPhone can't find/connect to the receiver.
            "multiNet": len(ips) > 1,
            "uxplay": uxplay_bin(),
            "bundled": bool(_bundled_uxplay()),
            "log": lines[-8:],
            "platform": sys.platform}


def airplay_start(opts=None):
    """Start the UxPlay AirPlay receiver. The mirror is re-encoded to MJPEG on a
    local TCP port so the app embeds it in the panel (no separate window). Idempotent
    — returns running:True if one is already up. opts: {name, audio}."""
    opts = opts or {}
    if not available():
        return {"ok": False, "error": "uxplay not found",
                "hint": "UxPlay isn't on Homebrew — the desktop build bundles it. From source: "
                        "run desktop/scripts/build-uxplay-gstreamer.sh, or build FDH2/UxPlay "
                        "(github.com/FDH2/UxPlay) and set its path in Config / Paths."}
    if not _gst_present():
        return {"ok": False, "error": "GStreamer runtime not found",
                "hint": "Install GStreamer (macOS: brew install gstreamer "
                        "gst-plugins-base gst-plugins-good gst-plugins-bad)."}
    if _running():
        return {"ok": True, "running": True, "name": _UX["name"], "already": True}
    name = _ascii_name((opts.get("name") or _default_name()).strip() or _default_name())
    audio = opts.get("audio", True)
    port = _free_port()
    cmd = [uxplay_bin(), "-n", name, "-nh", "-fps", "30",
           "-vs", _mjpeg_sink(port)] + _audio_args(audio)
    # UxPlay block-buffers stdout when it's a pipe/file, so its connection events
    # ("Accepting client…") never reach the log → the `connected` flag can't flip.
    # `stdbuf -oL` forces line buffering so status() sees them promptly (POSIX only).
    if sys.platform != "win32" and have("stdbuf"):
        cmd = ["stdbuf", "-oL", "-eL"] + cmd
    logf = None
    try:
        logf = open(_LOG, "wb")
        # start_new_session so a Ctrl-C / parent exit doesn't take the receiver with
        # it unexpectedly; we terminate it explicitly via airplay_stop().
        _UX["proc"] = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT,
                                       start_new_session=True, env=_spawn_env())
        _UX["log"] = _LOG
        _UX["name"] = name
        _UX["port"] = port
    except Exception as e:
        return {"ok": False, "error": "failed to launch uxplay: %s" % str(e)[:200]}
    finally:
        # The child dup'd the fd; close the parent's copy so we don't leak a handle
        # on every start (Windows also keeps the file locked until it's closed).
        if logf:
            try: logf.close()
            except Exception: pass
    time.sleep(0.8)
    if _UX["proc"].poll() is not None:        # died immediately → bad sink / missing plugin
        return {"ok": False, "error": "uxplay exited on launch",
                "detail": "\n".join(_tail(_LOG, 6)),
                "hint": "Usually a missing GStreamer plugin or video sink. "
                        "Check the log; try a different videosink."}
    return {"ok": True, "running": True, "name": name, "port": port, "ips": _local_ips()}


def airplay_stop():
    """Stop the receiver and free its port (UxPlay holds it until killed)."""
    p = _UX["proc"]
    if not p or p.poll() is not None:
        _UX["proc"] = None
        _UX["port"] = None
        return {"ok": True, "running": False}
    try:
        if hasattr(os, "killpg"):
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        else:
            p.terminate()
        try:
            p.wait(timeout=4)
        except Exception:
            p.kill()
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
    _UX["proc"] = None
    _UX["port"] = None
    return {"ok": True, "running": False}


def airplay_open_mjpeg():
    """Connect to UxPlay's local MJPEG tcpserversink. Returns the socket; the HTTP
    layer relays it to the browser <img> as multipart/x-mixed-replace."""
    port = _UX.get("port")
    if not (_running() and port):
        raise RuntimeError("receiver not running")
    s = socket.create_connection((_MJPEG_HOST, port), timeout=10)
    # 10s applied only to establishing the connection. Clear it for the long-lived
    # browser relay: frames legitimately pause (iPhone locks, mirroring paused) and
    # a recv timeout would kill the relay → the <img> flaps into a reconnect loop.
    # _grab_frame() sets its own short timeout for one-shot captures.
    s.settimeout(None)
    return s


def _grab_frame(timeout=8):
    """Pull one JPEG frame out of the MJPEG stream (reads a multipart part's
    Content-Length, then that many bytes). Returns JPEG bytes or b''."""
    sock = airplay_open_mjpeg()
    sock.settimeout(timeout)
    f = sock.makefile("rb")
    try:
        length = None
        for _ in range(200):                  # scan a bounded number of header lines
            line = f.readline()
            if not line:
                break
            low = line.strip().lower()
            if low.startswith(b"content-length:"):
                try: length = int(line.split(b":", 1)[1])
                except ValueError: length = None
            elif line in (b"\r\n", b"\n") and length:
                return f.read(length)
        return b""
    finally:
        try: f.close(); sock.close()
        except Exception: pass


def airplay_capture(dest_dir):
    """Grab the current mirror frame into the listing workflow (drag into a slot).
    Pulls a JPEG straight from the embedded MJPEG stream — exactly the iPhone screen,
    no OS screenshot, no separate window needed."""
    if not _running():
        return {"ok": False, "error": "receiver not running — press ▶ Start first"}
    try:
        data = _grab_frame()
    except Exception as e:
        return {"ok": False, "error": "capture failed: %s" % str(e)[:200]}
    if not data:
        return {"ok": False, "error": "no frame yet — connect the iPhone (Screen Mirroring) first"}
    os.makedirs(dest_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = "airplay-%s.jpg" % stamp
    path = os.path.join(dest_dir, name)
    n = 1
    while os.path.exists(path):
        name = "airplay-%s-%d.jpg" % (stamp, n); path = os.path.join(dest_dir, name); n += 1
    with open(path, "wb") as fp:
        fp.write(data)
    return {"ok": True, "path": path, "file": name}


# Kill the UxPlay receiver when the server process exits so quitting the desktop
# app doesn't leave an orphan uxplay.exe advertising a dead receiver on mDNS and
# holding its ports (only reachable via Task Manager otherwise). Best-effort — a
# hard TerminateProcess won't run this, but a normal exit / SIGTERM will.
def _cleanup_uxplay():
    try:
        if _running():
            airplay_stop()
    except Exception:
        pass


atexit.register(_cleanup_uxplay)
