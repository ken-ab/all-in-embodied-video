"""Inspect source videos and render a reviewed keep list with FFmpeg."""

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

SAMPLE_RATE = 48000
SILENCE_MARK = re.compile(r"silence_(start|end):\s*(-?\d+(?:\.\d+)?)")
SRT_TIME = r"(\d{2,}:\d{2}:\d{2}[,.]\d{3})"
SRT_RANGE = re.compile(rf"^{SRT_TIME}\s+-->\s+{SRT_TIME}(?:[ \t]+.*)?$")


def run(*command):
    return subprocess.run(command, check=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def positive_seconds(value):
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Expected a finite, positive duration")
    return seconds


def probe(file):
    data = json.loads(run("ffprobe", "-v", "error", "-show_format", "-show_streams",
                          "-of", "json", str(file)).stdout)
    streams = data["streams"]
    video = next((s for s in streams if s["codec_type"] == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        raise ValueError(f"No video stream in {file}")
    audio = next((s["index"] for s in streams if s["codec_type"] == "audio"), None)
    # Use the common container time origin for both video and audio.
    origin = float(data["format"].get("start_time", 0))
    if video.get("duration") not in (None, "N/A"):
        video_start = float(video.get("start_time", origin)) - origin
        duration = video_start + float(video["duration"])
    else:
        duration = data["format"]["duration"]
    return video["index"], audio, positive_seconds(duration)


def inspect(args):
    if not math.isfinite(args.noise_db) or args.noise_db > 0:
        raise ValueError("--noise-db must be a finite number at or below zero")
    minimum = positive_seconds(args.min_quiet)
    results = []
    for file in args.files:
        file = file.resolve(strict=True)
        _, audio, duration = probe(file)
        ranges = []
        if audio is not None:
            analysis = run("ffmpeg", "-hide_banner", "-nostats", "-i", str(file),
                           "-map", f"0:{audio}", "-vn",
                           "-af", f"silencedetect=n={args.noise_db}dB:d={minimum}",
                           "-f", "null", "-")
            start = None
            for kind, value in SILENCE_MARK.findall(analysis.stderr):
                point = min(duration, max(0.0, float(value)))
                if kind == "start":
                    start = point
                elif start is not None:
                    if point > start:
                        ranges.append({"start": start, "end": point})
                    start = None
        results.append({"file": str(file), "video_duration": duration,
                        "has_audio": audio is not None, "quiet_candidates": ranges})
    print(json.dumps(results, ensure_ascii=False, indent=2))


def subtitle_seconds(stamp):
    hours, minutes, seconds = stamp.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def read_srt(path):
    text = path.read_text(encoding="utf-8-sig").strip()
    cues = []
    for block in re.split(r"\n[ \t]*\n", text):
        lines = block.splitlines()
        if not lines:
            continue
        if lines[0].strip().isdigit():
            lines.pop(0)
        time = SRT_RANGE.fullmatch(lines[0].strip()) if lines else None
        if not time or len(lines) < 2:
            raise ValueError(f"Invalid SRT cue in {path}: {block[:100]}")
        start, end = map(subtitle_seconds, time.groups())
        if end <= start:
            raise ValueError(f"Non-positive SRT cue duration in {path}")
        cues.append((start, end, "\n".join(lines[1:])))
    return sorted(cues)


def srt_stamp(ms):
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


@dataclass(frozen=True)
class Source:
    file: Path
    video: int
    audio: int | None
    duration: float
    srt: Path | None


@dataclass(frozen=True)
class Clip:
    source: Source
    start: float
    end: float
    frames: int


def read_plan(path, fps):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    clips = []
    sources = {}
    for entry in data["keep"]:
        key = entry["source"]
        if key not in sources:
            config = data["sources"][key]
            file = (path.parent / config["video"]).resolve(strict=True)
            video, audio, duration = probe(file)
            srt = (path.parent / config["srt"]).resolve(strict=True) if config.get("srt") else None
            sources[key] = Source(file, video, audio, duration, srt)
        source = sources[key]
        start = float(entry["start"])
        end = float(entry["end"])
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end:
            raise ValueError(f"Invalid keep interval for {key}: {start}–{end}")
        if end > source.duration + 0.001:
            raise ValueError(f"Keep interval exceeds video duration for {key}: {source.duration}")
        end = min(end, source.duration)
        frames = round((end - start) * fps)
        if frames < 1:
            raise ValueError(f"Keep interval for {key} is shorter than one output frame")
        clips.append(Clip(source, start, end, frames))
    if not clips:
        raise ValueError("The plan must contain at least one keep interval")
    return clips


def map_subtitles(clips, fps):
    result = []
    frame_offset = 0
    cache = {}
    for clip in clips:
        source = clip.source.srt
        if source is not None:
            if source not in cache:
                cache[source] = read_srt(source)
            retained_end = min(clip.end, clip.start + clip.frames / fps)
            for start, end, text in cache[source]:
                left = max(start, clip.start)
                right = min(end, retained_end)
                if right > left:
                    start_ms = round((frame_offset / fps + left - clip.start) * 1000)
                    end_ms = round((frame_offset / fps + right - clip.start) * 1000)
                    if end_ms > start_ms:
                        result.append((start_ms, end_ms, text))
        frame_offset += clip.frames
    return "\n\n".join(f"{index}\n{srt_stamp(start)} --> {srt_stamp(end)}\n{text}"
                       for index, (start, end, text) in enumerate(sorted(result), 1))


def render(args):
    if min(args.width, args.height) < 2 or args.width % 2 or args.height % 2:
        raise ValueError("Output dimensions must be positive and even")
    clips = read_plan(args.plan.resolve(strict=True), args.fps)
    output = args.output.resolve()
    if output.suffix.lower() != ".mp4":
        raise ValueError("Output must have an .mp4 extension")
    subtitle_output = output.with_suffix(".srt")
    subtitles = map_subtitles(clips, args.fps)
    if output.exists() or (subtitles and subtitle_output.exists()):
        raise FileExistsError("Choose a new output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    inputs, filters, concat = [], [], []
    for index, clip in enumerate(clips):
        seconds = clip.end - clip.start
        duration = clip.frames / args.fps
        samples = clip.frames * SAMPLE_RATE // args.fps
        inputs.extend(["-ss", f"{clip.start:.9f}", "-t", f"{seconds:.9f}",
                       "-i", str(clip.source.file)])
        video = (
            f"[{index}:{clip.source.video}]"
            f"scale=trunc(iw*sar/2)*2:ih,setsar=1,"
            f"scale={args.width}:{args.height}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
            f"pad={args.width}:{args.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
            f"fps={args.fps}:start_time=0,tpad=stop_mode=clone:stop_duration={duration:.9f},"
            f"trim=end_frame={clip.frames},setpts=N/({args.fps}*TB),format=yuv420p[v{index}]"
        )
        if clip.source.audio is None:
            audio = f"anullsrc=r={SAMPLE_RATE}:cl=stereo"
        else:
            audio = (f"[{index}:{clip.source.audio}]aresample={SAMPLE_RATE}:async=1:first_pts=0,"
                     f"aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_len={samples}")
        audio += f",atrim=end_sample={samples},asetpts=N/SR/TB[a{index}]"
        filters.extend([video, audio])
        concat.extend([f"[v{index}]", f"[a{index}]"])
    filters.append("".join(concat) + f"concat=n={len(clips)}:v=1:a=1[v][a]")
    with TemporaryDirectory(dir=output.parent, prefix=".rough-cut-") as folder:
        work = Path(folder)
        movie = work / "render.mp4"
        run("ffmpeg", "-hide_banner", "-v", "error", "-xerror", *inputs,
            "-filter_complex_threads", "1", "-filter_complex", ";".join(filters),
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(movie))
        _, _, actual_duration = probe(movie)
        expected_duration = sum(clip.frames for clip in clips) / args.fps
        if abs(actual_duration - expected_duration) > 1 / args.fps + 0.001:
            raise ValueError(f"Unexpected video length: {actual_duration} vs {expected_duration}")
        run("ffmpeg", "-v", "error", "-xerror", "-i", str(movie), "-map", "0:v:0",
            "-map", "0:a:0", "-f", "null", "-")
        if output.exists() or (subtitles and subtitle_output.exists()):
            raise FileExistsError("Output was created while rendering")
        if subtitles:
            sidecar = work / "render.srt"
            sidecar.write_text(subtitles + "\n", encoding="utf-8")
            sidecar.replace(subtitle_output)
        movie.replace(output)
    print(json.dumps({"video": str(output), "duration_seconds": expected_duration,
                      "srt": str(subtitle_output) if subtitles else None}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    analysis = commands.add_parser("inspect", help="Report quiet intervals for review")
    analysis.add_argument("files", type=Path, nargs="+")
    analysis.add_argument("--noise-db", type=float, default=-38.0)
    analysis.add_argument("--min-quiet", type=float, default=0.45)
    analysis.set_defaults(handler=inspect)
    cut = commands.add_parser("render", help="Render an explicitly reviewed keep list")
    cut.add_argument("--plan", type=Path, required=True)
    cut.add_argument("--output", type=Path, required=True)
    cut.add_argument("--width", type=int, default=1080)
    cut.add_argument("--height", type=int, default=1920)
    cut.add_argument("--fps", type=int, choices=(24, 25, 30, 50, 60), default=30)
    cut.set_defaults(handler=render)
    args = parser.parse_args()
    try:
        args.handler(args)
    except subprocess.CalledProcessError as exc:
        parser.exit(1, exc.stderr or f"Tool exited with status {exc.returncode}\n")
    except (OSError, TypeError, ValueError, KeyError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
