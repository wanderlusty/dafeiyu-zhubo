"""Make a local Xiao Bai cover preview from a user-supplied audio file.

Run in the WSL CUDA voice environment. This never uploads or broadcasts audio.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf


PROJECT = Path(__file__).resolve().parents[2]
RVC_CONFIG = PROJECT / "workspaces" / "voice" / "rvc_config.json"


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def convert_chunked(vocals: Path, converted: Path, output: Path, args: argparse.Namespace,
                    settings: dict) -> None:
    """Keep RVC inference bounded for full songs and blend neighboring chunks."""
    audio, source_rate = sf.read(vocals, dtype="float32", always_2d=True)
    chunk_frames = round(args.rvc_chunk_seconds * source_rate)
    overlap_frames = round(0.25 * source_rate)
    count = (len(audio) + chunk_frames - 1) // chunk_frames
    chunk_dir = output / "rvc-chunks"
    chunk_dir.mkdir(exist_ok=True)
    pieces = []
    target_rate = None

    for index in range(count):
        first = max(0, index * chunk_frames - overlap_frames)
        last = min(len(audio), (index + 1) * chunk_frames + overlap_frames)
        source_piece = audio[first:last]
        if float(np.sqrt(np.mean(source_piece * source_piece))) < 0.003:
            pieces.append((first, last, None))
            continue
        chunk_input = chunk_dir / f"input-{index:03d}.wav"
        chunk_output = chunk_dir / f"output-{index:03d}.wav"
        sf.write(chunk_input, source_piece, source_rate, subtype="PCM_16")
        run(sys.executable, str(PROJECT / "workspaces" / "voice" / "rvc_convert.py"),
            "--model", settings["model"], "--index", settings["index"],
            "--index-rate", str(args.index_rate), "--pitch", str(args.pitch),
            "--protect", str(args.protect), "--rms-mix-rate", str(args.rms_mix_rate),
            "--f0-method", args.f0_method, "--input", str(chunk_input),
            "--output", str(chunk_output))
        result, rate = sf.read(chunk_output, dtype="float32", always_2d=True)
        if result.shape[1] != 1:
            raise RuntimeError("RVC chunk output is not mono")
        if target_rate is not None and target_rate != rate:
            raise RuntimeError("RVC chunk sample rates differ")
        target_rate = rate
        pieces.append((first, last, result[:, 0]))
        print(f"RVC chunk {index + 1}/{count} ready", flush=True)

    if target_rate is None:
        raise RuntimeError("RVC found no singing in any chunk")
    output_length = round(len(audio) * target_rate / source_rate)
    combined = np.zeros(output_length, dtype="float32")
    weight_sum = np.zeros(output_length, dtype="float32")
    fade_length = round(2 * overlap_frames * target_rate / source_rate)
    for index, (first, last, result) in enumerate(pieces):
        start = round(first * target_rate / source_rate)
        end = min(output_length, round(last * target_rate / source_rate))
        length = end - start
        if result is None:
            result = np.zeros(length, dtype="float32")
        elif abs(len(result) - length) > round(0.15 * target_rate):
            raise RuntimeError(f"RVC chunk {index + 1} has unexpected duration")
        elif len(result) < length:
            result = np.pad(result, (0, length - len(result)), mode="edge")
        else:
            result = result[:length]
        weights = np.ones(length, dtype="float32")
        if index > 0:
            width = min(fade_length, length)
            weights[:width] *= np.linspace(0, 1, width, dtype="float32")
        if index + 1 < count:
            width = min(fade_length, length)
            weights[-width:] *= np.linspace(1, 0, width, dtype="float32")
        combined[start:end] += result * weights
        weight_sum[start:end] += weights
    combined /= np.maximum(weight_sum, 1e-6)
    sf.write(converted, combined, target_rate, subtype="PCM_16")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Local MP3/WAV/FLAC/etc.")
    parser.add_argument("--name", required=True, help="Short ASCII output name")
    parser.add_argument("--start", type=float, default=0, help="Start time in seconds")
    parser.add_argument("--duration", type=float, default=35, help="Preview duration in seconds (default: 35)")
    parser.add_argument("--allow-long-experiment", action="store_true",
                        help="Allow an unreviewed experiment longer than 45 seconds")
    parser.add_argument("--pitch", type=int, required=True,
                        help="RVC pitch shift in semitones; choose deliberately for each song")
    parser.add_argument("--vocal-post-pitch", type=int, default=0,
                        help="Shift converted vocal after RVC; see --post-formant (default: 0)")
    parser.add_argument("--post-formant", choices=["preserved", "shifted"], default="preserved",
                        help="Formant behavior for the post-RVC pitch shift (default: preserved)")
    parser.add_argument("--backing-pitch", type=int,
                        help="Backing track shift in semitones (default: follow --pitch)")
    parser.add_argument("--allow-nonharmonic-experiment", action="store_true",
                        help="Allow vocal and backing to end in different keys for local comparison")
    parser.add_argument("--rvc-config", type=Path, default=RVC_CONFIG)
    parser.add_argument("--index-rate", type=float, default=0.10)
    parser.add_argument("--protect", type=float, default=0.10)
    parser.add_argument("--rms-mix-rate", type=float, default=0.25)
    parser.add_argument("--rvc-chunk-seconds", type=int, default=30,
                        help="RVC inference chunk length; 45 processes a 35-second clip in one pass")
    parser.add_argument("--f0-method", choices=["rmvpe", "fcpe", "pm"], default="rmvpe",
                        help="Pitch tracker used by RVC (default: rmvpe)")
    parser.add_argument("--vocal-gain", type=float, default=1.15)
    parser.add_argument("--backing-gain", type=float, default=0.62)
    args = parser.parse_args()
    if args.backing_pitch is None:
        args.backing_pitch = args.pitch
    source = args.input.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", args.name):
        raise ValueError("--name must be a short lowercase ASCII slug")
    if args.start < 0 or not (5 <= args.duration <= 600):
        raise ValueError("Invalid start/duration")
    if args.duration > 45 and not args.allow_long_experiment:
        raise ValueError("Only short previews are approved; use --allow-long-experiment for local testing")
    if not (0 <= args.index_rate <= 1):
        raise ValueError("--index-rate must be between 0 and 1")
    if not (0 <= args.protect <= 0.5 and 0 <= args.rms_mix_rate <= 1):
        raise ValueError("Invalid RVC protection or RMS mix rate")
    if not 15 <= args.rvc_chunk_seconds <= 45:
        raise ValueError("RVC chunk length must be 15 to 45 seconds")
    if not (0 < args.vocal_gain <= 3 and 0 < args.backing_gain <= 3):
        raise ValueError("Invalid gain")
    if not (-12 <= args.pitch <= 12 and -12 <= args.vocal_post_pitch <= 12
            and -12 <= args.backing_pitch <= 12):
        raise ValueError("Pitch shifts must be within -12 to 12 semitones")
    if ((args.pitch + args.vocal_post_pitch - args.backing_pitch) % 12 != 0
            and not args.allow_nonharmonic_experiment):
        raise ValueError("Vocal and backing would end in different keys; adjust --vocal-post-pitch or --backing-pitch")

    settings = json.loads(args.rvc_config.resolve().read_text(encoding="utf-8"))
    for key in ("model", "index"):
        if not Path(settings[key]).is_file():
            raise FileNotFoundError(settings[key])

    output = PROJECT / "outputs" / "covers" / args.name
    output.mkdir(parents=True, exist_ok=True)
    metadata_path = output / "settings.json"
    requested = {
        "source": str(source), "start": args.start, "duration": args.duration,
        "pitch": args.pitch, "index_rate": args.index_rate,
        "protect": args.protect, "rms_mix_rate": args.rms_mix_rate,
        "vocal_gain": args.vocal_gain, "backing_gain": args.backing_gain,
        "backing_pitch": args.backing_pitch,
        "vocal_post_pitch": args.vocal_post_pitch,
        "post_formant": args.post_formant,
        "rvc_model": settings["model"], "rvc_index": settings["index"],
        "rvc_chunk_seconds": args.rvc_chunk_seconds,
        "f0_method": args.f0_method,
    }
    previous = {}
    if metadata_path.exists():
        previous = json.loads(metadata_path.read_text(encoding="utf-8"))
        if any(previous.get(key, 0 if key == "vocal_post_pitch" else
                            "preserved" if key == "post_formant" else
                            "rmvpe" if key == "f0_method" else None) != value
               for key, value in requested.items()):
            raise ValueError("Output name already belongs to another set of cover settings")
    clip = output / "source-clip.wav"
    stems = output / "stems"
    vocals = stems / "htdemucs" / "source-clip" / "vocals.wav"
    backing = stems / "htdemucs" / "source-clip" / "no_vocals.wav"
    converted = output / "xiaobai-vocals.wav"
    mix = output / "xiaobai-cover.mp3"

    if not clip.is_file():
        run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(args.start), "-t", str(args.duration), "-i", str(source),
            "-vn", "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(clip))
    if not vocals.is_file() or not backing.is_file():
        run(sys.executable, "-m", "demucs", "-n", "htdemucs", "--two-stems", "vocals",
            "-o", str(stems), str(clip))
    vocal_audio, _ = sf.read(vocals, dtype="float32")
    vocal_rms = float(np.sqrt(np.mean(vocal_audio * vocal_audio)))
    if vocal_rms < 0.005:
        raise RuntimeError("This excerpt has almost no separated singing; choose another start time")

    if not converted.is_file():
        convert_chunked(vocals, converted, output, args, settings)
    if not mix.is_file():
        vocal_shift = (f"rubberband=pitch={2 ** (args.vocal_post_pitch / 12):.8f}:"
                       f"formant={args.post_formant}:pitchq=quality,"
                       if args.vocal_post_pitch else "")
        backing_shift = (f"rubberband=pitch={2 ** (args.backing_pitch / 12):.8f},"
                         if args.backing_pitch else "")
        filter_graph = (
            f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"{vocal_shift}highpass=f=95,lowpass=f=12500,volume={args.vocal_gain}[v];"
            f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"{backing_shift}volume={args.backing_gain}[b];"
            f"[v][b]amix=inputs=2:duration=longest:normalize=0,"
            f"afade=t=in:st=0:d=0.4,"
            f"afade=t=out:st={max(0, args.duration - 0.7):.2f}:d=0.7,"
            "alimiter=limit=0.9[m]"
        )
        run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(converted), "-i", str(backing), "-filter_complex", filter_graph,
            "-map", "[m]", "-c:a", "libmp3lame", "-b:a", "192k", str(mix))
    metadata_path.write_text(json.dumps({**requested,
        "vocal_rms": vocal_rms, "result": str(mix),
        "review_status": previous.get("review_status", "unreviewed"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(mix)


if __name__ == "__main__":
    main()
