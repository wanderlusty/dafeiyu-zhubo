"""Compare short-window vocal energy around a sung phrase."""

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--end", type=float, required=True)
    parser.add_argument("--step", type=float, default=0.05)
    args = parser.parse_args()
    tracks = [sf.read(path, dtype="float32") for path in args.files]
    print("time\t" + "\t".join(path.parent.parent.name for path in args.files))
    for t in np.arange(args.start, args.end, args.step):
        values = []
        for audio, rate in tracks:
            part = audio[round(t * rate):round((t + args.step) * rate)]
            values.append(f"{np.sqrt(np.mean(part * part)):.3f}")
        print(f"{t:.2f}\t" + "\t".join(values))


if __name__ == "__main__":
    main()
