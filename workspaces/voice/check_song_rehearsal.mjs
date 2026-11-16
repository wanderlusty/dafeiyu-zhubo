/** Verify that a simulated song request reaches the local stage as MP3. */
const origin = 'http://127.0.0.1:3090';
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(new Error('Song stage timeout')), 300_000);
const song = process.argv[2] || '许嵩的《断桥残雪》';
let started = false;
const request = async (path, body) => {
  const response = await fetch(origin + path, body === undefined ? { signal: controller.signal } : {
    method: 'POST', signal: controller.signal,
    headers: { origin, 'x-xiaobai-csrf': csrf, 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status} ${await response.text()}`);
  return response.json();
};
const csrf = (await request('/api/bootstrap')).csrf;
try {
  const state = await request('/api/live');
  const stage = new URL(state.stageUrl);
  if (stage.hostname !== '127.0.0.1') throw new Error('Stage is not local');
  const events = new URL('/events', stage);
  events.search = stage.search;
  const stream = await fetch(events, { signal: controller.signal });
  if (!stream.ok || !stream.body) throw new Error('Stage event stream unavailable');
  const reader = stream.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const songStates = [];
  let sung = null;
  const heard = (async () => {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) throw new Error('Stage disconnected');
      buffer += decoder.decode(value, { stream: true });
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const packet = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const line = packet.split('\n').find(part => part.startsWith('data: '));
        if (!line) continue;
        const event = JSON.parse(line.slice(6));
        if (event.type === 'songs') {
          const current = event.items?.at(-1);
          if (current && songStates.at(-1) !== current.state) songStates.push(current.state);
          if (current?.state === 'done' && sung) return { ...sung, songStates };
        }
        if (event.type !== 'say') continue;
        const ack = new URL('/said', stage);
        ack.search = stage.search;
        ack.searchParams.set('id', event.id);
        if (event.text?.startsWith('演唱《')) {
          const bytes = Buffer.from(event.audio || '', 'base64');
          if (bytes.length < 700_000) throw new Error('Singing MP3 is too small');
          sung = { text: event.text, bytes: bytes.length, localRehearsal: true };
          // Keep the song visible long enough to inspect the stage panel.
          await new Promise(resolve => setTimeout(resolve, 15_000));
        }
        await fetch(ack, { method: 'POST', signal: controller.signal });
      }
    }
  })();
  if (!state.show?.onAir) { await request('/api/live/rehearsal/start', {}); started = true; }
  await request('/api/live/simulate', { kind: 'chat', name: '本地测试观众',
    text: `小白，我想听你唱${song}，可以唱一小段吗？` });
  console.log(JSON.stringify(await heard));
} finally {
  controller.abort();
  clearTimeout(timer);
  if (started) {
    try { await fetch(origin + '/api/live/offair', { method: 'POST',
      headers: { origin, 'x-xiaobai-csrf': csrf, 'content-type': 'application/json' }, body: '{}' }); } catch {}
  }
}
