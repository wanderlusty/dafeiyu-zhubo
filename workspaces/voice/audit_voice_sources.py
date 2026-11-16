"""Summarize new local voice references without changing the originals."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "声音"
OLD_NAMES = {f"{number}.mp3" for number in range(1, 8)}


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,bit_rate:stream=codec_name,sample_rate,channels",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    audio = next((stream for stream in data.get("streams", [])
                  if stream.get("codec_name")), {})
    return {
        "name": path.name,
        "size_mb": round(path.stat().st_size / 1024**2, 2),
        "duration_sec": round(float(data["format"]["duration"]), 1),
        "bitrate_kbps": round(int(data["format"].get("bit_rate", 0)) / 1000),
        "codec": audio.get("codec_name"),
        "sample_rate": audio.get("sample_rate"),
        "channels": audio.get("channels"),
    }


def main() -> None:
    for path in sorted(ROOT.glob("*.mp3")):
        if path.name in OLD_NAMES or "彩虹" in path.name:
            continue
        print(json.dumps(probe(path), ensure_ascii=False))


if __name__ == "__main__":
    main()
