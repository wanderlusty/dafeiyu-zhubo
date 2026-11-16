/** Local-only integration check: a rehearsal line reaches the stage with MP3 audio. */
import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const origin = 'http://127.0.0.1:3090';
const project = fileURLToPath(new URL('../../', import.meta.url));
const output = join(project, 'outputs', 'xiaobai-stage-rehearsal.mp3');
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(new Error('No spoken stage event within 120 seconds')), 120_000);
const get = async (path) => {
  const response = await fetch(origin + path, { signal: controller.signal });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
};
const csrf = (await get('/api/bootstrap')).csrf;
const post = async (path, body = {}) => {
  const response = await fetch(origin + path, {
    method: 'POST', signal: controller.signal,
    headers: { origin, 'x-xiaobai-csrf': csrf, 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status} ${await response.text()}`);
  return response.json();
};

let started = false;
try {
  const status = await get('/api/live');
  const stage = new URL(status.stageUrl);
  if (stage.hostname !== '127.0.0.1') throw new Error('Stage URL is not local');
  const eventsUrl = new URL('/events', stage);
  eventsUrl.search = stage.search;
  const stream = await fetch(eventsUrl, { signal: controller.signal });
  if (!stream.ok || !stream.body) throw new Error(`Stage SSE HTTP ${stream.status}`);
  const reader = stream.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const eventLoop = (async () => {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) throw new Error('Stage SSE closed before audio');
      buffer += decoder.decode(value, { stream: true });
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const packet = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
        const data = packet.split('\n').find(line => line.startsWith('data: '));
        if (!data) continue;
        const event = JSON.parse(data.slice(6));
        if (event.type !== 'say') continue;
        const audio = event.audio ? Buffer.from(event.audio, 'base64') : null;
        const ack = new URL('/said', stage);
        ack.search = stage.search;
        ack.searchParams.set('id', event.id);
        await fetch(ack, { method: 'POST', signal: controller.signal });
        if (!audio || audio.length < 1000) throw new Error('Stage sent a silent line');
        await writeFile(output, audio);
        return { text: event.text, bytes: audio.length, output };
      }
    }
  })();
  if (!status.show?.onAir) { await post('/api/live/rehearsal/start'); started = true; }
  await post('/api/live/simulate', { kind: 'chat', name: '本地测试观众', text: '小白，你今天想和大家聊什么？' });
  const result = await eventLoop;
  console.log(JSON.stringify(result, null, 2));
} finally {
  controller.abort();
  clearTimeout(timer);
  if (started) {
    try { await fetch(origin + '/api/live/offair', { method: 'POST', headers: { origin, 'x-xiaobai-csrf': csrf, 'content-type': 'application/json' }, body: '{}' }); } catch {}
  }
}
