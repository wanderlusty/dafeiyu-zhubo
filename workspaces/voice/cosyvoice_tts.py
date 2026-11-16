"""Local CosyVoice3 zero-shot TTS for Xiao Bai. Run in the existing WSL CUDA venv."""

import argparse
import os
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--prompt-text', required=True)
    parser.add_argument('--text', required=True)
    parser.add_argument('--delivery', default='')
    parser.add_argument('--fp16', action='store_true', help='Test half precision without changing the live voice service')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    for path in (args.repo, args.model, args.reference):
        if not path.exists():
            raise FileNotFoundError(path)
    if not args.text.strip() or not args.prompt_text.strip():
        raise ValueError('Text and prompt transcript must be nonempty')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)

    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.chdir(args.repo)
    sys.path[:0] = [str(args.repo), str(args.repo / 'third_party' / 'Matcha-TTS')]
    # WeText tries to download its normalizer at model startup. Keep this
    # local prototype offline; the script receives already prepared text.
    sys.modules['wetext'] = None

    import numpy as np
    import soundfile as sf
    import torch
    from cosyvoice.cli.cosyvoice import AutoModel

    torch.set_num_threads(4)
    voice = AutoModel(model_dir=str(args.model), fp16=args.fp16, load_trt=False, load_vllm=False)
    prompt = 'You are a helpful assistant.<|endofprompt|>' + args.prompt_text
    with torch.inference_mode():
        if args.delivery:
            instruction = 'You are a helpful assistant. ' + args.delivery + '<|endofprompt|>'
            generated = voice.inference_instruct2(
                args.text, instruction, str(args.reference), stream=False,
                text_frontend=False
            )
        else:
            generated = voice.inference_zero_shot(
                args.text, prompt, str(args.reference), stream=False,
                text_frontend=False
            )
        chunks = [result['tts_speech'].detach().cpu().numpy().reshape(-1)
                  for result in generated]
    if not chunks:
        raise RuntimeError('CosyVoice returned no audio')
    audio = np.concatenate(chunks)
    if not np.isfinite(audio).all() or len(audio) < voice.sample_rate // 10:
        raise RuntimeError('CosyVoice returned invalid audio')
    peak = float(np.max(np.abs(audio)))
    if peak > 0.98:
        audio *= 0.98 / peak
    sf.write(args.output, audio, voice.sample_rate, subtype='PCM_16')
    print(f'{args.output} | {len(audio) / voice.sample_rate:.2f}s | {voice.sample_rate}Hz')
    import resource
    print(f'precision={"fp16" if args.fp16 else "fp32"} peak_rss_mb={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} '
          f'cuda_peak_reserved_mb={torch.cuda.max_memory_reserved() / 1024**2:.0f}', flush=True)


if __name__ == '__main__':
    main()
