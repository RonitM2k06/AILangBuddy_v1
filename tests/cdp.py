"""A minimal Chrome DevTools Protocol client for the mobile layout tests (Phase 15A): the standard library only (a WebSocket client in a few
dozen lines), so no browser-automation dependency is added. It drives a headless Google Chrome that can reach nothing but this machine
(--host-resolver-rules maps every other host to "not found", so not even web fonts load) with a throwaway profile."""
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

CHROME_PATHS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser")


def chrome_path():
    return next((p for p in CHROME_PATHS if Path(p).exists()), None) or shutil.which("google-chrome") or shutil.which("chromium")


class WebSocket:
    """Just enough RFC 6455 for CDP: text frames, client masking, no extensions."""

    def __init__(self, url):
        assert url.startswith("ws://127.0.0.1:"), url              # only ever the local browser
        host_port, path = url[len("ws://"):].split("/", 1)
        host, port = host_port.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /{path} HTTP/1.1\r\nHost: {host_port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            head += self.sock.recv(1)
        assert b" 101 " in head.split(b"\r\n")[0], head

    def send(self, text):
        data, mask = text.encode(), os.urandom(4)
        n = len(data)
        header = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536
                                  else bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("browser closed the connection")
            buf += chunk
        return buf

    def recv(self):
        message = b""
        while True:
            b1, b2 = self._exact(2)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._exact(8))[0]
            payload = self._exact(n)
            if b1 & 0x0F == 0x9:                                   # ping
                continue
            message += payload
            if b1 & 0x80:
                return message.decode()


class Browser:
    def __init__(self):
        exe = chrome_path()
        if not exe:
            raise RuntimeError("Google Chrome is not installed")
        self.profile = tempfile.mkdtemp(prefix="lb-chrome-")
        self.proc = subprocess.Popen([exe, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={self.profile}", "--no-first-run",
                                      "--no-default-browser-check", "--disable-extensions", "--disable-background-networking", "--disable-sync",
                                      "--disable-component-update", "--disable-default-apps", "--metrics-recording-only", "--mute-audio",
                                      "--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = Path(self.profile) / "DevToolsActivePort"
        for _ in range(200):
            if port_file.exists() and port_file.read_text().strip():
                break
            time.sleep(0.05)
        port = int(port_file.read_text().split()[0])
        targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=10).read())
        page = next(t for t in targets if t["type"] == "page")
        self.ws, self.next_id = WebSocket(page["webSocketDebuggerUrl"]), 0
        self.events = []                                          # notifications seen while waiting for replies (most recent 2000)
        self.call("Page.enable")
        self.call("Runtime.enable")

    def call(self, method, session=None, **params):
        """One CDP command. `session` targets an attached target (a service worker, say) instead of the page."""
        self.next_id += 1
        my = self.next_id
        msg = {"id": my, "method": method, "params": params}
        if session:
            msg["sessionId"] = session
        self.ws.send(json.dumps(msg))
        while True:
            msg = json.loads(self.ws.recv())
            if "method" in msg and "id" not in msg:
                self.events.append(msg)
                del self.events[:-2000]
                continue
            if msg.get("id") == my:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def viewport(self, width, height, mobile=True):
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1 if not mobile else 2, mobile=mobile)
        self.call("Emulation.setTouchEmulationEnabled", enabled=mobile)

    def evaluate(self, expression):
        r = self.call("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description", str(r["exceptionDetails"])))
        return r["result"].get("value")

    def goto(self, url, settle=1.2):
        self.call("Page.navigate", url=url)
        time.sleep(settle)

    def wait_for(self, expression, timeout=8.0):
        end = time.time() + timeout
        while time.time() < end:
            if self.evaluate(expression):
                return True
            time.sleep(0.1)
        return False

    def screenshot(self, path):
        data = self.call("Page.captureScreenshot", format="png")["data"]
        Path(path).write_bytes(base64.b64decode(data))

    def offline(self, on):
        """The device goes offline (or back): the page AND every service worker, which Chrome runs as targets of their own. One session per
        worker is kept and reused (a second session would leave the first one's setting in force); call again after a reload, since Chrome
        may have started a new worker instance meanwhile."""
        conditions = dict(offline=on, latency=0, downloadThroughput=-1, uploadThroughput=-1)
        self.call("Network.emulateNetworkConditions", **conditions)
        sessions = self.__dict__.setdefault("_sw_sessions", {})
        live = {t["targetId"] for t in self.call("Target.getTargets")["targetInfos"] if t["type"] == "service_worker"}
        for target in live - set(sessions):
            sessions[target] = self.call("Target.attachToTarget", targetId=target, flatten=True)["sessionId"]
            self.call("Network.enable", session=sessions[target])
        for target in list(sessions):
            if target not in live:
                del sessions[target]
                continue
            self.call("Network.emulateNetworkConditions", session=sessions[target], **conditions)

    def set_cookie(self, base, name, value):
        self.call("Network.setCookie", name=name, value=value, url=base, httpOnly=True, sameSite="Lax")

    def clear_cookies(self):
        self.call("Network.clearBrowserCookies")

    def close(self):
        try:
            self.call("Browser.close")
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)
