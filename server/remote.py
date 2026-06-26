"""Drive a remote Mac's iOS simulators over SSH (paramiko).

Holds ONE active connection plus local port-forward tunnels, so the Mac's
WebDriverAgent (HTTP 8100 + MJPEG 9100) appears on this host's 127.0.0.1 — that
lets the existing localhost WDA code in ios.py work unchanged *through the
tunnel*. The macOS-only bits (simctl / xcodebuild) are run on the Mac via run().

Used when this server runs on a non-Mac box (e.g. Windows): the user picks a
"runner" (host/user/pass) and we connect here. On macOS you'd just drive the
local simulators directly, so this stays dormant unless connect() is called.
"""
import socket, select, threading

try:
    import paramiko
except Exception:        # paramiko optional — remote features just stay unavailable
    paramiko = None

# Ports forwarded from this host's 127.0.0.1 to the Mac's 127.0.0.1 (WDA HTTP + MJPEG).
TUNNEL_PORTS = [8100, 9100]

_LOCK = threading.Lock()
_STATE = {"client": None, "host": None, "user": None, "tunnels": []}


def available():
    return paramiko is not None


def active():
    return _STATE["client"] is not None


def status():
    return {"connected": active(), "host": _STATE["host"], "user": _STATE["user"],
            "paramiko": available()}


class _Tunnel(threading.Thread):
    """Local-forward one TCP port: 127.0.0.1:<port> here → Mac 127.0.0.1:<port>
    over the SSH transport. Handles many concurrent connections (MJPEG + HTTP)."""
    def __init__(self, transport, port):
        super().__init__(daemon=True)
        self.transport, self.port, self._srv, self._stop = transport, port, None, False

    def run(self):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", self.port))
            srv.listen(16)
            srv.settimeout(1.0)
            self._srv = srv
        except Exception:
            return
        while not self._stop:
            try:
                cli, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._pipe, args=(cli,), daemon=True).start()
        try: srv.close()
        except Exception: pass

    def _pipe(self, cli):
        try:
            chan = self.transport.open_channel("direct-tcpip", ("127.0.0.1", self.port), cli.getpeername())
        except Exception:
            cli.close(); return
        if chan is None:
            cli.close(); return
        try:
            while True:
                r, _, _ = select.select([cli, chan], [], [], 1.0)
                if cli in r:
                    d = cli.recv(32768)
                    if not d: break
                    chan.sendall(d)
                if chan in r:
                    d = chan.recv(32768)
                    if not d: break
                    cli.sendall(d)
        except Exception:
            pass
        finally:
            try: chan.close()
            except Exception: pass
            try: cli.close()
            except Exception: pass

    def stop(self):
        self._stop = True
        try:
            if self._srv: self._srv.close()
        except Exception: pass


def connect(host, port, user, password):
    if not paramiko:
        raise RuntimeError("paramiko not installed on the server")
    disconnect()
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(host, port=int(port or 22), username=user, password=password,
                timeout=12, banner_timeout=12, auth_timeout=12,
                allow_agent=False, look_for_keys=False)
    tr = cli.get_transport()
    tr.set_keepalive(20)
    tunnels = [_Tunnel(tr, p) for p in TUNNEL_PORTS]
    for t in tunnels:
        t.start()
    with _LOCK:
        _STATE.update({"client": cli, "host": host, "user": user, "tunnels": tunnels})
    return status()


def disconnect():
    with _LOCK:
        for t in _STATE.get("tunnels") or []:
            try: t.stop()
            except Exception: pass
        cli = _STATE.get("client")
        _STATE.update({"client": None, "host": None, "user": None, "tunnels": []})
    if cli:
        try: cli.close()
        except Exception: pass


def _q(a):
    """Quote one argv token for a POSIX remote shell."""
    a = str(a)
    if a and all(c.isalnum() or c in "@%._+-=:/," for c in a):
        return a
    return "'" + a.replace("'", "'\\''") + "'"


def run(argv, timeout=30):
    """Run a command on the Mac. Mirrors util.run → (stdout, stderr, rc)."""
    cli = _STATE["client"]
    if not cli:
        raise RuntimeError("no remote connection")
    cmd = " ".join(_q(a) for a in argv) if isinstance(argv, (list, tuple)) else str(argv)
    _, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return out, err, rc


def read_file(path):
    """Read a remote file's bytes over SFTP (used to fetch simctl screenshots)."""
    cli = _STATE["client"]
    if not cli:
        raise RuntimeError("no remote connection")
    sftp = cli.open_sftp()
    try:
        with sftp.open(path, "rb") as f:
            return f.read()
    finally:
        sftp.close()
