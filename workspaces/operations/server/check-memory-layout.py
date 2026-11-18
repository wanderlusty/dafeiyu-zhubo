#!/usr/bin/env python3
"""Read-only checks for Xiao Bai's scene routing and memory layout."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


FILES = (
    "shared.md",
    "room/AGENTS.md",
    "room/memory/qq.md",
    "room/memory/qq-style.md",
    "bili-duty/AGENTS.md",
    "bili-duty/memory.md",
    "live/AGENTS.md",
    "live/memory.md",
    "service/AGENTS.md",
    "service/memory.md",
)


def normalized(value: str) -> str:
    return re.sub(r"/+", "/", value.replace("\\", "/")).rstrip("/").casefold()


def block_value(text: str, block_id: str, key: str) -> str | None:
    match = re.search(
        rf"(?ms)^- id: {re.escape(block_id)}\s*\r?\n(?:(?!^- id:).)*",
        text,
    )
    if not match:
        return None
    value = re.search(rf"(?m)^[ \t]+{re.escape(key)}:[ \t]*([^\r\n]*)", match.group(0))
    return value.group(1).strip() if value else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--workspaces", type=Path)
    parser.add_argument("--bili-config", type=Path)
    args = parser.parse_args()

    world = args.world.resolve()
    failures: list[str] = []
    warnings: list[str] = []
    for relative in FILES:
        path = world / relative
        if path.is_file():
            print(f"PASS file {relative}")
        else:
            failures.append(f"missing file: {relative}")

    diary = world / "room" / "diary"
    if diary.is_dir():
        print("PASS dir room/diary")
    else:
        failures.append("missing writable diary directory: room/diary")

    if args.config:
        config = args.config.resolve()
        text = config.read_text(encoding="utf-8")
        expected_paths = {
            ("dsh-world", "diaryDir"): diary,
            ("bili-scroll", "workspace"): world / "bili-duty",
        }
        for (block_id, key), expected_path in expected_paths.items():
            value = block_value(text, block_id, key)
            if value is None:
                failures.append(f"missing {block_id}.{key} in {config}")
            elif normalized(value.strip("'\"")) != normalized(str(expected_path)):
                failures.append(
                    f"{block_id}.{key} is {value!r}; expected {str(expected_path)!r}"
                )
            else:
                print(f"PASS config {block_id}.{key}")
        expected_values = {
            ("dsh-world", "batchQuietMs"): "800",
            ("dsh-world", "bindHomeSession"): "none",
            ("agent-default-model", "reasoningEffort"): "low",
        }
        for (block_id, key), expected_value in expected_values.items():
            value = block_value(text, block_id, key)
            if value != expected_value:
                failures.append(
                    f"{block_id}.{key} is {value!r}; expected {expected_value!r}"
                )
            else:
                print(f"PASS config {block_id}.{key}")

    if args.workspaces:
        path = args.workspaces.resolve()
        state = json.loads(path.read_text(encoding="utf-8"))
        workspaces = state.get("tables", {}).get("workspaces", {})
        sessions = [
            session
            for workspace in workspaces.values()
            for session in workspace.get("sessionIds", [])
        ]
        duplicates = sorted(name for name, count in Counter(sessions).items() if count > 1)
        if duplicates:
            failures.append(f"duplicate session registrations: {', '.join(duplicates[:5])}")
        else:
            print(f"PASS workspace index ({len(workspaces)} workspaces, 0 duplicate sessions)")
        for workspace in workspaces.values():
            workspace_path = str(workspace.get("path", ""))
            compatibility_path = normalized(workspace_path).replace(
                "/local-data/accounts/.dsh-home/", "/"
            )
            if "/.dsh-home/" in compatibility_path:
                warnings.append(f"workspace uses compatibility link: {workspace_path}")

    if args.bili_config:
        path = args.bili_config.resolve()
        config = json.loads(path.read_text(encoding="utf-8"))
        expected_workspace = normalized(str(world / "bili-duty"))
        checks = (
            ("workspace", expected_workspace, lambda value: normalized(str(value)) == expected_workspace),
            ("headlessProfile", "bili-duty", lambda value: value == "bili-duty"),
            ("autoComment", False, lambda value: value is False),
            ("replyToComments", False, lambda value: value is False),
            ("dmMode", "off", lambda value: value == "off"),
        )
        for key, expected, predicate in checks:
            value = config.get(key)
            if predicate(value):
                print(f"PASS bili-duty {key}")
            else:
                failures.append(f"bili-duty {key} is {value!r}; expected {expected!r}")

    for message in warnings:
        print(f"WARN {message}")
    for message in failures:
        print(f"FAIL {message}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
