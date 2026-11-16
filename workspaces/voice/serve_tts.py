"""Loopback CosyVoice3 service for the local Xiao Bai stage."""

import argparse
import io
import json
import os
import subprocess
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    config_path = parser.parse_args().config
    config = json.loads(config_path.read_text(encoding='utf-8'))
    args = SimpleNamespace(
        repo=Path(config['repo']), model=Path(config['model']),
        reference=Path(config['reference']),
        prompt_text=config['prompt_text'], delivery=config.get('delivery', ''),
        port=int(config.get('port', 7391)), rvc_url=config.get('rvc_url', ''),
    )

    for path in (args.repo, args.model, args.reference):
        if not path.exists():
            raise FileNotFoundError(path)
    if not (1024 <= args.port <= 65535):
        raise ValueError('Invalid port')
    if args.rvc_url:
        parsed = urlparse(args.rvc_url)
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.path != '/convert':
            raise ValueError('RVC URL must be a local /convert endpoint')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.chdir(args.repo)
    sys.path[:0] = [str(args.repo), str(args.repo / 'third_party' / 'Matcha-TTS')]
    sys.modules['wetext'] = None

    import numpy as np
    import soundfile as sf
    import torch
    from cosyvoice.cli.cosyvoice import AutoModel

    torch.set_num_threads(4)
    voice = AutoModel(model_dir=str(args.model), fp16=False, load_trt=False, load_vllm=False)
    lock = threading.Lock()
    prompt = 'You are a helpful assistant.<|endofprompt|>' + args.prompt_text
    instruction = 'You are a helpful assistant. ' + args.delivery + '<|endofprompt|>'

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/health':
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'ready': True, 'engine': 'cosyvoice3',
                'rvc': bool(args.rvc_url),
            }).encode())

        def do_POST(self):
            if self.path != '/synthesize':
                self.send_error(404)
                return
            size = int(self.headers.get('Content-Length', '0'))
            if size <= 0 or size > 4096:
                self.send_error(413)
                return
            try:
                request = json.loads(self.rfile.read(size))
                text = request['text'].strip()
                if not isinstance(text, str) or not (1 <= len(text) <= 400):
                    raise ValueError('Invalid text')
                with lock, torch.inference_mode():
                    if args.delivery:
                        generated = voice.inference_instruct2(
                            text, instruction, str(args.reference), stream=False,
                            text_frontend=False)
                    else:
                        generated = voice.inference_zero_shot(
                            text, prompt, str(args.reference), stream=False,
                            text_frontend=False)
                    chunks = [x['tts_speech'].detach().cpu().numpy().reshape(-1)
                              for x in generated]
                if not chunks:
                    raise RuntimeError('No audio')
                samples = np.concatenate(chunks)
                if not np.isfinite(samples).all():
                    raise RuntimeError('Invalid audio')
                peak = float(np.max(np.abs(samples)))
                if peak > 0.98:
                    samples *= 0.98 / peak
                wav = io.BytesIO()
                sf.write(wav, samples, voice.sample_rate, format='WAV', subtype='PCM_16')
                wav_bytes = wav.getvalue()
                if args.rvc_url:
                    try:
                        request = urllib.request.Request(
                            args.rvc_url, data=wav_bytes, method='POST',
                            headers={'Content-Type': 'audio/wav'},
                        )
                        with urllib.request.urlopen(request, timeout=30) as reply:
                            if reply.headers.get_content_type() != 'audio/wav':
                                raise RuntimeError('RVC returned a non-WAV response')
                            wav_bytes = reply.read(10_000_001)
                            if not (1000 <= len(wav_bytes) <= 10_000_000):
                                raise RuntimeError('RVC audio size is invalid')
                    except Exception as error:
                        print(f'RVC unavailable, keeping CosyVoice3 audio: {error}', flush=True)
                encoded = subprocess.run(
                    ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', 'pipe:0',
                     '-ac', '1', '-ar', '24000', '-b:a', '128k', '-f', 'mp3', 'pipe:1'],
                    input=wav_bytes, capture_output=True, check=True,
                    timeout=15,
                ).stdout
                if len(encoded) < 1000:
                    raise RuntimeError('Empty MP3')
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Content-Length', str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
            except Exception as error:
                self.send_error(500, str(error)[:200])

        def log_message(self, format, *values):
            print('%s %s' % (self.address_string(), format % values), flush=True)

    server = HTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Xiao Bai CosyVoice3 ready at http://127.0.0.1:{args.port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
