"""Invoke the official RVC CLI from outside its repository."""

import os
import sys
from pathlib import Path


repo = Path(__file__).resolve().parents[2] / 'vendor' / 'rvc-official'
os.chdir(repo)
sys.path.insert(0, str(repo))

from infer.cli import main  # noqa: E402


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
