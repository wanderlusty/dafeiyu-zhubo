"""Print half-second vocal pitch medians for a cover's source and RVC outputs."""

import argparse
from pathlib import Path

import numpy as np
import parselmouth


def contour(path: Path, start: float, end: float) -> np.ndarray:
    sound = parselmouth.Sound(str(path)).extract_part(from_time=start, to_time=end,
                                                      preserve_times=False)
    pitch = sound.to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=1000)
    return pitch.selected_array["frequency"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--end", type=float, default=35)
    parser.add_argument("--step", type=float, default=0.5)
    args = parser.parse_args()
    tracks = [contour(path, args.start, args.end) for path in args.files]
    print("time\t" + "\t".join(path.stem for path in args.files))
    for index in range(round((args.end - args.start) / args.step)):
        first = round(index * args.step / 0.01)
        last = round((index + 1) * args.step / 0.01)
        values = []
        for track in tracks:
            voiced = track[first:last]
            voiced = voiced[voiced > 0]
            values.append(f"{np.median(voiced):.0f}" if len(voiced) >= 5 else "-")
        print(f"{args.start + index * args.step:.1f}\t" + "\t".join(values))


if __name__ == "__main__":
    main()
