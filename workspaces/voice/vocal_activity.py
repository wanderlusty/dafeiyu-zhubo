"""Check whether a separated song excerpt contains sustained singing."""

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vocals", type=Path)
    args = parser.parse_args()
    audio, rate = sf.read(args.vocals, dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    window = round(rate * 0.5)
    rms = np.array([np.sqrt(np.mean(mono[i:i + window] ** 2))
                    for i in range(0, len(mono), window) if len(mono[i:i + window]) >= window // 2])
    active = rms >= 0.01
    longest_quiet = 0
    current = 0
    for voiced in active:
        current = 0 if voiced else current + 1
        longest_quiet = max(longest_quiet, current)
    report = {
        "active_fraction": round(float(active.mean()), 3) if len(active) else 0,
        "longest_quiet_seconds": round(longest_quiet * 0.5, 1),
        "rms": round(float(np.sqrt(np.mean(mono * mono))), 4) if len(mono) else 0,
    }
    report["usable"] = report["active_fraction"] >= 0.6 and report["longest_quiet_seconds"] <= 8
    print(json.dumps(report))


if __name__ == "__main__":
    main()
