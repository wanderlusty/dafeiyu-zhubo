import { readFileSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';

const require = createRequire(new URL('../../platform/qqbot-bridge/package.json', import.meta.url));
const { WebSocket } = require('ws');
const configDir = process.argv[2] || '/srv/xiaobai/data/napcat/config';
const configName = readdirSync(configDir).find(name => /^onebot11_\d+\.json$/.test(name));
if (!configName) throw new Error('NapCat OneBot config not found');
const config = JSON.parse(readFileSync(join(configDir, configName), 'utf8'));
const server = config.network?.websocketServers?.find(item => item.enable && Number(item.port) === 3001);
if (!server) throw new Error('OneBot WebSocket server is disabled');

const socket = new WebSocket('ws://127.0.0.1:3001', {
  headers: server.token ? { Authorization: `Bearer ${server.token}` } : {},
});
let settled = false;
let opened = false;
const finish = (loggedIn, message) => {
  if (settled) return;
  settled = true;
  clearTimeout(timer);
  console.log(JSON.stringify({ onebotReachable: opened, qqLoggedIn: loggedIn, message }));
  process.exitCode = loggedIn ? 0 : 1;
  socket.close();
};
const timer = setTimeout(() => finish(false, 'OneBot login check timed out'), 5000);
socket.on('open', () => {
  opened = true;
  socket.send(JSON.stringify({ action: 'get_login_info', echo: 'xiaobai-health' }));
});
socket.on('message', raw => {
  try {
    const response = JSON.parse(String(raw));
    if (response.echo !== 'xiaobai-health') return;
    const loggedIn = response.status === 'ok' && /^\d+$/.test(String(response.data?.user_id || ''));
    finish(loggedIn, loggedIn ? 'QQ account responded to get_login_info' : 'QQ account did not report a login');
  } catch { /* Ignore unrelated or malformed events. */ }
});
socket.on('error', () => finish(false, 'OneBot WebSocket connection failed'));
socket.on('close', () => finish(false, 'OneBot WebSocket closed before login response'));
