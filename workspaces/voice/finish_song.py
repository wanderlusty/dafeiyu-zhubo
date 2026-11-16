"""Separate, voice-convert and remix the locally generated Xiao Bai song."""

import json
import argparse
import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
STEMS = PROJECT / "workspaces" / "voice" / "song-stems"


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="xiaobai-song-source-v2")
    args = parser.parse_args()
    if not args.name.startswith("xiaobai-song-source") or "/" in args.name or "\\" in args.name:
        raise ValueError("Invalid source name")
    source = PROJECT / "outputs" / f"{args.name}.flac"
    if not source.is_file():
        raise FileNotFoundError(source)
    suffix = args.name.removeprefix("xiaobai-song-source").lstrip("-")
    tag = f"-{suffix}" if suffix else ""
    vocals = STEMS / "htdemucs" / args.name / "vocals.wav"
    backing = STEMS / "htdemucs" / args.name / "no_vocals.wav"
    converted = PROJECT / "outputs" / f"xiaobai-song-rvc-vocals{tag}.wav"
    mix = PROJECT / "outputs" / f"xiaobai-song-rvc{tag}.mp3"
    settings = json.loads((PROJECT / "workspaces" / "voice" / "rvc_config.json").read_text(encoding="utf-8"))
    for key in ("model", "index"):
        if not Path(settings[key]).is_file():
            raise FileNotFoundError(settings[key])
    if not vocals.is_file() or not backing.is_file():
        run(sys.executable, "-m", "demucs", "-n", "htdemucs", "--two-stems", "vocals",
            "-o", str(STEMS), str(source))
    # An earlier candidate had no actual singing. Refuse to remix a silent stem.
    import numpy as np
    import soundfile as sf
    vocal_audio, _ = sf.read(vocals, dtype="float32")
    vocal_rms = float(np.sqrt(np.mean(vocal_audio * vocal_audio)))
    print(f"vocal_rms={vocal_rms:.5f}")
    if vocal_rms < 0.01:
        raise RuntimeError("Separated vocal is too quiet to count as singing")
    if not converted.is_file():
        run(sys.executable, str(PROJECT / "workspaces" / "voice" / "rvc_convert.py"),
            "--model", settings["model"], "--index", settings["index"],
            "--index-rate", str(settings["index_rate"]),
            "--pitch", "0", "--f0-method", "rmvpe",
            "--input", str(vocals), "--output", str(converted))
    if not mix.is_file():
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(converted),
            "-i", str(backing), "-filter_complex",
            "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.1[v];"
            "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.55[b];"
            "[v][b]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.9[m]",
            "-map", "[m]", "-c:a", "libmp3lame", "-b:a", "192k", str(mix))
    print(mix)


if __name__ == "__main__":
    main()
