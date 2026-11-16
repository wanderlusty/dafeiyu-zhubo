"""Extract vocals from newly supplied clips, preserving every source file."""

import json
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "声音"
STEMS = PROJECT / "workspaces" / "voice" / "data" / "rvc-new-stems"
CLEAN = PROJECT / "workspaces" / "voice" / "data" / "rvc-new-clean"
OLD_NAMES = {f"{number}.mp3" for number in range(1, 8)}


def main() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)
    paths = sorted(path for path in SOURCE.glob("*.mp3")
                   if path.name not in OLD_NAMES and "彩虹" not in path.name)
    mapping = []
    for number, source in enumerate(paths, 1):
        dest = CLEAN / f"new-{number:02d}.wav"
        stem = STEMS / "htdemucs" / source.stem / "vocals.wav"
        mapping.append({"source": str(source), "vocal": str(dest)})
        if dest.is_file():
            print(f"cached {number}/{len(paths)} {source.name}", flush=True)
            continue
        if not stem.is_file():
            subprocess.run(
                [sys.executable, "-m", "demucs", "-n", "htdemucs", "--two-stems",
                 "vocals", "--device", "cpu", "-o", str(STEMS), str(source)],
                check=True,
            )
        shutil.copy2(stem, dest)
        print(f"cleaned {number}/{len(paths)} {source.name} -> {dest}", flush=True)
    (CLEAN / "source-map.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
