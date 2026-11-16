"""Resolve a live song request without waiting for the owner to choose a voice."""

import argparse
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "workspaces" / "voice" / "song_clip_catalog.json"
QUALITY_HOLDS = ROOT / "workspaces" / "voice" / "song_quality_holds.json"
COVERS = (ROOT / "outputs" / "covers").resolve()


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE)


def safe_file(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(COVERS):
        raise ValueError("Song catalog path must stay within outputs/covers")
    return path


def decline(reason: str) -> dict:
    return {
        "decision": "decline",
        "reason": reason,
        "reply": "这首歌我还没准备好，先换一首哦。",
        "needs_owner_choice": False,
    }


def resolve(query: str, catalog_path: Path = CATALOG) -> dict:
    key = normalized(query)
    if not key or len(query) > 80:
        return decline("invalid_query")
    holds = json.loads(QUALITY_HOLDS.read_text(encoding="utf-8"))["holds"]
    for held in holds:
        title = normalized(held["title"])
        artist = normalized(held["artist"])
        if key in {title, artist + title, title + artist, artist + "的" + title}:
            return {"decision": "decline", "reason": "needs_revision",
                    "reply": "这首歌我还在修音，先换一首好吗？", "needs_owner_choice": False}
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    matches = []
    for song in catalog["songs"]:
        aliases = {normalized(alias) for alias in song["aliases"]}
        if key in aliases:
            matches.append(song)
    if not matches:
        return {"decision": "prepare_in_background", "reply": "这首我还没唱过，我去找音源准备一小段。",
                "needs_owner_choice": False}
    if len(matches) != 1:
        return decline("ambiguous_song")

    song = matches[0]
    try:
        clip = safe_file(song["clip"])
        settings_path = safe_file(song["settings"])
        settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))
        if not clip.is_file() or clip.stat().st_size < 10_000:
            return decline("clip_missing")
        if settings.get("review_status") != "preferred_by_user":
            return decline("clip_not_accepted")
        for field in ("pitch", "backing_pitch", "start", "duration"):
            if settings.get(field) != song[field]:
                return decline("clip_settings_changed")
    except (FileNotFoundError, KeyError, ValueError, OSError, json.JSONDecodeError):
        return decline("catalog_invalid")

    return {
        "decision": "play_prepared_clip",
        "title": song["title"],
        "artist": song["artist"],
        "clip": str(clip),
        "pitch": song["pitch"],
        "backing_pitch": song["backing_pitch"],
        "duration": song["duration"],
        "needs_owner_choice": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Parsed song title, optionally with artist")
    args = parser.parse_args()
    # stdout is consumed as UTF-8 by Node; ASCII JSON avoids Windows console encoding drift.
    print(json.dumps(resolve(args.query), ensure_ascii=True))


if __name__ == "__main__":
    main()
