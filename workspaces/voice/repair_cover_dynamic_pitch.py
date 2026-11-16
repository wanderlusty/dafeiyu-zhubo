"""Create a local cover trial with smoothly varying post-RVC vocal pitch.

The input is one already synthesized vocal track. FFmpeg Rubber Band receives
time-varying pitch commands, then the whole vocal is mixed with the original
backing. There is no cut-and-paste of vocal audio.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

import soundfile as sf


ROOT = Path(__file__).resolve().parents[2]


def run(*command: str) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-name", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--rise-start", type=float, required=True)
    parser.add_argument("--rise-end", type=float, required=True)
    parser.add_argument("--fall-start", type=float, required=True)
    parser.add_argument("--fall-end", type=float, required=True)
    parser.add_argument("--semitones", type=float, default=12)
    args = parser.parse_args()
    if not (0 < args.rise_start < args.rise_end < args.fall_start < args.fall_end < 35):
        raise ValueError("Pitch envelope times must be ordered inside the clip")
    if not 0 < args.semitones <= 12:
        raise ValueError("Pitch change must be within one octave")

    base = ROOT / "outputs" / "covers" / args.base_name
    output = ROOT / "outputs" / "covers" / args.name
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    settings = json.loads((base / "settings.json").read_text(encoding="utf-8"))
    source = base / "xiaobai-vocals.wav"
    backing = base / "stems" / "htdemucs" / "source-clip" / "no_vocals.wav"
    commands = output / "pitch-commands.txt"
    lines = []
    for start, end, low, high in (
        (args.rise_start, args.rise_end, 0.0, args.semitones),
        (args.fall_start, args.fall_end, args.semitones, 0.0),
    ):
        steps = max(2, math.ceil((end - start) / 0.025))
        for i in range(steps + 1):
            t = start + (end - start) * i / steps
            semitones = low + (high - low) * i / steps
            lines.append(f"{t:.4f} rubberband@rb pitch {2 ** (semitones / 12):.8f};")
    commands.write_text("\n".join(lines) + "\n", encoding="ascii")

    vocal = output / "xiaobai-vocals.wav"
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-af", f"asendcmd=f={commands},rubberband@rb=pitch=1:formant=preserved:"
               "pitchq=quality:transients=smooth", "-c:a", "pcm_s16le", str(vocal))
    before, sr = sf.read(source, dtype="float32")
    after, after_sr = sf.read(vocal, dtype="float32")
    if sr != after_sr or abs(len(before) - len(after)) > sr // 20:
        raise RuntimeError("Post-processing changed the vocal duration or sample rate")

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
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(vocal),
        "-i", str(backing), "-filter_complex", graph, "-map", "[m]", "-c:a",
        "libmp3lame", "-b:a", "192k", str(mix))
    (output / "settings.json").write_text(json.dumps({**settings,
        "dynamic_pitch": {"rise_start": args.rise_start, "rise_end": args.rise_end,
                          "fall_start": args.fall_start, "fall_end": args.fall_end,
                          "semitones": args.semitones},
        "review_status": "unreviewed", "result": str(mix)}, ensure_ascii=False,
        indent=2), encoding="utf-8")
    print(mix)


if __name__ == "__main__":
    main()
