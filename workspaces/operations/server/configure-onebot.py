#!/usr/bin/env python3
"""Enable a local-only OneBot WebSocket server in a NapCat account config."""

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: configure-onebot.py /path/to/onebot11_ACCOUNT.json")
    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    network = data.setdefault("network", {})
    network["websocketServers"] = [
        {
            "enable": True,
            "name": "XiaoBaiLocalWS",
            "host": "0.0.0.0",
            "port": 3001,
            "reportSelfMessage": False,
            "enableForcePushEvent": True,
            "messagePostFormat": "array",
            "token": "",
            "debug": False,
            "heartInterval": 30000,
        }
    ]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OneBot WebSocket enabled on container port 3001; bind host port to loopback only")


if __name__ == "__main__":
    main()
