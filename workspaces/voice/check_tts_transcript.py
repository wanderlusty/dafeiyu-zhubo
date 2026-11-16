"""Check whether voice conversion preserved the spoken words."""

import argparse
import json
import os


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--segments', action='store_true', help='Print short timestamped excerpts')
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    import whisper

    model = whisper.load_model('base', device='cpu')
    for name in args.files:
        result = model.transcribe(name, language='zh', fp16=False)
        if args.segments:
            rows = [{'start': round(s['start'], 1), 'end': round(s['end'], 1),
                     'text': s['text'].strip()} for s in result['segments']]
            print(json.dumps({'file': name, 'segments': rows}, ensure_ascii=False))
        else:
            print(json.dumps({'file': name, 'text': result['text'].strip()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
