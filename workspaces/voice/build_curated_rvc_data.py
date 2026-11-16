"""Build an isolated Xiao Bai RVC experiment from original and screened new speech."""

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
DATA = PROJECT / "workspaces" / "voice" / "data"
OLD = DATA / "rvc-clean"
NEW = DATA / "rvc-new-clean"
OUT = DATA / "rvc-v2-curated"
AUDIT = PROJECT / "outputs" / "voice-source-audit"
ENCODER = PROJECT / "models" / "Fun-CosyVoice3-0.5B-2512" / "campplus.onnx"
REFERENCE = DATA / "reference-clean.wav"
MIN_OLD_SIMILARITY = 0.50
MIN_NEW_SIMILARITY = 0.55


def to_mono_16k(audio: np.ndarray, rate: int) -> np.ndarray:
    mono = audio.mean(axis=1) if audio.ndim == 2 else audio
    if rate != 16000:
        divisor = math.gcd(rate, 16000)
        mono = resample_poly(mono, 16000 // divisor, rate // divisor)
    return np.asarray(mono, dtype="float32")


def embedding(session: ort.InferenceSession, audio: np.ndarray, rate: int) -> np.ndarray:
    wave = torch.from_numpy(to_mono_16k(audio, rate).copy())[None, :]
    features = kaldi.fbank(wave, num_mel_bins=80, dither=0, sample_frequency=16000)
    features -= features.mean(dim=0, keepdim=True)
    values = session.run(None, {session.get_inputs()[0].name:
                                features.unsqueeze(0).numpy()})[0].flatten()
    return values / max(float(np.linalg.norm(values)), 1e-9)


def groups(segments: list[dict]) -> list[dict]:
    result = []
    current = None
    for segment in segments:
        if segment["no_speech_prob"] >= 0.45 or not segment["text"].strip():
            if current is not None:
                result.append(current)
                current = None
            continue
        start, end = float(segment["start"]), float(segment["end"])
        if current is not None and start - current["end"] <= 0.45 and end - current["start"] <= 8:
            current["end"] = end
            current["text"] += segment["text"]
        else:
            if current is not None:
                result.append(current)
            current = {"start": start, "end": end, "text": segment["text"]}
    if current is not None:
        result.append(current)
    return [group for group in result if 2.5 <= group["end"] - group["start"] <= 8]


def main() -> None:
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f"Curated output already exists: {OUT}")
    new_files = sorted(NEW.glob("new-*.wav"))
    if len(new_files) != 4:
        raise RuntimeError(f"Expected 4 separated new sources, found {len(new_files)}")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    session = ort.InferenceSession(str(ENCODER), sess_options=options,
                                   providers=["CPUExecutionProvider"])
    ref_audio, ref_rate = sf.read(REFERENCE, dtype="float32", always_2d=True)
    reference = embedding(session, ref_audio, ref_rate)
    old_files = sorted(OLD.glob("*.wav"))
    if len(old_files) != 7:
        raise RuntimeError(f"Expected 7 original sources, found {len(old_files)}")
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"thresholds": {"old": MIN_OLD_SIMILARITY, "new": MIN_NEW_SIMILARITY},
              "selected": [], "rejected": []}
    jobs = [("old", number, path, AUDIT / f"old-{number}.json", MIN_OLD_SIMILARITY)
            for number, path in enumerate(old_files, 1)]
    jobs += [("new", number, path, AUDIT / f"source-{number}.json", MIN_NEW_SIMILARITY)
             for number, path in enumerate(new_files, 1)]
    for kind, number, path, transcript_path, threshold in jobs:
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        audio, rate = sf.read(path, dtype="float32", always_2d=True)
        for index, segment in enumerate(groups(transcript["segments"]), 1):
            begin = max(0, int((segment["start"] - 0.10) * rate))
            end = min(len(audio), int((segment["end"] + 0.10) * rate))
            clip = audio[begin:end]
            mono = clip.mean(axis=1)
            rms = float(np.sqrt(np.mean(mono * mono)))
            if rms < 0.01:
                score = 0.0
            else:
                score = float(np.dot(reference, embedding(session, clip, rate)))
            row = {"kind": kind, "source": path.name, "start": segment["start"],
                   "end": segment["end"], "text": segment["text"],
                   "rms": round(rms, 4), "similarity": round(score, 3)}
            if score < threshold:
                report["rejected"].append(row)
                continue
            target = OUT / f"{kind}-{number:02d}-{index:03d}.wav"
            # Short fades avoid abrupt edges in the source clips.
            fade = min(int(rate * 0.04), len(mono) // 2)
            if fade:
                mono[:fade] *= np.linspace(0, 1, fade, dtype="float32")
                mono[-fade:] *= np.linspace(1, 0, fade, dtype="float32")
            sf.write(target, mono, rate, subtype="PCM_16")
            row["output"] = target.name
            report["selected"].append(row)
        print(f"processed {kind} {number}: {path.name}", flush=True)
    report_path = AUDIT / "curation-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Selected {len(report['selected'])} curated clips; rejected {len(report['rejected'])}; report: {report_path}", flush=True)


if __name__ == "__main__":
    main()
