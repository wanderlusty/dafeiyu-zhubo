"""Generate an original short Mandarin song using the local ACE-Step 1.5 Turbo model.

Run with the existing WSL CUDA Python after the model checkpoints are downloaded.
This is an offline rehearsal tool; it does not touch Bilibili or the live stage.
"""

import json
import os
import shutil
import sys
import argparse
import re
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
ACE = PROJECT / "vendor" / "ace-step-1.5"
DEPS = PROJECT / "vendor" / "ace-step-deps"
DEFAULT_CAPTION = (
    "Mandarin Chinese pop SONG WITH CLEAR SUNG FEMALE VOCALS THROUGHOUT, "
    "solo youthful female lead singing every line of the provided lyrics, "
    "expressive human-sounding lead voice, "
    "catchy melodic chorus, gentle acoustic guitar and piano accompaniment, "
    "soft drums, warm intimate studio recording, crisp Mandarin diction, "
    "clean acoustic production, each Chinese syllable articulated clearly on its own note, "
    "minimal melisma, comfortable mid-range melody with gentle high notes, "
    "no choir, no synthesizer, no vocoder."
)

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
sys.path[:0] = [str(DEPS), str(ACE)]
os.chdir(ACE)

import torch  # noqa: E402
from acestep.handler import AceStepHandler  # noqa: E402
from acestep.llm_inference import LLMHandler  # noqa: E402
from acestep.inference import GenerationConfig, GenerationParams, create_sample, generate_music  # noqa: E402
from acestep import model_downloader  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261104)
    parser.add_argument("--duration", type=int, default=36)
    parser.add_argument("--name", default="xiaobai-song-source-v2")
    parser.add_argument("--lm", action="store_true", help="Use the local 0.6B 5Hz LM for audio planning")
    lyrics_source = parser.add_mutually_exclusive_group()
    lyrics_source.add_argument("--lyrics-file", type=Path, help="UTF-8 lyrics file for a new local song")
    lyrics_source.add_argument("--topic", help="Generate new Mandarin lyrics from this theme")
    parser.add_argument("--prompt", help="Music style and arrangement description")
    parser.add_argument("--bpm", type=int, help="Tempo; 0 lets the model choose")
    parser.add_argument("--keyscale", help="Key; empty string lets the model choose")
    parser.add_argument("--timesignature", choices=["2/4", "3/4", "4/4", "6/8"])
    args = parser.parse_args()
    if not re.fullmatch(r"xiaobai-song-source(?:-[a-z0-9][a-z0-9_-]{0,49})?", args.name):
        raise ValueError("Invalid output name")
    if not (15 <= args.duration <= 180):
        raise ValueError("--duration must be between 15 and 180 seconds")
    if args.prompt is not None and not (1 <= len(args.prompt) <= 512):
        raise ValueError("--prompt must contain 1 to 512 characters")
    if args.bpm is not None and args.bpm != 0 and not (30 <= args.bpm <= 300):
        raise ValueError("--bpm must be 0 or between 30 and 300")
    if args.topic is not None and not (2 <= len(args.topic.strip()) <= 200):
        raise ValueError("--topic must contain 2 to 200 characters")
    output = PROJECT / "outputs" / f"{args.name}.flac"
    torch.set_num_threads(4)
    required = [
        ACE / "checkpoints" / "acestep-v15-turbo" / "model.safetensors",
        ACE / "checkpoints" / "Qwen3-Embedding-0.6B" / "model.safetensors",
        ACE / "checkpoints" / "vae" / "diffusion_pytorch_model.safetensors",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing ACE-Step checkpoints: " + ", ".join(missing))
    if output.exists():
        raise FileExistsError(output)

    # The upstream main-model precheck includes the optional planner. Limit
    # this precheck to the three components required by music generation;
    # topic mode checks and loads its planner separately below.
    model_downloader.MAIN_MODEL_COMPONENTS[:] = [
        "acestep-v15-turbo", "vae", "Qwen3-Embedding-0.6B",
    ]

    handler = AceStepHandler()
    status, ready = handler.initialize_service(
        project_root=str(ACE),
        config_path="acestep-v15-turbo",
        device="cuda",
        use_flash_attention=False,
        compile_model=False,
        offload_to_cpu=True,
        offload_dit_to_cpu=False,
        quantization=None,
    )
    if not ready:
        raise RuntimeError(status)

    llm = None
    if args.lm or args.topic:
        lm_weights = ACE / "checkpoints" / "acestep-5Hz-lm-0.6B" / "model.safetensors"
        if not lm_weights.is_file():
            raise FileNotFoundError(lm_weights)
        llm = LLMHandler()
        lm_status, lm_ready = llm.initialize(
            checkpoint_dir=str(ACE / "checkpoints"),
            lm_model_path="acestep-5Hz-lm-0.6B",
            backend="pt",
            device="cuda",
            offload_to_cpu=True,
            dtype=None,
        )
        if not lm_ready:
            raise RuntimeError(lm_status)

    lyrics = """[Verse]
海风轻轻吹过来
月亮挂在窗外
今天有你陪我聊天
烦恼交给大海

[Chorus]
听我唱，听我唱
小白陪你到天亮"""
    if args.lyrics_file:
        lyrics = args.lyrics_file.read_text(encoding="utf-8").strip()
    sample = None
    if args.topic:
        sample = create_sample(
            llm,
            f"Create a {args.duration}-second original Mandarin song about {args.topic.strip()}. "
            "Use at most eight short lyric lines, a clear singable melody, and a comfortable female range.",
            vocal_language="zh",
        )
        if not sample.success or not sample.lyrics:
            raise RuntimeError(f"Could not compose original lyrics: {sample.error}")
        lyrics = sample.lyrics
    if not (1 <= len(lyrics) <= 4096):
        raise ValueError("Lyrics must contain 1 to 4096 characters")
    caption = args.prompt or (sample.caption if sample else DEFAULT_CAPTION)
    if not caption:
        caption = DEFAULT_CAPTION
    if len(caption) > 512:
        caption = caption[:512].rsplit(",", 1)[0] or caption[:512]
    bpm = (args.bpm if args.bpm is not None
           else (sample.bpm if sample and sample.bpm else 100))
    if bpm and not (30 <= bpm <= 300):
        bpm = 100
    keyscale = (args.keyscale if args.keyscale is not None
                else (sample.keyscale if sample and sample.keyscale else "C Major"))
    timesignature = (args.timesignature if args.timesignature is not None
                     else (sample.timesignature if sample and sample.timesignature in {"2/4", "3/4", "4/4", "6/8"}
                           else "4/4"))
    params = GenerationParams(
        task_type="text2music",
        caption=caption,
        lyrics=lyrics,
        instrumental=False,
        vocal_language="zh",
        bpm=bpm or None,
        keyscale=keyscale,
        timesignature=timesignature,
        duration=args.duration,
        inference_steps=8,
        shift=3.0,
        seed=args.seed,
        thinking=bool(llm),
        use_cot_metas=False,
        use_cot_caption=False,
        use_cot_language=False,
    )
    config = GenerationConfig(batch_size=1, seeds=[args.seed], use_random_seed=False, audio_format="flac")
    scratch = PROJECT / "outputs" / "ace-song-working"
    scratch.mkdir(parents=True, exist_ok=True)
    result = generate_music(handler, llm, params, config, save_dir=str(scratch))
    if not result.success or not result.audios:
        raise RuntimeError(str(result.error))
    source = Path(result.audios[0]["path"])
    if not source.is_file():
        raise FileNotFoundError(source)
    shutil.copy2(source, output)
    (PROJECT / "outputs" / f"{args.name}.json").write_text(
        json.dumps({"lyrics": lyrics, "caption": params.caption, "seed": args.seed,
                    "topic": args.topic,
                    "model": "acestep-v15-turbo", "lm": args.lm, "path": str(output),
                    "bpm": params.bpm, "keyscale": params.keyscale,
                    "timesignature": params.timesignature}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(output)


if __name__ == "__main__":
    main()
