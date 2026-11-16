"""Compose and convert a new Xiao Bai song from any topic or original lyrics."""

import argparse
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]


def service_ready(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--topic", help="Theme for a newly composed Mandarin song")
    source.add_argument("--lyrics-file", type=Path, help="Your original UTF-8 lyrics")
    parser.add_argument("--name", help="ASCII slug for this song")
    parser.add_argument("--prompt", help="Music style and arrangement")
    parser.add_argument("--duration", type=int, default=40)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--bpm", type=int)
    parser.add_argument("--keyscale")
    parser.add_argument("--timesignature", choices=["2/4", "3/4", "4/4", "6/8"])
    args = parser.parse_args()
    slug = args.name or datetime.now().strftime("song-%Y%m%d-%H%M%S")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,49}", slug):
        raise ValueError("--name must be a short lowercase ASCII slug")
    if service_ready(7391) or service_ready(7392):
        raise RuntimeError("Voice servers are using this GPU; prepare songs only while the live stage is idle and voice servers are stopped")
    name = f"xiaobai-song-source-{slug}"
    command = [sys.executable, str(PROJECT / "workspaces" / "voice" / "generate_song.py"),
               "--name", name, "--duration", str(args.duration)]
    if args.topic:
        command += ["--topic", args.topic]
    else:
        command += ["--lyrics-file", str(args.lyrics_file.resolve(strict=True))]
    for key in ("prompt", "bpm", "keyscale", "timesignature", "seed"):
        value = getattr(args, key)
        if value is not None:
            command += [f"--{key}", str(value)]
    subprocess.run(command, check=True)
    subprocess.run([sys.executable, str(PROJECT / "workspaces" / "voice" / "finish_song.py"),
                    "--name", name], check=True)
    output = PROJECT / "outputs" / f"xiaobai-song-rvc-{slug}.mp3"
    if not output.is_file():
        raise FileNotFoundError(output)
    print(output)


if __name__ == "__main__":
    main()
