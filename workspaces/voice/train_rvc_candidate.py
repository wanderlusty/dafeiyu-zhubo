"""Run a separate RVC candidate experiment from the screened local speech set."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
REPO = PROJECT / "vendor" / "rvc-official"
DATA = PROJECT / "workspaces" / "voice" / "data" / "rvc-v2-curated"
EXPERIMENT = "xiaobai_v2_curated"
STAGES = ["preprocess", "f0", "features", "filelist", "train", "index"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-stage", choices=STAGES, default="preprocess")
    parser.add_argument("--through-stage", choices=STAGES, default="index")
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()
    first = STAGES.index(args.from_stage)
    last = STAGES.index(args.through_stage)
    if first > last:
        raise ValueError("--from-stage follows --through-stage")
    if not (5 <= args.epochs <= 100):
        raise ValueError("Candidate training accepts 5 to 100 epochs")
    if not DATA.is_dir() or len(list(DATA.glob("*.wav"))) < 30:
        raise RuntimeError("The curated training set is missing or too small")
    os.chdir(REPO)
    os.environ["PYTHONPATH"] = str(REPO) + os.pathsep + os.environ.get("PYTHONPATH", "")
    python = sys.executable
    experiment = REPO / "logs" / EXPERIMENT
    experiment.mkdir(parents=True, exist_ok=True)
    calls = {
        "preprocess": [python, "-m", "train.preprocess", str(DATA), "40000", "8",
                       str(experiment), "False", "3.7"],
        "f0": [python, "-m", "train.dataset.extract_f0", "cuda", "1", "0", "0",
               str(experiment), "true"],
        "features": [python, "-m", "train.dataset.extract_hubert_feature", "cuda:0", "1",
                     "0", "0", str(experiment), "v2", "true"],
        "filelist": [python, str(PROJECT / "workspaces" / "voice" / "prepare_rvc_experiment.py"),
                     "--repo", str(REPO), "--name", EXPERIMENT],
        "train": [python, "-m", "train.train", "-e", EXPERIMENT, "-sr", "40k",
                  "-f0", "1", "-bs", "4", "-g", "0", "-te", str(args.epochs),
                  "-se", "10", "-pg", "assets/pretrained_v2/f0G40k.pth",
                  "-pd", "assets/pretrained_v2/f0D40k.pth", "-l", "0",
                  "-c", "0", "-sw", "1", "-v", "v2"],
        "index": [python, "-m", "train.train_index", EXPERIMENT, "v2",
                  "assets/indices", "8", "single"],
    }
    for stage in STAGES[first:last + 1]:
        print(f"STAGE {stage}", flush=True)
        subprocess.run(calls[stage], check=True)
        print(f"DONE {stage}", flush=True)


if __name__ == "__main__":
    main()
