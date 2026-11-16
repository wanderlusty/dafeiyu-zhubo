"""Estimate an RVC pitch shift from separated vocals and a preferred clip.

This is a coarse automatic choice for live requests, not a listening review.
"""

import argparse
import json
import math
from pathlib import Path

import librosa
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "outputs/covers/qingming-bili-v2-chorus-p8/stems/htdemucs/source-clip/vocals.wav"


def median_pitch(path: Path) -> float:
    audio, sr = librosa.load(path, sr=16000, mono=True)
    if len(audio) < sr * 10:
        raise ValueError("Too little audio for pitch estimate")
    # Analyze a bounded set of frames to keep this usable during a live request.
    audio = audio[: sr * 35]
    hop = 512
    f0 = librosa.yin(audio, fmin=75, fmax=650, sr=sr, frame_length=2048, hop_length=hop)
    rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=hop)[0]
    count = min(len(f0), len(rms))
    voiced = f0[:count][rms[:count] > max(0.012, float(np.quantile(rms[:count], 0.55)))]
    voiced = voiced[np.isfinite(voiced)]
    if len(voiced) < 30:
        raise ValueError("Could not estimate sung pitch")
    return float(np.median(voiced))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vocals", type=Path)
    args = parser.parse_args()
    source = median_pitch(args.vocals)
    reference = median_pitch(REFERENCE)
    target = reference * 2 ** (8 / 12)
    shift = round(12 * math.log2(target / source))
    # The voice model is trained on speech; extreme shifts often sound metallic.
    shift = min(10, max(4, shift))
    print(json.dumps({"pitch": shift, "source_median_hz": source,
                      "reference_median_hz": reference, "target_hz": target}))


if __name__ == "__main__":
    main()
