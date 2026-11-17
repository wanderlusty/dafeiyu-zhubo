import { readFileSync, writeFileSync, renameSync, unlinkSync, existsSync } from 'node:fs';
import { QQBot } from '@tencent-connect/qqbot-nodejs';
import { BridgeClient } from './bridge-client.mjs';
import { OfficialQqAdapter } from './adapter.mjs';

const required = (name) => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing ${name}`);
  return value;
};
const appId = required('QQBOT_APP_ID');
const appSecret = required('QQBOT_APP_SECRET');
const bridgeUrl = required('DSH_QQ_BRIDGE_URL');
const bridgeToken = required('DSH_QQ_BRIDGE_TOKEN');
const allowFile = required('QQBOT_ALLOWED_OPENIDS_FILE');
const pendingFile = required('QQBOT_PENDING_OPENIDS_FILE');
const sessionFile = required('QQBOT_SESSION_FILE');
if (!/^ws:\/\/127\.0\.0\.1:\d+$/.test(bridgeUrl)) throw new Error('Bridge must bind to localhost');

const savePrivateJson = (file, value) => {
  const temp = `${file}.${process.pid}.tmp`;
  writeFileSync(temp, JSON.stringify(value), { encoding: 'utf8', mode: 0o600 });
  renameSync(temp, file);
};
const readJson = (file, fallback) => {
  try { return JSON.parse(readFileSync(file, 'utf8')); }
  catch { return fallback; }
};
const allowed = (openid) => {
  const ids = readJson(allowFile, []);
  return Array.isArray(ids) && ids.includes(openid);
};
const unapproved = (openid) => {
  const pending = readJson(pendingFile, {});
  pending[openid] = new Date().toISOString();
  savePrivateJson(pendingFile, pending);
};
const sessionPersistence = {
  load: () => readJson(sessionFile, null),
  save: (session) => savePrivateJson(sessionFile, session),
  clear: () => { if (existsSync(sessionFile)) unlinkSync(sessionFile); },
};
const logger = {
  info: (message) => console.log(String(message)),
  warn: (message) => console.warn(String(message)),
  error: (message) => console.error(String(message)),
  debug: () => {},
};
const bot = new QQBot({ appId, appSecret, markdownSupport: false, sessionPersistence,
  logger: { info: () => {}, warn: () => {}, error: () => {}, debug: () => {} } });
const bridge = new BridgeClient({ url: bridgeUrl, token: bridgeToken, logger });
const adapter = new OfficialQqAdapter({ bot, bridge, allowed, unapproved, logger });
bot.on('ready', () => logger.info('QQ Bot connected'));
bot.on('resumed', () => logger.info('QQ Bot resumed'));
bot.on('disconnected', () => logger.warn('QQ Bot disconnected'));
bot.on('error', () => logger.error('QQ Bot transport error'));
bot.on('message', (_context, message) => adapter.handle(message));
const stop = () => { bridge.stop(); bot.stop(); };
process.once('SIGTERM', stop);
process.once('SIGINT', stop);
bridge.start();
await bot.start();
