"""Prepare the single-speaker RVC v2/40k file list from completed feature extraction."""

import argparse
import json
import random
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.name):
        raise ValueError('Invalid experiment name')
    repo = args.repo.resolve(strict=True)
    experiment = repo / 'logs' / args.name
    paths = {
        'wav': experiment / '0_gt_wavs',
        'f0': experiment / '2a_f0',
        'f0nsf': experiment / '2b-f0nsf',
        'feature': experiment / '3_feature768',
    }
    names = sorted(p.stem for p in paths['wav'].glob('*.wav'))
    if len(names) < 10:
        raise ValueError(f'Only {len(names)} training clips found')
    records = []
    for name in names:
        files = [
            paths['wav'] / f'{name}.wav',
            paths['feature'] / f'{name}.npy',
            paths['f0'] / f'{name}.wav.npy',
            paths['f0nsf'] / f'{name}.wav.npy',
        ]
        for file in files:
            if not file.is_file():
                raise FileNotFoundError(file)
        records.append('|'.join(str(file) for file in files) + '|0')
    mute = repo / 'logs' / 'mute'
    mute_files = [
        mute / '0_gt_wavs' / 'mute40k.wav',
        mute / '3_feature768' / 'mute.npy',
        mute / '2a_f0' / 'mute.wav.npy',
        mute / '2b-f0nsf' / 'mute.wav.npy',
    ]
    for file in mute_files:
        if not file.is_file():
            raise FileNotFoundError(file)
    records += ['|'.join(str(file) for file in mute_files) + '|0'] * 2
    random.Random(1234).shuffle(records)
    config = json.loads((repo / 'configs' / 'v1' / '40k.json').read_text(encoding='utf-8'))
    config['train']['batch_size'] = 4
    (experiment / 'config.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    (experiment / 'filelist.txt').write_text('\n'.join(records) + '\n', encoding='utf-8')
    print(f'{len(names)} clips, {len(records)} filelist entries: {experiment}')


if __name__ == '__main__':
    main()
