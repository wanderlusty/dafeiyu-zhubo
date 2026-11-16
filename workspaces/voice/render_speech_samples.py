"""Record a few ordinary Xiao Bai lines through the same local TTS+RVC service as the stage."""

import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs" / "speech-samples" / "2026-11-05"
FFMPEG = Path("D:/bilidown/resources/bin/ffmpeg.exe")
LINES = [
    ("chat", "刚才刷到一个海边的小视频，浪一下一下地拍过来，听着还挺治愈的。你今天过得怎么样？"),
    ("danmaku", "哎，这条弹幕我看见啦。你想听我唱歌？可以呀，给我一点时间找音源，做好就唱给你听。"),
    ("casual", "我刚刚想说什么来着……啊，对，今天别光顾着忙，记得吃饭，也记得抬头看看窗外。"),
]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, text in LINES:
        path = OUTPUT / f"xiaobai-{name}.mp3"
        request = urllib.request.Request(
            "http://127.0.0.1:7391/synthesize", method="POST",
            data=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.headers.get_content_type() != "audio/mpeg":
                raise RuntimeError(f"Unexpected audio response for {name}")
            audio = response.read(5_000_001)
        if not 10_000 < len(audio) < 5_000_000:
            raise RuntimeError(f"Invalid speech size for {name}")
        path.write_bytes(audio)
        subprocess.run([str(FFMPEG), "-v", "error", "-i", str(path), "-f", "null", "NUL"],
                       check=True, timeout=30)
        entries.append({"name": name, "text": text, "file": str(path), "bytes": len(audio)})
        print(f"{name}: {path} ({len(audio)} bytes)", flush=True)
    (OUTPUT / "manifest.json").write_text(
        json.dumps({"pipeline": "CosyVoice3 -> RVC -> MP3", "samples": entries},
                   ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
