"""Read-only, loopback-only media server for explicitly registered preview folders."""
from __future__ import annotations
import argparse
import json
import mimetypes
import os
import re
import base64
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
ALLOWED = {"index.html", "video.mp4", "cover.png", "cover.jpg", "cover.webp", "poster.jpg", "预览清单.json"}

def atomic_json(path, data):
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def fingerprint():
    import hashlib
    return hashlib.sha256(str(HERE).lower().encode()).hexdigest()[:20]

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def do_HEAD(self):
        self.respond(head=True)

    def do_GET(self):
        self.respond(head=False)

    def do_POST(self):
        """Only a same-origin screenshot from this UI may be saved to its preview folder."""
        route = unquote(urlsplit(self.path).path)
        match = re.fullmatch(r"/p/([a-f0-9]{16})/snapshot", route)
        expected = f"http://127.0.0.1:{self.server.server_address[1]}"
        if not match or self.headers.get("Origin") != expected or self.headers.get("Content-Type") != "application/json":
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length < 24_000_000:
                raise ValueError()
            data = json.loads(self.rfile.read(length))
            encoded = data["image"].removeprefix("data:image/png;base64,")
            payload = base64.b64decode(encoded, validate=True)
            if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError()
            registry = json.loads((HERE / "registry.json").read_text(encoding="utf-8"))
            root = Path(registry[match[1]]["directory"]).resolve()
            folder = root / "检查图"
            folder.mkdir(exist_ok=True)
            filename = datetime.now().strftime("check_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6] + ".png"
            (folder / filename).write_bytes(payload)
            result = json.dumps({"url":f"/p/{match[1]}/checks/{filename}","path":str(folder/filename)}, ensure_ascii=False).encode("utf-8")
        except (OSError, ValueError, KeyError, TypeError):
            self.send_error(400)
            return
        self.send_response(201)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(result)))
        self.end_headers()
        self.wfile.write(result)

    def respond(self, head):
        route = unquote(urlsplit(self.path).path)
        if route == "/health":
            payload = json.dumps({"service": "all-in-mobile-preview", "project": fingerprint()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if not head:
                self.wfile.write(payload)
            return
        match = re.fullmatch(r"/p/([a-f0-9]{16})(?:/(.*))?", route)
        if not match:
            self.send_error(404)
            return
        ident, name = match.groups()
        name = name or "index.html"
        is_check = bool(re.fullmatch(r"checks/check_\d{8}_\d{6}_[a-f0-9]{6}\.png", name))
        is_versioned_video = bool(re.fullmatch(r"video_[a-f0-9]{12}\.mp4", name))
        if name not in ALLOWED and not is_check and not is_versioned_video:
            self.send_error(404)
            return
        try:
            registry = json.loads((HERE / "registry.json").read_text(encoding="utf-8"))
            root = Path(registry[ident]["directory"]).resolve()
            target = (root / "检查图" / Path(name).name).resolve() if is_check else (root / name).resolve()
            allowed_parent = (root / "检查图").resolve() if is_check else root
            if target.parent != allowed_parent or not target.is_file():
                raise FileNotFoundError()
            f = target.open("rb")
        except (OSError, ValueError, KeyError):
            self.send_error(404)
            return
        with f:
            size = os.fstat(f.fileno()).st_size
            start, end, code = 0, size - 1, 200
            requested = self.headers.get("Range")
            if requested:
                r = re.fullmatch(r"bytes=(\d*)-(\d*)", requested.strip())
                try:
                    if not r or not any(r.groups()):
                        raise ValueError()
                    if not r[1]:
                        suffix = int(r[2])
                        if suffix <= 0:
                            raise ValueError()
                        start = max(0, size - suffix)
                    else:
                        start = int(r[1])
                        end = min(int(r[2]), size - 1) if r[2] else size - 1
                    if start >= size or end < start:
                        raise ValueError()
                    code = 206
                except ValueError:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
            self.send_response(code)
            kind = mimetypes.guess_type(name)[0] or "application/octet-stream"
            self.send_header("Content-Type", kind + ("; charset=utf-8" if kind in {"text/html", "application/json"} else ""))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            if code == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if head:
                return
            f.seek(start)
            remaining = end - start + 1
            try:
                while remaining:
                    chunk = f.read(min(256 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    port = server.server_address[1]
    atomic_json(HERE / ".server.json", {"pid": os.getpid(), "base_url": f"http://127.0.0.1:{port}", "project": fingerprint()})
    server.serve_forever()

if __name__ == "__main__":
    main()
