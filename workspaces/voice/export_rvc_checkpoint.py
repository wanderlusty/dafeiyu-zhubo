"""Export a small inference weight from an RVC training checkpoint."""

import argparse
import os
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    os.chdir(args.repo)
    sys.path.insert(0, str(args.repo))
    from train.process_ckpt import extract_small_model

    result = extract_small_model(str(args.checkpoint), args.name, '40k', 1, '', 'v2')
    print(result)
    output = args.repo / 'assets' / 'weights' / f'{args.name}.pth'
    if not output.is_file() or output.stat().st_size < 1_000_000:
        raise RuntimeError(f'Export failed: {output}')
    print(output)


if __name__ == '__main__':
    main()
