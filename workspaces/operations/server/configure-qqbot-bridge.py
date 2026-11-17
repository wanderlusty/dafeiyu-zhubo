"""Enable DSH's localhost QQ bridge in the private server config.

Run on the ECS as root. This script keeps a timestamped private backup and
refuses an unexpected layout instead of rewriting an unrelated YAML key.
"""

from datetime import datetime, timezone
from pathlib import Path
import re

CONFIG = Path('/srv/xiaobai/data/dsh/profiles/web/cordis.patch.yml')
old = CONFIG.read_text(encoding='utf-8')
start = old.find('    qqNative:\n')
if start < 0:
    raise SystemExit('qqNative block missing')
tail_start = start + len('    qqNative:\n')
next_block = re.search(r'(?m)^    (?=\S)', old[tail_start:])
end = tail_start + next_block.start() if next_block else -1
block = old[start:end if end >= 0 else None]
if '      bridge:\n        port: 3210\n' in block:
    print('QQ bridge already configured')
    raise SystemExit(0)
anchor = '      bindHomeSession: none\n'
if block.count(anchor) != 1 or '      bridge:' in block:
    raise SystemExit('Unexpected qqNative layout; config unchanged')
updated = old[:start] + block.replace(anchor, anchor + '      bridge:\n        port: 3210\n') + old[end if end >= 0 else len(old):]
backup = CONFIG.with_name(CONFIG.name + '.before-qqbot-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
backup.write_text(old, encoding='utf-8')
backup.chmod(0o600)
CONFIG.write_text(updated, encoding='utf-8')
print('Enabled localhost QQ bridge on port 3210; private backup saved')
