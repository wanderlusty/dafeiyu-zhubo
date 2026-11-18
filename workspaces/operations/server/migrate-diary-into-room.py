#!/usr/bin/env python3
"""Move dated diaries into Xiaobai's writable room without overwriting data."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


DATE_FILE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def candidates(world: Path) -> tuple[list[tuple[Path, Path]], list[Path]]:
    room = world / "room"
    target = room / "diary"
    sources = (world / "diary", room / "diary-待迁")
    planned: list[tuple[Path, Path]] = []
    skipped: list[Path] = []
    for source_dir in sources:
        if not source_dir.is_dir():
            continue
        for source in sorted(source_dir.iterdir(), key=lambda item: item.name):
            if not source.is_file() or source.suffix.lower() != ".md":
                continue
            if not DATE_FILE.fullmatch(source.name):
                skipped.append(source)
                continue
            planned.append((source, target / source.name))
    return planned, skipped


def copy_without_overwrite(source: Path, target: Path, apply: bool) -> str:
    if target.exists():
        if sha256(source) == sha256(target):
            return "same"
        raise RuntimeError(f"conflict: {target} already exists with different content")
    if not apply:
        return "copy"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    shutil.copy2(source, temporary)
    if sha256(source) != sha256(temporary):
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"copy verification failed: {source}")
    os.replace(temporary, target)
    return "copied"


def update_world_config(config: Path, diary_dir: Path, apply: bool) -> bool:
    original = config.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    start = next((index for index, line in enumerate(lines) if re.fullmatch(r"- id:\s*dsh-world\s*", line.rstrip("\r\n"))), None)
    if start is None:
        raise RuntimeError(f"dsh-world block not found in {config}")
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("- id:")), len(lines))
    value = "    diaryDir: '" + diary_dir.as_posix().replace("'", "''") + "'"
    value += "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
    existing = next((index for index in range(start, end) if lines[index].startswith("    diaryDir:")), None)
    if existing is not None:
        if lines[existing] == value:
            return False
        lines[existing] = value
    else:
        world_id = next((index for index in range(start, end) if lines[index].startswith("    worldId:")), None)
        if world_id is None:
            raise RuntimeError(f"worldId not found under dsh-world in {config}")
        lines.insert(world_id + 1, value)
    if apply:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = config.with_name(f"{config.name}.before-diary-room-{stamp}")
        if backup.exists():
            raise RuntimeError(f"backup already exists: {backup}")
        shutil.copy2(config, backup)
        temporary = config.with_name(f".{config.name}.{os.getpid()}.tmp")
        temporary.write_text("".join(lines), encoding="utf-8", newline="")
        os.replace(temporary, config)
        print(f"config updated: {config}")
        print(f"config backup:  {backup}")
    else:
        print(f"config would be updated: {config}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--apply", action="store_true", help="write changes; otherwise print a dry run")
    args = parser.parse_args()

    world = args.world.resolve()
    room = world / "room"
    target = room / "diary"
    if not room.is_dir():
        raise FileNotFoundError(room)
    if args.apply:
        target.mkdir(parents=True, exist_ok=True)
    planned, skipped = candidates(world)
    if skipped:
        print("skipped non-canonical files (left in place):")
        for path in skipped:
            print(f"  {path}")
    if not planned:
        print("no dated diary files found")
    for source, destination in planned:
        result = copy_without_overwrite(source, destination, args.apply)
        print(f"{result:6} {source} -> {destination}")
    if args.config:
        update_world_config(args.config.resolve(), target.resolve(), args.apply)
    if not args.apply:
        print("dry run only; rerun with --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
