"""One local rehearsal voice check. Reads DSH token from DS_WEB_TOKEN; never prints it."""

import base64
import http.cookiejar
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path


BASE = "http://127.0.0.1:3081"
token = os.environ["DS_WEB_TOKEN"]
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
opener.open(f"{BASE}/?token={urllib.parse.quote(token)}", timeout=10).close()
state = json.load(opener.open(f"{BASE}/api/dsh-livestream/state", timeout=10))
stage = state["stageUrl"]
events = stage.replace("/?", "/events?", 1)
result = {}


def send() -> None:
    time.sleep(0.6)
    simulated = os.environ.get("DS_TEST_SIMULATE") == "1"
    payload = ({"kind": "chat", "name": "语音验收观众", "text": "小白你好，请用你的名字回答我。"}
               if simulated else {"text": "你好，我是小白。今天先在电脑上彩排。"})
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    endpoint = "simulate" if simulated else "say"
    request = urllib.request.Request(f"{BASE}/api/dsh-livestream/{endpoint}", data=body, headers={"Content-Type": "application/json"})
    try:
        with opener.open(request, timeout=35) as response:
            result["say_ok"] = json.load(response).get("ok")
    except Exception as error:
        result["say_error"] = str(error)


worker = threading.Thread(target=send, daemon=True)
worker.start()
with urllib.request.urlopen(events, timeout=35) as stream:
    for line in stream:
        if not line.startswith(b"data: "):
            continue
        event = json.loads(line[6:])
        if event.get("type") != "say":
            continue
        result["text"] = event.get("text")
        result["audio_bytes"] = len(event.get("audio") or "") * 3 // 4
        if event.get("audio"):
            output = Path(__file__).resolve().parents[2] / "artifacts" / "pilot-video" / "小白-stage-audio.mp3"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(base64.b64decode(event["audio"]))
        ack = stage.replace("/?", "/said?", 1) + "&id=" + urllib.parse.quote(event["id"])
        urllib.request.urlopen(urllib.request.Request(ack, data=b"", method="POST"), timeout=10).close()
        break
worker.join(timeout=10)
print(json.dumps(result, ensure_ascii=True))
if result.get("audio_bytes", 0) < 1000 or result.get("say_ok") is not True:
    raise SystemExit(1)
