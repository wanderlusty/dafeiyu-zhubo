import { createServer } from 'node:http';
import { randomBytes } from 'node:crypto';
import { readFileSync, readdirSync, mkdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync, spawn } from 'node:child_process';
import { freemem, totalmem } from 'node:os';

const root = dirname(fileURLToPath(import.meta.url));
const project = join(root, '..', '..');
const dsh = 'http://127.0.0.1:3081';
const port = Number(process.env.XIAOBAI_PORT || 3090);
const songSourceDir = join(project, '声音', '点歌素材');
mkdirSync(songSourceDir, { recursive: true });
const tokenFile = join(project, '.dsh-home', 'control-center-token');
const csrf = randomBytes(24).toString('base64url');
let cookie = '';
const songJobs = new Map();
const songQueue = [];
let activeSongJob = null;
let voiceStartPromise = null;
let voiceReleasePromise = null;
let voiceIdleSince = null;
let cacheReclaimPromise = null;
let lastCacheReclaimAt = 0;
const songJobRoot = join(project, 'outputs', 'song-jobs');

function validSongResult(id, result) {
  const expected = join(project, 'outputs', 'covers', `auto-${id}`, 'xiaobai-cover.mp3');
  return result?.clip === expected && statSync(expected).size >= 700_000;
}

mkdirSync(songJobRoot, { recursive: true });
for (const entry of readdirSync(songJobRoot, { withFileTypes: true })) {
  if (!entry.isDirectory() || !/^[a-f0-9]{16}$/.test(entry.name)) continue;
  try {
    const result = JSON.parse(readFileSync(join(songJobRoot, entry.name, 'result.json'), 'utf8'));
    if (validSongResult(entry.name, result)) songJobs.set(entry.name,
      { id: entry.name, query: result.query || result.title, status: 'ready', result });
  } catch { /* incomplete or failed jobs stay unavailable */ }
}

function runNextSong() {
  if (activeSongJob || !songQueue.length) return;
  const job = songQueue.shift();
  activeSongJob = job.id;
  job.status = 'preparing';
  const worker = spawn('py', ['-3', join(project, 'workspaces', 'voice', 'auto_prepare_song.py'),
    '--query', job.query, '--job-id', job.id], { cwd: project, windowsHide: true,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
  let stdout = '';
  let stderr = '';
  worker.stdout.on('data', data => { stdout = (stdout + data.toString('utf8')).slice(-8000); });
  worker.stderr.on('data', data => { stderr = (stderr + data.toString('utf8')).slice(-2000); });
  const timeout = setTimeout(() => worker.kill(), 10 * 60 * 1000);
  worker.on('error', error => {
    clearTimeout(timeout);
    job.status = 'failed'; job.error = error.message;
  });
  worker.on('close', code => {
    clearTimeout(timeout);
    if (job.status !== 'failed') {
      try {
        if (code !== 0) throw new Error(stderr.split('\n').filter(Boolean).slice(-2).join(' ').slice(0, 200) || `退出码 ${code}`);
        const result = JSON.parse(stdout.split('\n').filter(Boolean).at(-1));
        if (!validSongResult(job.id, result)) throw new Error('生成文件路径无效');
        job.result = result;
        job.status = 'ready';
      } catch (error) { job.status = 'failed'; job.error = error.message; }
    }
    if (activeSongJob === job.id) activeSongJob = null;
    runNextSong();
  });
}

function songJobView(job) {
  return { id: job.id, query: job.query, status: job.status,
    result: job.status === 'ready' ? job.result : undefined,
    error: job.status === 'failed' ? job.error : undefined };
}

function token() {
  const value = readFileSync(tokenFile, 'utf8').trim();
  if (!/^[A-Za-z0-9_-]{20,200}$/.test(value)) throw new Error('DSH 连接令牌无效，请用“启动小白.cmd”启动服务');
  return value;
}

async function authenticate() {
  const response = await fetch(`${dsh}/?token=${encodeURIComponent(token())}`, { redirect: 'manual', signal: AbortSignal.timeout(8000) });
  const header = response.headers.get('set-cookie');
  if (response.status !== 303 || !header) throw new Error('DSH 登录已过期，请重启小白服务');
  cookie = header.split(';', 1)[0];
}

async function upstream(path, method = 'GET', body) {
  if (!cookie) await authenticate();
  const send = async () => fetch(dsh + path, {
    method,
    headers: { cookie, origin: dsh, 'content-type': 'application/json', 'x-dsh-world': '1' },
    body: method === 'POST' ? JSON.stringify(body || {}) : undefined,
    signal: AbortSignal.timeout(30000),
  });
  let response = await send();
  if (response.status === 401) { await authenticate(); response = await send(); }
  const content = await response.text();
  let value;
  try { value = JSON.parse(content); } catch { throw new Error(`DSH 返回 HTTP ${response.status}`); }
  if (!response.ok) throw new Error(value.error || value.message || `DSH 返回 HTTP ${response.status}`);
  return value;
}

function json(res, status, value) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
  res.end(JSON.stringify(value));
}

async function readJson(req) {
  let data = '';
  for await (const chunk of req) {
    data += chunk;
    if (data.length > 16384) throw new Error('请求太大');
  }
  return data ? JSON.parse(data) : {};
}

function qrData(value) {
  const python = join(project, '.venv-bili-cli', 'Scripts', 'python.exe');
  const png = execFileSync(python, [join(root, 'qr.py'), value], { timeout: 8000, maxBuffer: 1024 * 1024 });
  return `data:image/png;base64,${png.toString('base64')}`;
}

function songDecision(query) {
  const output = execFileSync('py', ['-3', join(project, 'workspaces', 'voice', 'song_request_policy.py'), query],
    { timeout: 5000, maxBuffer: 64 * 1024 });
  return JSON.parse(output.toString('utf8'));
}

async function voiceStatus() {
  try {
    const response = await fetch('http://127.0.0.1:7391/health', { signal: AbortSignal.timeout(2000) });
    if (!response.ok) throw new Error('语音服务不可用');
    const status = await response.json();
    if (status.rvc) {
      try {
        const conversion = await fetch('http://127.0.0.1:7392/health', { signal: AbortSignal.timeout(2000) });
        status.rvc = conversion.ok && (await conversion.json()).ready === true;
      } catch { status.rvc = false; }
    }
    return status;
  } catch { return { ready: false, engine: 'unloaded', rvc: false }; }
}

function runVoiceScript(name, timeoutMs) {
  return new Promise((resolve, reject) => {
    const script = join(project, 'workspaces', 'operations', name);
    const child = spawn('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script],
      { cwd: project, windowsHide: true });
    let output = '';
    for (const stream of [child.stdout, child.stderr]) stream.on('data', data => {
      output = (output + data.toString('utf8')).slice(-4000);
    });
    const timer = setTimeout(() => child.kill(), timeoutMs);
    child.on('error', error => { clearTimeout(timer); reject(error); });
    child.on('exit', code => {
      clearTimeout(timer);
      child.stdout.destroy();
      child.stderr.destroy();
      if (code === 0) resolve(output);
      else reject(new Error(`${name} 执行失败：${output.slice(-600) || `退出码 ${code}`}`));
    });
  });
}

async function ensureVoiceReady() {
  voiceIdleSince = null;
  if (voiceReleasePromise) await voiceReleasePromise.catch(() => {});
  const current = await voiceStatus();
  if (current.ready && current.rvc) return;
  if (!voiceStartPromise) voiceStartPromise = (async () => {
    await runVoiceScript('Start-Voice.ps1', 200_000);
    const status = await voiceStatus();
    if (!status.ready || !status.rvc) throw new Error('小白声线未就绪，请查看语音服务日志');
  })().finally(() => { voiceStartPromise = null; });
  await voiceStartPromise;
}

async function releaseIdleVoice() {
  if (!voiceReleasePromise) voiceReleasePromise = runVoiceScript('释放语音内存.ps1', 60_000)
    .finally(() => { voiceReleasePromise = null; });
  await voiceReleasePromise;
}

function resourceStatus() {
  const result = {
    freeRamMiB: Math.round(freemem() / 1048576),
    totalRamMiB: Math.round(totalmem() / 1048576),
    gpu: null,
  };
  try {
    const line = execFileSync('nvidia-smi',
      ['--query-gpu=memory.total,memory.free', '--format=csv,noheader,nounits'],
      { encoding: 'utf8', timeout: 3000, windowsHide: true }).trim().split(/\r?\n/)[0];
    const [totalMiB, freeMiB] = line.split(',').map(part => Number(part.trim()));
    if (Number.isFinite(totalMiB) && Number.isFinite(freeMiB)) result.gpu = { totalMiB, freeMiB };
  } catch { /* Some computers have no NVIDIA GPU or nvidia-smi. */ }
  return result;
}

async function reclaimVoiceCache() {
  if (!cacheReclaimPromise) cacheReclaimPromise = runVoiceScript('回收WSL文件缓存.ps1', 20_000)
    .then(() => { lastCacheReclaimAt = Date.now(); })
    .finally(() => { cacheReclaimPromise = null; });
  await cacheReclaimPromise;
}

const routes = {
  '/api/world': ['GET', '/dsh-world/console/snapshot'],
  '/api/qq': ['GET', '/dsh-world/qq/native'],
  '/api/qq/settings': ['POST', '/dsh-world/qq/native'],
  '/api/bili': ['GET', '/api/bili-duty/status'],
  '/api/bili/watched': ['GET', '/api/bili-duty/watched?limit=30'],
  '/api/bili/report': ['GET', '/api/bili-duty/report'],
  '/api/bili/settings': ['POST', '/api/bili-duty/config'],
  '/api/bili/run': ['POST', '/api/bili-duty/run'],
  '/api/live': ['GET', '/api/dsh-livestream/state'],
  '/api/live/account': ['GET', '/api/dsh-livestream/account'],
  '/api/live/room-info': ['GET', '/api/dsh-livestream/room-info'],
  '/api/live/settings': ['POST', '/api/dsh-livestream/settings'],
  '/api/live/login/start': ['POST', '/api/dsh-livestream/login/start'],
  '/api/live/login/import-duty': ['POST', '/api/dsh-livestream/login/import-duty'],
  '/api/live/login/poll': ['POST', '/api/dsh-livestream/login/poll'],
  '/api/live/connect': ['POST', '/api/dsh-livestream/connect'],
  '/api/live/disconnect': ['POST', '/api/dsh-livestream/disconnect'],
  '/api/live/rehearsal/start': ['POST', '/api/dsh-livestream/rehearsal/start'],
  '/api/live/simulate': ['POST', '/api/dsh-livestream/simulate'],
  '/api/live/offair': ['POST', '/api/dsh-livestream/offair'],
  '/api/live/obs/check': ['POST', '/api/dsh-livestream/obs/check'],
  '/api/live/broadcast/start': ['POST', '/api/dsh-livestream/broadcast/start'],
  '/api/live/broadcast/onair': ['POST', '/api/dsh-livestream/broadcast/onair'],
  '/api/live/broadcast/stop': ['POST', '/api/dsh-livestream/broadcast/stop'],
};

const server = createServer(async (req, res) => {
  try {
    if (req.headers.host !== `127.0.0.1:${port}` && req.headers.host !== `localhost:${port}`) return json(res, 403, { error: '只允许本机访问' });
    const requestUrl = new URL(req.url, `http://127.0.0.1:${port}`);
    const path = requestUrl.pathname;
    if (path === '/api/song/resolve' && req.method === 'GET') {
      const query = (requestUrl.searchParams.get('q') || '').trim();
      if (query.length > 80) return json(res, 400, { error: '歌名太长' });
      return json(res, 200, songDecision(query));
    }
    if (path === '/api/song/request' && req.method === 'POST') {
      if (req.headers.origin !== `http://127.0.0.1:${port}` && req.headers.origin !== `http://localhost:${port}`) return json(res, 403, { error: '来源不允许' });
      if (req.headers['x-xiaobai-csrf'] !== csrf) return json(res, 403, { error: '页面验证失败' });
      const query = String((await readJson(req)).query || '').trim();
      if (!query || query.length > 80) return json(res, 400, { error: '歌名无效' });
      const decision = songDecision(query);
      if (decision.decision === 'play_prepared_clip') return json(res, 200, decision);
      if (decision.decision === 'decline') return json(res, 200, decision);
      const existing = [...songJobs.values()].find(job => job.query === query && ['queued', 'preparing', 'ready'].includes(job.status));
      if (existing) return json(res, 200, songJobView(existing));
      if (songQueue.length >= 7) return json(res, 429, { error: '已有 8 首歌正在准备或等待，请稍后再点' });
      const job = { id: randomBytes(8).toString('hex'), query, status: 'queued' };
      songJobs.set(job.id, job);
      songQueue.push(job);
      runNextSong();
      return json(res, 202, songJobView(job));
    }
    if (path === '/api/song/job' && req.method === 'GET') {
      const job = songJobs.get(requestUrl.searchParams.get('id'));
      return job ? json(res, 200, songJobView(job)) : json(res, 404, { error: '点歌任务不存在' });
    }
    if (path === '/api/song/audio' && req.method === 'GET') {
      const job = songJobs.get(requestUrl.searchParams.get('id'));
      if (!job || job.status !== 'ready') return json(res, 404, { error: '点歌音频未就绪' });
      const audio = readFileSync(job.result.clip);
      if (audio.length > 2_000_000) return json(res, 502, { error: '点歌音频过大' });
      res.writeHead(200, { 'content-type': 'audio/mpeg', 'content-length': audio.length, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
      return res.end(audio);
    }
    if (path === '/preview/song' && req.method === 'GET') {
      const query = (requestUrl.searchParams.get('q') || '').trim();
      if (query.length > 80) return json(res, 400, { error: '歌名太长' });
      const decision = songDecision(query);
      if (decision.decision !== 'play_prepared_clip') return json(res, 404, { error: '没有已通过试听的片段' });
      const audio = readFileSync(decision.clip);
      res.writeHead(200, { 'content-type': 'audio/mpeg', 'content-length': audio.length, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
      return res.end(audio);
    }
    if (path === '/api/song/search' && req.method === 'GET') {
      const query = (requestUrl.searchParams.get('q') || '').trim().toLocaleLowerCase('zh-CN');
      if (query.length > 80) return json(res, 400, { error: '歌名太长' });
      const terms = query.split(/[\s·:：—-]+/u).filter(Boolean);
      const allowed = new Set(['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg']);
      const rows = readdirSync(songSourceDir, { withFileTypes: true })
        .filter(entry => entry.isFile() && allowed.has(entry.name.slice(entry.name.lastIndexOf('.')).toLowerCase()))
        .map(entry => ({ name: entry.name, available: true }))
        .filter(entry => terms.length && terms.every(term => entry.name.toLocaleLowerCase('zh-CN').includes(term)))
        .slice(0, 20);
      return json(res, 200, { query, matches: rows, sourceDirectory: songSourceDir,
        status: rows.length ? 'source_available' : 'source_missing',
        message: rows.length ? '本机找到了音源，可以准备本地翻唱。' : '本机还没有这首歌的可用音源；小白不会凭歌名准确唱出原曲。' });
    }
    if (path === '/' && req.method === 'GET') {
      const html = readFileSync(join(root, 'index.html'));
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'content-security-policy': "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-src http://127.0.0.1:7390; connect-src 'self'; base-uri 'none'; object-src 'none'" });
      return res.end(html);
    }
    if (path === '/app.js' && req.method === 'GET') {
      res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8', 'cache-control': 'no-store' });
      return res.end(readFileSync(join(root, 'app.js')));
    }
    if (path === '/style.css' && req.method === 'GET') {
      res.writeHead(200, { 'content-type': 'text/css; charset=utf-8', 'cache-control': 'no-store' });
      return res.end(readFileSync(join(root, 'style.css')));
    }
    if (path === '/assets/live-cover-xiaobai.jpg' && req.method === 'GET') {
      const cover = readFileSync(join(project, 'assets', 'live-cover-xiaobai.jpg'));
      res.writeHead(200, { 'content-type': 'image/jpeg', 'content-length': cover.length, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
      return res.end(cover);
    }
    if ((path === '/preview/xiaobai-song-rvc.mp3' || path === '/preview/xiaobai-song-original.mp3') && req.method === 'GET') {
      const filename = path.endsWith('-rvc.mp3') ? 'xiaobai-song-rvc-v3.mp3' : 'xiaobai-song-original-v3.mp3';
      const audio = readFileSync(join(project, 'outputs', filename));
      res.writeHead(200, { 'content-type': 'audio/mpeg', 'content-length': audio.length, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
      return res.end(audio);
    }
    if ((path === '/preview/xiaobai-song-clean.mp3' || path === '/preview/xiaobai-song-v4.mp3' || path === '/preview/xiaobai-rainbow.mp3') && req.method === 'GET') {
      const filename = path.endsWith('rainbow.mp3')
        ? join(project, 'outputs', 'covers', 'rainbow-preview-a', 'xiaobai-cover-faded.mp3')
        : join(project, 'outputs', path.endsWith('v4.mp3') ? 'xiaobai-song-rvc-v4.mp3' : 'xiaobai-song-rvc-v2.mp3');
      const audio = readFileSync(filename);
      res.writeHead(200, { 'content-type': 'audio/mpeg', 'content-length': audio.length, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
      return res.end(audio);
    }
    if (path === '/preview/xiaobai-song-v2.mp3' && req.method === 'GET') {
      const audio = readFileSync(join(project, 'outputs', 'xiaobai-song-rvc-v2.mp3'));
      res.writeHead(200, { 'content-type': 'audio/mpeg', 'content-length': audio.length, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
      return res.end(audio);
    }
    if (path === '/preview/xiaobai-speech-v2.wav' && req.method === 'GET') {
      const audio = readFileSync(join(project, 'outputs', 'xiaobai-clean-natural-rvc-v2.wav'));
      res.writeHead(200, { 'content-type': 'audio/wav', 'content-length': audio.length, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
      return res.end(audio);
    }
    const voiceCompare = {
      '/preview/compare/xiaobai-v4.mp3': 'xiaobai-v4-words-original.mp3',
      '/preview/compare/xiaobai-v4-clear.mp3': 'xiaobai-v4-words-clear.mp3',
      '/preview/compare/xiaobai-v4-protect10.mp3': 'xiaobai-v4-words-protect10.mp3',
      '/preview/compare/xiaobai-v4-index30.mp3': 'xiaobai-v4-words-index30.mp3',
      '/preview/compare/rainbow-high.mp3': 'rainbow-phrase-p8.mp3',
      '/preview/compare/rainbow-low.mp3': 'rainbow-phrase-p0.mp3',
    };
    if (req.method === 'GET' && Object.hasOwn(voiceCompare, path)) {
      const audio = readFileSync(join(project, 'outputs', 'voice-compare', voiceCompare[path]));
      res.writeHead(200, { 'content-type': 'audio/mpeg', 'content-length': audio.length, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
      return res.end(audio);
    }
    if ((path === '/preview/xiaobai-tts.wav' || path === '/preview/xiaobai-rvc.wav') && req.method === 'GET') {
      const filename = path.endsWith('-rvc.wav') ? 'xiaobai-clean-natural-rvc-v2.wav' : 'xiaobai-clean-natural-tts.wav';
      const audio = readFileSync(join(project, 'outputs', filename));
      res.writeHead(200, { 'content-type': 'audio/wav', 'content-length': audio.length, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
      return res.end(audio);
    }
    if (path === '/api/voice' && req.method === 'GET') {
      return json(res, 200, await voiceStatus());
    }
    if (path === '/api/resources' && req.method === 'GET') return json(res, 200, resourceStatus());
    if (path === '/api/resources/reclaim' && req.method === 'POST') {
      if (req.headers.origin !== `http://127.0.0.1:${port}` && req.headers.origin !== `http://localhost:${port}`) return json(res, 403, { error: '来源不允许' });
      if (req.headers['x-xiaobai-csrf'] !== csrf) return json(res, 403, { error: '页面验证失败' });
      await readJson(req);
      if (voiceStartPromise || activeSongJob) return json(res, 409, { error: '模型或点歌任务正在运行，请稍后再回收缓存' });
      const status = await voiceStatus();
      if (!status.ready || !status.rvc) return json(res, 409, { error: '语音正在生成或模型未就绪，请稍后重试' });
      await reclaimVoiceCache();
      return json(res, 200, resourceStatus());
    }
    if ((path === '/api/voice/prepare' || path === '/api/voice/release') && req.method === 'POST') {
      if (req.headers.origin !== `http://127.0.0.1:${port}` && req.headers.origin !== `http://localhost:${port}`) return json(res, 403, { error: '来源不允许' });
      if (req.headers['x-xiaobai-csrf'] !== csrf) return json(res, 403, { error: '页面验证失败' });
      await readJson(req);
      if (path === '/api/voice/prepare') await ensureVoiceReady();
      else {
        if (voiceStartPromise) return json(res, 409, { error: '小白声线正在加载，请稍后释放' });
        const state = await upstream('/api/dsh-livestream/state');
        if (state.show?.onAir || state.broadcast?.phase !== 'idle') return json(res, 400, { error: '小白正在彩排或直播，请先结束' });
        voiceIdleSince = null;
        await releaseIdleVoice();
      }
      return json(res, 200, await voiceStatus());
    }
    if (path === '/api/bootstrap' && req.method === 'GET') return json(res, 200, { csrf });
    const route = routes[path];
    if (!route || req.method !== route[0]) return json(res, 404, { error: '接口不存在' });
    let body;
    if (req.method === 'POST') {
      if (req.headers.origin !== `http://127.0.0.1:${port}` && req.headers.origin !== `http://localhost:${port}`) return json(res, 403, { error: '来源不允许' });
      if (req.headers['x-xiaobai-csrf'] !== csrf) return json(res, 403, { error: '页面验证失败' });
      body = await readJson(req);
      if (path === '/api/qq/settings') {
        body = Object.fromEntries(Object.entries(body).filter(([key]) => ['autoReply', 'allowPrivate'].includes(key)));
      }
      if (path === '/api/bili/settings') {
        body = Object.fromEntries(Object.entries(body).filter(([key]) => ['perDay', 'peakValley', 'noon', 'night', 'autoComment', 'replyToComments', 'fetchPerRound'].includes(key)));
      }
      if (path === '/api/live/settings') {
        body = Object.fromEntries(Object.entries(body).filter(([key]) => ['liveTitle', 'roomId', 'areaId', 'streamKbps', 'videoVolume', 'videoDuckVolume', 'voiceGain', 'idleAfterSec', 'useCover'].includes(key)));
        if ('useCover' in body) {
          body.liveCover = body.useCover ? join(project, 'assets', 'live-cover-xiaobai.jpg') : '';
          delete body.useCover;
        }
      }
      if (path === '/api/live/broadcast/start' && body.confirm !== '开播') return json(res, 400, { error: '请在页面确认正式开播' });
    }
    if (path === '/api/live/broadcast/start') {
      const [account, current] = await Promise.all([
        upstream('/api/dsh-livestream/account'),
        upstream('/api/dsh-livestream/state'),
      ]);
      if (!account.account) return json(res, 400, { error: '请先登录 B 站开播账号' });
      if (!current.settings?.areaId) return json(res, 400, { error: '请先选择直播分区并保存' });
      if (current.show?.onAir) return json(res, 400, { error: '请先结束本地彩排，等小白停止说话后再正式开播' });
      body = {};
    }
    if (path === '/api/live/rehearsal/start' || path === '/api/live/broadcast/start' || path === '/api/live/broadcast/onair') await ensureVoiceReady();
    let result = await upstream(route[1], req.method, body);
    if (path === '/api/live/broadcast/stop') result = await upstream('/api/dsh-livestream/offair', 'POST', {});
    if (path === '/api/live/offair' || path === '/api/live/broadcast/stop') voiceIdleSince = null;
    if (path === '/api/live/login/start' && result.url) {
      result.qrData = qrData(result.url);
    }
    if (path === '/api/live' && result.broadcast?.phase === 'face' && result.broadcast.faceQr) result.broadcast.faceQrData = qrData(result.broadcast.faceQr);
    return json(res, 200, result);
  } catch (error) {
    return json(res, 502, { error: error instanceof Error ? error.message : String(error) });
  }
});

server.listen(port, '127.0.0.1', () => console.log(`小白控制台：http://127.0.0.1:${port}/`));
const voiceIdleMonitor = setInterval(async () => {
  if (voiceStartPromise || voiceReleasePromise) return;
  try {
    const status = await voiceStatus();
    if (!status.ready) { voiceIdleSince = null; return; }
    const state = await upstream('/api/dsh-livestream/state');
    if (state.show?.onAir || state.broadcast?.phase !== 'idle') {
      voiceIdleSince = null;
      if (status.rvc && !activeSongJob && !cacheReclaimPromise
          && freemem() < 5 * 1073741824 && Date.now() - lastCacheReclaimAt > 180_000) {
        await reclaimVoiceCache();
      }
      return;
    }
    if (voiceIdleSince === null) voiceIdleSince = Date.now();
    if (Date.now() - voiceIdleSince < 120_000) return;
    voiceIdleSince = null;
    await releaseIdleVoice();
  } catch (error) { console.warn('空闲语音检查失败：', error.message); }
}, 30_000);
voiceIdleMonitor.unref();
