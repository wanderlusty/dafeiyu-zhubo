"""Interactively save official QQ Bot credentials in the ECS private data dir.

Run from an interactive terminal as root. The AppSecret input is hidden and
never appears in a shell command, process argument, or this repository.
"""

import getpass
import json
import os
import re
from pathlib import Path

PRIVATE = Path('/srv/xiaobai/data/qqbot')
BRIDGE = Path('/srv/xiaobai/data/dsh/worlds/ds/qq-bridge.json')
SAFE = re.compile(r'^[A-Za-z0-9._~+-]+$')

app_id = input('QQ Bot AppID: ').strip()
app_secret = getpass.getpass('QQ Bot AppSecret (input hidden): ').strip()
if not SAFE.fullmatch(app_id) or not SAFE.fullmatch(app_secret):
    raise SystemExit('Unexpected credential characters; no file was written')
token = json.loads(BRIDGE.read_text(encoding='utf-8'))['token']
if not isinstance(token, str) or len(token) < 16:
    raise SystemExit('DSH bridge token missing')

PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
body = '\n'.join((
    f'QQBOT_APP_ID={app_id}',
    f'QQBOT_APP_SECRET={app_secret}',
    'DSH_QQ_BRIDGE_URL=ws://127.0.0.1:3210',
    f'DSH_QQ_BRIDGE_TOKEN={token}',
    'QQBOT_ALLOWED_OPENIDS_FILE=/srv/xiaobai/data/qqbot/allowed-openids.json',
    'QQBOT_PENDING_OPENIDS_FILE=/srv/xiaobai/data/qqbot/pending-openids.json',
    'QQBOT_SESSION_FILE=/srv/xiaobai/data/qqbot/gateway-session.json',
    '',
))
target = PRIVATE / 'qqbot.env'
temp = PRIVATE / 'qqbot.env.tmp'
with open(temp, 'w', encoding='utf-8', opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
    output.write(body)
os.chmod(temp, 0o600)
os.replace(temp, target)
for name, default in (('allowed-openids.json', '[]\n'), ('pending-openids.json', '{}\n')):
    file = PRIVATE / name
    if not file.exists():
        with open(file, 'w', encoding='utf-8', opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
            output.write(default)
    os.chmod(file, 0o600)
uid = __import__('pwd').getpwnam('xiaobai').pw_uid
gid = __import__('grp').getgrnam('xiaobai').gr_gid
for file in (target, PRIVATE / 'allowed-openids.json', PRIVATE / 'pending-openids.json'):
    os.chown(file, uid, gid)
os.chmod(PRIVATE, 0o700)
os.chown(PRIVATE, uid, gid)
print('Private QQ Bot configuration saved. No credentials printed.')
