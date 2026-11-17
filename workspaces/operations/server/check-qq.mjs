import { execFileSync } from 'node:child_process';

const journal = execFileSync('journalctl', ['-u', 'xiaobai-dsh', '--no-pager', '-n', '200'], { encoding: 'utf8' });
const matches = [...journal.matchAll(/127\.0\.0\.1:3081\/\?token=([A-Za-z0-9_-]{20,200})/g)];
if (!matches.length) throw new Error('DSH login token was not found in the local service journal');
const token = matches.at(-1)[1];
const base = 'http://127.0.0.1:3081';
const auth = await fetch(`${base}/?token=${encodeURIComponent(token)}`, { redirect: 'manual' });
const cookie = auth.headers.get('set-cookie')?.split(';', 1)[0];
if (auth.status !== 303 || !cookie) throw new Error(`DSH authentication returned ${auth.status}`);
const response = await fetch(`${base}/dsh-world/qq/native`, {
  headers: { cookie, origin: base, 'x-dsh-world': '1' },
});
if (!response.ok) throw new Error(`QQ status returned ${response.status}`);
const state = await response.json();
const { enabled, connected, autoReply, bindHomeSession, allowPrivateIds, sent, failed, lastError,
  lastEventAt, blocked, lastBlockedAt, conversations, answering, outbox } = state;
console.log(JSON.stringify({ enabled, connected, autoReply, bindHomeSession, allowPrivateIds, sent, failed, lastError,
  lastEventAt, blocked, lastBlockedAt, conversations, answering, outbox }));
