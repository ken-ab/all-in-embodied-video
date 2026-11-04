"""Build a portable local mobile-platform viewing check for a completed MP4."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from serve_preview import atomic_json

HERE = Path(__file__).resolve().parent

def media_link(source, destination):
    if destination.exists() and os.path.samefile(source, destination):
        return "hardlink"
    tmp = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        try:
            os.link(source, tmp)
            method = "hardlink"
        except OSError:
            shutil.copy2(source, tmp)
            method = "copy"
        os.replace(tmp, destination)
        return method
    finally:
        if tmp.exists():
            tmp.unlink()

def read_long_subtitle(path):
    cues = []
    pattern = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)\s*\n(.+?)(?=\n\s*\n|\Z)", re.S)
    for match in pattern.finditer(Path(path).read_text(encoding="utf-8-sig")):
        g = match.groups()
        t = int(g[0])*3600 + int(g[1])*60 + int(g[2]) + int(g[3])/1000
        end = int(g[4])*3600 + int(g[5])*60 + int(g[6]) + int(g[7])/1000
        weighted = sum(1 if ord(c)>127 else .5 for c in g[8] if not c.isspace())
        cues.append((weighted, (t+end)/2))
    return max(cues)[1] if cues else None

def build(args):
    video = Path(args.video).resolve(strict=True)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    ident = hashlib.sha256(str(out).lower().encode()).hexdigest()[:16]
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], encoding="utf-8"))
    vs = next(s for s in probe["streams"] if s["codec_type"] == "video")
    duration = float(probe["format"]["duration"])
    initial = min(max(0, args.initial_time), max(0, duration-.1))
    checks = [{"label":"开头", "time":min(2,duration/2)}, {"label":"中段", "time":duration/2}, {"label":"结尾", "time":max(0,duration-5)}]
    if args.srt:
        longest = read_long_subtitle(args.srt)
        if longest is not None:
            checks.insert(1, {"label":"长字幕", "time":longest})
    if args.checkpoints:
        checks = json.loads(Path(args.checkpoints).read_text(encoding="utf-8-sig"))
    for item in checks:
        if not isinstance(item.get("label"), str) or not 0 <= float(item["time"]) < duration:
            raise ValueError("检查点必须包含label和成片时长内的time")
    # A previous MP4 may still be open in the browser on Windows. Give each
    # verified version its own immutable URL instead of replacing an open file.
    with video.open("rb") as source:
        digest = hashlib.file_digest(source,"sha256").hexdigest()
    video_name = "video_" + digest[:12] + ".mp4"
    storage = media_link(video, out / video_name)
    cover_name = None
    if args.cover:
        cover = Path(args.cover).resolve(strict=True)
        suffix = cover.suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("封面请用PNG、JPEG或WebP")
        cover_name = "cover" + (".jpg" if suffix == ".jpeg" else suffix)
        media_link(cover, out / cover_name)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(initial), "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out / "poster.jpg")], check=True)
    built = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    config = {"id":ident,"title":args.title,"description":args.description,
              "authors":{"douyin":"创作者","wechat":"创作者","xhs":"创作者"},
              "video":video_name,"cover":cover_name,"poster":"poster.jpg",
              "duration":duration,"width":vs["width"],"height":vs["height"],
              "initial_time":initial,"checkpoints":checks,"built_at":built}
    template = (HERE / "index.template.html").read_text(encoding="utf-8")
    html = template.replace("/*__CSS__*/", (HERE / "app.css").read_text(encoding="utf-8"))
    html = html.replace("/*__CONFIG__*/", json.dumps(config, ensure_ascii=False).replace("<", "\\u003c"))
    html = html.replace("/*__JS__*/", (HERE / "app.js").read_text(encoding="utf-8"))
    (out / "index.html").write_text(html, encoding="utf-8")
    manifest = {"generated_at":built,"id":ident,"source_video":str(video),"source_bytes":video.stat().st_size,
                "source_sha256":digest,
                "media_storage":storage,"source_cover":str(Path(args.cover).resolve()) if args.cover else None,
                "page":str(out/"index.html"),"config":config,"scope":"本地模拟，非平台真实发布截图"}
    atomic_json(out / "预览清单.json", manifest)
    registry_path = HERE / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
    registry[ident] = {"directory":str(out),"title":args.title,"built_at":built}
    atomic_json(registry_path, registry)
    if os.name == "nt":
        quote = lambda s: "'" + str(s).replace("'", "''") + "'"
        ps = "& " + quote(sys.executable) + " -X utf8 " + quote(HERE/"launch_preview.py") + " --id " + quote(ident) + " --open\n"
        (out / "启动手机预览.ps1").write_text(ps, encoding="utf-8-sig")
        (out / "打开手机预览.cmd").write_text('@echo off\r\nchcp 65001 >nul\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0启动手机预览.ps1"\r\n', encoding="utf-8")
        launcher = out / "打开手机预览.cmd"
    else:
        launcher = out / "打开手机预览.command"
        command = [sys.executable, "-X", "utf8", str(HERE / "launch_preview.py"), "--id", ident, "--open"]
        launcher.write_text("#!/bin/sh\nexec " + shlex.join(command) + "\n", encoding="utf-8")
        launcher.chmod(0o755)
    url = None
    if args.start:
        from launch_preview import ensure_service
        url = ensure_service() + "/p/" + ident + "/"
        manifest["url"] = url
        atomic_json(out / "预览清单.json", manifest)
    result = {"page":str(out/"index.html"),"launcher":str(launcher),"url":url,"id":ident}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--cover")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="All In 具身｜学习记录与技术讲解。")
    p.add_argument("--out", required=True)
    p.add_argument("--srt")
    p.add_argument("--checkpoints")
    p.add_argument("--initial-time", type=float, default=2)
    p.add_argument("--start", action="store_true")
    build(p.parse_args())

if __name__ == "__main__":
    main()
