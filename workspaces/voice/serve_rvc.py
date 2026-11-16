"""Keep the trained Xiao Bai RVC model warm for local voice conversion."""

import argparse
import io
import json
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    settings = json.loads(parser.parse_args().config.read_text(encoding='utf-8'))
    repo = Path(settings['repo']).resolve()
    model = Path(settings['model']).resolve()
    index = Path(settings['index']).resolve()
    port = int(settings.get('port', 7392))
    if not all(path.is_file() for path in (model, index)) or not repo.is_dir():
        raise FileNotFoundError('RVC model, index or repository is missing')
    if not (1024 <= port <= 65535):
        raise ValueError('Invalid port')
    os.chdir(repo)
    os.environ['weight_root'] = str(model.parent)
    os.environ['rmvpe_root'] = str(repo / 'assets' / 'rmvpe')
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    sys.path.insert(0, str(repo))

    from configs.config import Config
    from infer.vc.modules import VC
    import soundfile as sf

    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        config = Config()
    finally:
        sys.argv = original_argv
    converter = VC(config)
    converter.get_vc(model.name)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/health':
                self.send_error(404)
                return
            body = json.dumps({'ready': True, 'engine': 'rvc-v2', 'model': model.name}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != '/convert':
                self.send_error(404)
                return
            size = int(self.headers.get('Content-Length', '0'))
            if not (1000 <= size <= 10_000_000):
                self.send_error(413)
                return
            source = self.rfile.read(size)
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as item:
                    item.write(source)
                    input_path = Path(item.name)
                try:
                    status, result = converter.vc_single(
                        0, str(input_path), 0, 'rmvpe', str(index),
                        float(settings.get('index_rate', 0.6)), 0, 1.0, 0.33,
                    )
                finally:
                    input_path.unlink(missing_ok=True)
                if not result or result[0] is None or result[1] is None:
                    raise RuntimeError(str(status))
                output = io.BytesIO()
                sf.write(output, result[1], result[0], format='WAV', subtype='PCM_16')
                body = output.getvalue()
                self.send_response(200)
                self.send_header('Content-Type', 'audio/wav')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as error:
                print(f'RVC conversion failed: {error}', flush=True)
                self.send_error(500, 'Voice conversion failed')

        def log_message(self, fmt, *values):
            print('%s %s' % (self.address_string(), fmt % values), flush=True)

    server = HTTPServer(('127.0.0.1', port), Handler)
    print(f'Xiao Bai RVC ready at http://127.0.0.1:{port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
