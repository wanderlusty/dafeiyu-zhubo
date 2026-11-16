"""Make a local pitch-region comparison from an existing RVC cover.

This only edits the isolated vocal. The backing and other vocal phrases retain
the original cover settings. It is an audition tool, not a live auto-repair.
"""

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parents[2]


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-name", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--end", type=float, required=True)
    parser.add_argument("--semitones", type=int, required=True)
    parser.add_argument("--fade", type=float, default=0.12)
    args = parser.parse_args()
    if not (0 < args.start < args.end < 45 and 0.03 <= args.fade <= 0.3):
        raise ValueError("Invalid region or fade")
    if args.semitones not in (-12, 12):
        raise ValueError("Only octave comparisons are supported")
    base = ROOT / "outputs" / "covers" / args.base_name
    output = ROOT / "outputs" / "covers" / args.name
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    settings = json.loads((base / "settings.json").read_text(encoding="utf-8"))
    source = base / "xiaobai-vocals.wav"
    backing = base / "stems" / "htdemucs" / "source-clip" / "no_vocals.wav"
    shifted = output / "pitch-shifted.wav"
    factor = 2 ** (args.semitones / 12)
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-af", f"rubberband=pitch={factor:.8f}:formant=preserved:pitchq=quality",
        "-c:a", "pcm_s16le", str(shifted))
    original_audio, sr = sf.read(source, dtype="float32")
    shifted_audio, shift_sr = sf.read(shifted, dtype="float32")
    if sr != shift_sr or abs(len(original_audio) - len(shifted_audio)) > sr // 10:
        raise RuntimeError("Pitch shift changed duration or sample rate")
    if len(shifted_audio) < len(original_audio):
        shifted_audio = np.pad(shifted_audio, (0, len(original_audio) - len(shifted_audio)))
    else:
        shifted_audio = shifted_audio[:len(original_audio)]
    left = round(args.start * sr)
    right = round(args.end * sr)
    fade = round(args.fade * sr)
    weight = np.zeros(len(original_audio), dtype="float32")
    weight[left:right] = 1
    weight[left:left + fade] = np.linspace(0, 1, fade, dtype="float32")
    weight[right - fade:right] = np.linspace(1, 0, fade, dtype="float32")
    repaired = (original_audio * (1 - weight) + shifted_audio * weight).astype("float32")
    vocal_path = output / "xiaobai-vocals.wav"
    sf.write(vocal_path, repaired, sr, subtype="PCM_16")
    mix = output / "xiaobai-cover.mp3"
    backing_pitch = settings["backing_pitch"]
    backing_shift = (f"rubberband=pitch={2 ** (backing_pitch / 12):.8f},"
                     if backing_pitch else "")
    graph = (
        "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,"
        f"highpass=f=95,lowpass=f=12500,volume={settings['vocal_gain']}[v];"
        "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,"
        f"{backing_shift}volume={settings['backing_gain']}[b];"
        "[v][b]amix=inputs=2:duration=longest:normalize=0,"
        "afade=t=in:st=0:d=0.4,"
        f"afade=t=out:st={max(0, settings['duration'] - 0.7):.2f}:d=0.7,"
        "alimiter=limit=0.9[m]"
    )
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(vocal_path),
        "-i", str(backing), "-filter_complex", graph, "-map", "[m]", "-c:a",
        "libmp3lame", "-b:a", "192k", str(mix))
    (output / "settings.json").write_text(json.dumps({**settings,
        "local_pitch_region": {"start": args.start, "end": args.end,
                               "semitones": args.semitones, "fade": args.fade},
        "review_status": "unreviewed", "result": str(mix)}, ensure_ascii=False,
        indent=2), encoding="utf-8")
    print(mix)


if __name__ == "__main__":
    main()
