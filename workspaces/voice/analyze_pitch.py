"""Compare an audio excerpt's pitch range with the RVC training data."""

import argparse
from pathlib import Path

import librosa
import numpy as np


PROJECT = Path(__file__).resolve().parents[2]
F0_DIR = PROJECT / "vendor" / "rvc-official" / "logs" / "xiaobai_v1" / "2b-f0nsf"


def summarize(name: str, values: np.ndarray) -> None:
    values = np.asarray(values)
    values = values[np.isfinite(values) & (values > 50) & (values < 2000)]
    if len(values) == 0:
        print(name, "no voiced frames")
        return
    print(name, "frames", len(values), "Hz p10/p50/p90/p99", np.percentile(values, [10, 50, 90, 99]).round(1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    training = np.concatenate([np.load(path) for path in F0_DIR.glob("*.npy")])
    summarize("xiaobai training", training)
    for path in args.files:
        audio, sr = librosa.load(path, sr=16000, mono=True)
        f0 = librosa.yin(audio, fmin=65, fmax=1000, sr=sr, frame_length=2048, hop_length=256)
        power = librosa.feature.rms(y=audio, frame_length=2048, hop_length=256)[0]
        summarize(path.name, f0[power[:len(f0)] > np.percentile(power, 35)])


if __name__ == "__main__":
    main()
