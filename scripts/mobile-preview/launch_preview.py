"""Start/reuse one local preview service. No browser is opened unless --open is given."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from serve_preview import fingerprint

HERE = Path(__file__).resolve().parent

def healthy():
    try:
        state = json.loads((HERE / ".server.json").read_text(encoding="utf-8"))
        base = state["base_url"]
        if not base.startswith("http://127.0.0.1:"):
            return None
        with urllib.request.urlopen(base + "/health", timeout=.7) as res:
            info = json.load(res)
        if info.get("service") == "all-in-mobile-preview" and info.get("project") == fingerprint():
            return base
    except (OSError, ValueError, KeyError):
        pass
    return None

def ensure_service():
    base = healthy()
    if base:
        return base
    with (HERE / "server.log").open("ab") as log:
        subprocess.Popen([sys.executable, "-X", "utf8", str(HERE / "serve_preview.py")],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log, cwd=HERE,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        base = healthy()
        if base:
            return base
        time.sleep(.12)
    raise RuntimeError("手机预览服务未能启动，请查看 scripts/mobile-preview/server.log")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    registry = json.loads((HERE / "registry.json").read_text(encoding="utf-8"))
    if args.id not in registry:
        raise ValueError("未登记的预览")
    url = ensure_service() + "/p/" + args.id + "/"
    print(url, flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(url)

if __name__ == "__main__":
    main()
