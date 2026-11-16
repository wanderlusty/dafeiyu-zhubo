"""Read the logged-in Bilibili account's live-room metadata; print no cookies."""

import asyncio
import json
from pathlib import Path

from bilibili_api import Credential, user


ROOT = Path(__file__).resolve().parents[2]
saved = json.loads((ROOT / ".dsh-home" / "bili-cli" / "credential.json").read_text(encoding="utf-8"))
credential = Credential(**saved)
uid = int(saved["dedeuserid"])


async def main() -> None:
    info = await user.User(uid=uid, credential=credential).get_live_info()
    room = info.get("live_room") or {}
    print(json.dumps({
        "uid": uid,
        "room_id": room.get("roomid") or room.get("room_id"),
        "live_status": room.get("liveStatus") or room.get("live_status"),
        "room_title": room.get("title"),
        "keys": list(info.keys()),
    }, ensure_ascii=True))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "message": str(exc)[:200]}, ensure_ascii=True))
        raise SystemExit(1) from None
