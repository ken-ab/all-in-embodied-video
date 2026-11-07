#!/usr/bin/env python3
"""Lock and verify the immutable prediction sections of a cheat prediction file.

Works in any agent (Codex has no Claude Code PreToolUse hook). A prediction
section is every block that starts with an H2 heading beginning with
"## 预测" or "## Prediction" and runs until the next H2 heading.

Locks are stored next to the predictions in predictions/.prediction-locks.json,
so they are versioned with the predictions themselves.

Usage:
  python3 prediction_lock.py lock   <predictions/xxx.md>
  python3 prediction_lock.py verify <predictions/xxx.md>

Exit codes:
  0  ok
  1  a locked section was changed or removed (verify or lock)
  2  usage error, file missing, or file has no prediction section
  3  verify: file has never been locked
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

LOCK_NAME = ".prediction-locks.json"
PREFIXES = ("## 预测", "## Prediction")


def sections(text: str) -> list[tuple[str, str]]:
    """Return (heading, sha256) for each prediction section, in file order."""
    out: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            if line.startswith(PREFIXES):
                current = [line]
                out.append((line.strip(), current))
                continue
            current = None
            continue
        if current is not None:
            current.append(line)
    result = []
    for heading, lines in out:
        body = "\n".join(lines).rstrip() + "\n"
        result.append((heading, hashlib.sha256(body.encode("utf-8")).hexdigest()))
    return result


def load(lock_path: Path) -> dict:
    if lock_path.exists():
        return json.loads(lock_path.read_text(encoding="utf-8"))
    return {}


def compare(locked: list[dict], current: list[tuple[str, str]]) -> list[str]:
    problems = []
    current_map: dict[str, list[str]] = {}
    for heading, digest in current:
        current_map.setdefault(heading, []).append(digest)
    for entry in locked:
        digests = current_map.get(entry["heading"], [])
        if not digests:
            problems.append(f"locked section removed or renamed: {entry['heading']}")
        elif entry["sha256"] not in digests:
            problems.append(f"locked section changed: {entry['heading']}")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"lock", "verify"}:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    command, file_arg = argv[1], argv[2]
    path = Path(file_arg).expanduser().resolve()
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2
    current = sections(path.read_text(encoding="utf-8"))
    if not current:
        print(f"no '## 预测' / '## Prediction' section in {path.name}", file=sys.stderr)
        return 2

    lock_path = path.parent / LOCK_NAME
    locks = load(lock_path)
    key = path.name
    locked = locks.get(key, {}).get("sections", [])
    problems = compare(locked, current)

    if command == "verify":
        if not locked:
            print(f"never locked: {key}. Immutability for this file cannot be checked.", file=sys.stderr)
            return 3
        if problems:
            for p in problems:
                print(p, file=sys.stderr)
            return 1
        print(f"ok: {len(locked)} locked section(s) unchanged in {key}")
        return 0

    # lock: refuse if an already-locked section changed; add any new sections (e.g. 预测 v2)
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        print("refusing to re-lock a changed prediction. Write a _redo.md file instead.", file=sys.stderr)
        return 1
    known = {(e["heading"], e["sha256"]) for e in locked}
    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    added = 0
    for heading, digest in current:
        if (heading, digest) not in known:
            locked.append({"heading": heading, "sha256": digest, "locked_at": now})
            known.add((heading, digest))
            added += 1
    locks[key] = {"sections": locked}
    tmp = lock_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(locks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(lock_path)
    print(f"locked {added} new section(s) in {key}; {len(locked)} total")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
