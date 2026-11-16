"""Prepare one short Bilibili song request for local stage playback.

Search/download, separate, estimate pitch, convert, and run mechanical QA.
The result is auto-checked, never represented as a human listening review.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[2]
JOBS = ROOT / "outputs" / "song-jobs"
COVERS = ROOT / "outputs" / "covers"
BILI = ROOT / ".venv-bili-cli" / "Scripts" / "bili.exe"
BBDOWN = ROOT / "vendor" / "bbdownnext" / "BBDown.exe"
FFMPEG = Path("D:/bilidown/resources/bin/ffmpeg.exe")
WSL_PYTHON = "/home/qzy/.local/share/feiyu-voice/cuda/tts-proxy/venv/bin/python"


def run(args: list[str], timeout: int) -> str:
    result = subprocess.run(args, text=True, encoding="utf-8", errors="replace",
                            capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed: {result.stderr[-500:] or result.stdout[-500:]}")
    return result.stdout


def wsl(path: Path) -> str:
    path = path.resolve()
    return f"/mnt/{path.drive[0].lower()}/{path.as_posix()[3:]}"


def duration(path: Path) -> float:
    result = subprocess.run([str(FFMPEG), "-hide_banner", "-i", str(path)],
                            text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=20)
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        raise RuntimeError("Could not read audio duration")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def compact(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", unicodedata.normalize("NFKC", text).casefold())


def parse_request(query: str) -> tuple[str, str]:
    quoted = re.search(r"《([^》]{1,40})》", query)
    if quoted:
        return query[:quoted.start()].strip().removesuffix("的"), quoted.group(1).strip()
    terms = query.split()
    if len(terms) >= 2:
        try:
            catalog = json.loads((ROOT / "workspaces" / "voice" / "song_clip_catalog.json").read_text(encoding="utf-8"))
            known_artists = {compact(song["artist"]) for song in catalog["songs"]}
            if compact(terms[-1]) in known_artists:
                return terms[-1], " ".join(terms[:-1])
        except (OSError, KeyError, ValueError):
            pass
        return terms[0].removesuffix("的"), " ".join(terms[1:])
    return "", query


def choose(items: list[dict], artist: str, song: str) -> dict:
    title = compact(song)
    singer = compact(artist)
    ranked = []
    for item in items:
        name = compact(re.sub(r"<[^>]+>", "", item.get("title", "")))
        if not title or title not in name:
            continue
        if singer and singer not in name and singer not in compact(item.get("desc", "")):
            continue
        try:
            mins, secs = map(int, item["duration"].split(":"))
            seconds = mins * 60 + secs
        except (ValueError, KeyError):
            continue
        if not 110 <= seconds <= 420:
            continue
        raw_title = item["title"]
        score = 0
        for word, weight in (("无损", 3), ("音质", 2), ("歌词", 2), ("MV", 1), ("现场", -5),
                             ("翻唱", -8), ("教学", -9), ("解析", -9), ("大声听", -7), ("伴奏", -9)):
            if word.casefold() in raw_title.casefold():
                score += weight
        ranked.append((score, item))
    if not ranked:
        raise RuntimeError("没有找到可用的原唱音源")
    return max(ranked, key=lambda pair: pair[0])[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()
    query = args.query.strip()
    if not 1 <= len(query) <= 80 or not re.fullmatch(r"[a-f0-9]{16}", args.job_id):
        raise ValueError("Invalid request")
    job = JOBS / args.job_id
    job.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    stage_started = started
    timings = {}

    def mark(stage: str) -> None:
        nonlocal stage_started
        now = time.perf_counter()
        timings[stage] = round(timings.get(stage, 0) + now - stage_started, 2)
        stage_started = now
        print(f"Timing {stage}: {timings[stage]:.2f}s", flush=True)

    artist, song = parse_request(query)
    search_query = f"{artist} {song}".strip()
    search = json.loads(run([str(BILI), "--compact", "search", "video", search_query, "--size", "10"], 40))
    if not search.get("ok"):
        raise RuntimeError("B 站搜索失败")
    item = choose(search["data"]["items"], artist, song)
    bvid = item["bvid"]
    print(f"Selected {bvid}: {item['title']}", flush=True)
    mark("search")
    run([str(BBDOWN), bvid, "-g", "a", "-F", "source", "-cwd", str(job),
         "--ffmpeg-path", str(FFMPEG)], 150)
    source = next(job.glob("source.*"), None)
    if not source or source.stat().st_size < 100_000 or source.stat().st_size > 70_000_000:
        raise RuntimeError("Downloaded audio is missing or oversized")
    source_duration = duration(source)
    if not 110 <= source_duration <= 420:
        raise RuntimeError("Source duration is outside the short-song range")
    mark("download")
    cover_name = f"auto-{args.job_id}"
    cover = COVERS / cover_name
    clip = cover / "source-clip.wav"
    vocals = cover / "stems" / "htdemucs" / "source-clip" / "vocals.wav"
    cover.mkdir(parents=True, exist_ok=False)
    excerpt_start = None
    activity = None
    candidates = []
    for fraction in (0.28, 0.43, 0.58, 0.73):
        start = max(20, min(source_duration - 35, round(source_duration * fraction)))
        if start not in candidates:
            candidates.append(start)
    for number, start in enumerate(candidates):
        attempt = cover / "candidates" / str(number)
        attempt.mkdir(parents=True)
        attempt_clip = attempt / "source-clip.wav"
        attempt_stems = attempt / "stems"
        attempt_vocals = attempt_stems / "htdemucs" / "source-clip" / "vocals.wav"
        run([str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-ss", str(start),
             "-t", "35", "-i", str(source), "-vn", "-ar", "44100", "-ac", "2",
             "-c:a", "pcm_s16le", str(attempt_clip)], 60)
        mark("clip")
        run(["wsl", "-e", WSL_PYTHON, "-m", "demucs", "-n", "htdemucs",
             "--two-stems", "vocals", "-o", wsl(attempt_stems), wsl(attempt_clip)], 420)
        mark("separation")
        activity = json.loads(run(["wsl", "-e", WSL_PYTHON,
                                   wsl(ROOT / "workspaces" / "voice" / "vocal_activity.py"),
                                   wsl(attempt_vocals)], 45).splitlines()[-1])
        mark("vocal_activity")
        print(f"Excerpt {start}s activity: {activity}", flush=True)
        if activity["usable"]:
            excerpt_start = start
            shutil.copy2(attempt_clip, clip)
            shutil.copytree(attempt_stems, cover / "stems")
            break
    if excerpt_start is None:
        raise RuntimeError("No 35-second excerpt has sustained singing")
    pitch_info = json.loads(run(["wsl", "-e", WSL_PYTHON,
                                 wsl(ROOT / "workspaces" / "voice" / "song_pitch.py"), wsl(vocals)], 60).splitlines()[-1])
    pitch = pitch_info["pitch"]
    print(f"Auto pitch: {pitch}", flush=True)
    mark("pitch_estimate")
    run(["wsl", "-e", WSL_PYTHON, wsl(ROOT / "workspaces" / "voice" / "cover_song.py"),
         "--input", wsl(source), "--name", cover_name, "--start", str(excerpt_start),
         "--duration", "35", "--pitch", str(pitch), "--backing-pitch", str(pitch),
         "--index-rate", "0.15", "--protect", "0.1"], 420)
    mark("voice_conversion_and_mix")
    output = cover / "xiaobai-cover.mp3"
    if not output.is_file() or not 700_000 <= output.stat().st_size <= 2_000_000:
        raise RuntimeError("Generated clip has an unexpected size")
    output_duration = duration(output)
    if not 33 <= output_duration <= 37:
        raise RuntimeError("Generated clip has an unexpected duration")
    run([str(FFMPEG), "-v", "error", "-i", str(output), "-f", "null", "NUL"], 60)
    settings_path = cover / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    if settings["vocal_rms"] < 0.005:
        raise RuntimeError("Generated clip has too little separated singing")
    mark("qa")
    settings.update({"review_status": "auto_checked", "source_bvid": bvid,
                     "source_title": item["title"], "song_query": query,
                     "pitch_estimate": pitch_info, "vocal_activity": activity})
    settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {"title": song, "query": query, "artist": artist, "clip": str(output), "duration": 35, "pitch": pitch,
              "bvid": bvid, "sourceTitle": item["title"], "reviewStatus": "auto_checked",
              "timingsSeconds": timings, "totalSeconds": round(time.perf_counter() - started, 2)}
    (job / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Song preparation failed: {error}", file=sys.stderr, flush=True)
        raise
