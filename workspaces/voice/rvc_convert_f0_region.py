"""Run RVC once while correcting an F0 octave error inside a named time span.

The correction enters RVC synthesis before audio generation, so it does not
paste or pitch-shift an already synthesized phrase. For local experiments only.
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2] / "vendor" / "rvc-official"
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from infer.cli import main as rvc_main  # noqa: E402
from infer.vc.pipeline import Pipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--f0-region-start", type=float, required=True)
    parser.add_argument("--f0-region-end", type=float, required=True)
    parser.add_argument("--f0-region-semitones", type=float, required=True)
    parser.add_argument("--f0-region-fade", type=float, default=0.08)
    local, rest = parser.parse_known_args()
    if not (0 <= local.f0_region_start < local.f0_region_end < 45):
        raise ValueError("Invalid F0 correction span")
    if not (-12 <= local.f0_region_semitones <= 12):
        raise ValueError("F0 correction must be within one octave")
    if not 0 < local.f0_region_fade <= 0.25:
        raise ValueError("Invalid F0 ramp")

    original_get_f0 = Pipeline.get_f0

    def corrected_get_f0(self, audio, p_len, f0_up_key, f0_method):
        _, f0 = original_get_f0(self, audio, p_len, f0_up_key, f0_method)
        f0 = f0.copy()
        times = np.arange(len(f0)) * self.window / self.sr - self.t_pad / self.sr
        start, end, fade = (local.f0_region_start, local.f0_region_end,
                            local.f0_region_fade)
        amount = np.zeros(len(f0), dtype="float32")
        rising = (times >= start) & (times < start + fade)
        middle = (times >= start + fade) & (times <= end - fade)
        falling = (times > end - fade) & (times <= end)
        amount[rising] = (times[rising] - start) / fade
        amount[middle] = 1
        amount[falling] = (end - times[falling]) / fade
        f0 *= np.exp2(local.f0_region_semitones * amount / 12)

        f0_min, f0_max = 50, 1100
        mel_min = 1127 * np.log(1 + f0_min / 700)
        mel_max = 1127 * np.log(1 + f0_max / 700)
        mel = 1127 * np.log(1 + f0 / 700)
        mel = np.where(mel > 0, (mel - mel_min) * 254 / (mel_max - mel_min) + 1, 1)
        coarse = np.rint(np.clip(mel, 1, 255)).astype(np.int32)
        print(f"F0 correction {start:.2f}-{end:.2f}s {local.f0_region_semitones:+.0f}st; "
              f"{int(np.count_nonzero(amount))} frames", flush=True)
        return coarse, f0

    Pipeline.get_f0 = corrected_get_f0
    return rvc_main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
