"""Compare local voice clips to Xiao Bai's reference with CosyVoice's speaker encoder."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import onnxruntime as ort
import soundfile as sf
import torch
import torchaudio.compliance.kaldi as kaldi
from scipy.signal import resample_poly


PROJECT = Path(__file__).resolve().parents[2]
REFERENCE = PROJECT / "workspaces" / "voice" / "data" / "reference-clean.wav"
ENCODER = PROJECT / "models" / "Fun-CosyVoice3-0.5B-2512" / "campplus.onnx"


def load_mono(path: Path) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    if rate != 16000:
        divisor = math.gcd(rate, 16000)
        mono = resample_poly(mono, 16000 // divisor, rate // divisor)
    return mono


def embed(session: ort.InferenceSession, audio: np.ndarray) -> np.ndarray:
    tensor = torch.from_numpy(np.asarray(audio, dtype="float32").copy())[None, :]
    feature = kaldi.fbank(tensor, num_mel_bins=80, dither=0, sample_frequency=16000)
    feature -= feature.mean(dim=0, keepdim=True)
    values = session.run(None, {session.get_inputs()[0].name:
                                feature.unsqueeze(0).numpy()})[0].flatten()
    return values / max(float(np.linalg.norm(values)), 1e-9)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new", action="store_true")
    args = parser.parse_args()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    session = ort.InferenceSession(str(ENCODER), sess_options=options,
                                   providers=["CPUExecutionProvider"])
    reference = embed(session, load_mono(REFERENCE))
    folder = PROJECT / "workspaces" / "voice" / "data" / ("rvc-new-clean" if args.new else "rvc-clean")
    for path in sorted(folder.glob("*.wav")):
        audio = load_mono(path)
        length = len(audio) / 16000
        scores = []
        for start in range(0, int(length) - 5, 20):
            clip = audio[start * 16000:(start + 6) * 16000]
            if float(np.sqrt(np.mean(clip * clip))) < 0.01:
                continue
            scores.append(round(float(np.dot(reference, embed(session, clip))), 3))
        print(json.dumps({"file": path.name, "duration_sec": round(length, 1),
                          "scores": scores,
                          "p10_p50_p90": np.percentile(scores, [10, 50, 90]).round(3).tolist()
                          if scores else []}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
