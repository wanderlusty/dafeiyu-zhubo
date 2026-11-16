"""Stop only this project's persistent TTS/RVC workers inside WSL."""

import os
import signal
from pathlib import Path


ROOT = Path("/mnt/d/PRJ/ds-zhubo/workspaces/voice")
SERVICES = {str(ROOT / "serve_tts.py"), str(ROOT / "serve_rvc.py")}


def main() -> None:
    stopped = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            args = (proc / "cmdline").read_bytes().decode("utf-8", "replace").split("\0")
        except (OSError, PermissionError):
            continue
        scripts = SERVICES.intersection(args)
        if len(scripts) != 1:
            continue
        config = str(ROOT / ("voice_config.json" if "serve_tts.py" in next(iter(scripts)) else "rvc_config.json"))
        if config not in args:
            continue
        pid = int(proc.name)
        os.kill(pid, signal.SIGTERM)
        stopped.append(f"{pid}:{Path(next(iter(scripts))).name}")
    print("Stopped " + (", ".join(stopped) if stopped else "no voice workers"))


if __name__ == "__main__":
    main()
