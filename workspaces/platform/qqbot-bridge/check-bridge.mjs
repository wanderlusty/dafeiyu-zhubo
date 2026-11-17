import { readFileSync } from 'node:fs';
import { WebSocket } from 'ws';

const tokenFile = process.argv[2];
if (!tokenFile) throw new Error('Usage: node check-bridge.mjs /private/path/qq-bridge.json');
const { token } = JSON.parse(readFileSync(tokenFile, 'utf8'));
if (typeof token !== 'string' || token.length < 16) throw new Error('Bridge token missing');
const socket = new WebSocket('ws://127.0.0.1:3210');
const timer = setTimeout(() => { console.error('Bridge handshake timed out'); process.exitCode = 1; socket.terminate(); }, 5_000);
socket.on('open', () => socket.send(JSON.stringify({ kind: 'hello', token })));
socket.on('message', (raw) => {
  try {
    if (JSON.parse(String(raw)).kind === 'ready') {
      clearTimeout(timer);
      console.log('DSH QQ bridge authenticated on localhost');
      socket.close();
    }
  } catch { /* ignore malformed reply */ }
});
socket.on('error', () => { clearTimeout(timer); console.error('DSH QQ bridge unavailable'); process.exitCode = 1; });
