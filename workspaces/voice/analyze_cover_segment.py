"""Summarize source and converted vocal pitch/level around a reported defect."""

import argparse
import json
from pathlib import Path

import librosa
import numpy as np


def measure(path: Path, start: float, end: float) -> dict:
    audio, sr = librosa.load(path, sr=16000, mono=True, offset=start, duration=end - start)
    if len(audio) < sr:
        raise ValueError(f"Not enough audio: {path}")
    hop = 256
    f0 = librosa.yin(audio, fmin=80, fmax=900, sr=sr, hop_length=hop)
    rms = librosa.feature.rms(y=audio, hop_length=hop)[0]
    n = min(len(f0), len(rms))
    mask = rms[:n] > max(0.01, float(np.quantile(rms[:n], 0.5)))
    voiced = f0[:n][mask]
    jumps = np.abs(12 * np.diff(np.log2(voiced))) if len(voiced) > 1 else np.array([])
    return {"rms": round(float(np.sqrt(np.mean(audio**2))), 4),
            "peak": round(float(np.max(np.abs(audio))), 4),
            "pitch_median_hz": round(float(np.median(voiced)), 1),
            "pitch_p90_hz": round(float(np.quantile(voiced, 0.9)), 1),
            "large_pitch_jumps": int(np.count_nonzero(jumps > 4))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-vocals", type=Path, required=True)
    parser.add_argument("--converted-vocals", type=Path, required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()
    rows = []
    for second in range(args.start, args.end):
        rows.append({"second": second,
                     "source": measure(args.source_vocals, second, second + 1),
                     "converted": measure(args.converted_vocals, second, second + 1)})
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
