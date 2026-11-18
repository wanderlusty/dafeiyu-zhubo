import { readFileSync } from 'node:fs';
import { performance } from 'node:perf_hooks';
import { BridgeClient } from './bridge-client.mjs';

const bridgeFile = process.argv[2];
const text = process.argv[3] ?? '在吗？用一句话回我';
if (!bridgeFile) throw new Error('Usage: node check-chat-latency.mjs /private/path/qq-bridge.json [text]');

const state = JSON.parse(readFileSync(bridgeFile, 'utf8'));
const port = Number(process.env.XIAOBAI_QQ_BRIDGE_PORT ?? 3210);
if (!Number.isInteger(port) || port < 1 || port > 65_535) throw new Error('Bridge port is invalid');
const url = `ws://127.0.0.1:${port}`;
if (typeof state.token !== 'string' || state.token.length < 16) throw new Error('Bridge token missing');

const bridge = new BridgeClient({ url, token: state.token, timeoutMs: 90_000, logger: { warn() {} } });
bridge.start();
const started = performance.now();
try {
  const reply = await bridge.ask('latency-check', text, '本地延时测试');
  console.log(JSON.stringify({ elapsedMs: Math.round(performance.now() - started), text: reply, chars: [...reply].length }, null, 2));
} finally {
  bridge.stop();
}
