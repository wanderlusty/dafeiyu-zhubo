"""Transcribe user-provided new voice samples for local training-data review."""

import json
import os
import argparse
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "声音"
OUTPUT = PROJECT / "outputs" / "voice-source-audit"
OLD_NAMES = {f"{number}.mp3" for number in range(1, 8)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", action="store_true", help="Audit the seven original cleaned WAV files")
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    import torch
    import whisper

    torch.set_num_threads(4)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    model = whisper.load_model("base", device="cpu")
    if args.old:
        paths = sorted((PROJECT / "workspaces" / "voice" / "data" / "rvc-clean").glob("*.wav"))
    else:
        paths = sorted(path for path in SOURCE.glob("*.mp3")
                       if path.name not in OLD_NAMES and "彩虹" not in path.name)
    for number, path in enumerate(paths, 1):
        target = OUTPUT / f"{'old' if args.old else 'source'}-{number}.json"
        if target.exists():
            data = json.loads(target.read_text(encoding="utf-8"))
            if data.get("source") == str(path):
                print(f"cached {number}: {path.name}", flush=True)
                continue
        result = model.transcribe(str(path), language="zh", fp16=False,
                                  condition_on_previous_text=False)
        segments = [{
            "start": round(segment["start"], 2),
            "end": round(segment["end"], 2),
            "text": segment["text"].strip(),
            "no_speech_prob": round(segment["no_speech_prob"], 3),
        } for segment in result["segments"]]
        data = {"source": str(path), "segments": segments}
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        print(f"{number}/{len(paths)} {path.name}: {len(segments)} segments", flush=True)


if __name__ == "__main__":
    main()
