import { test } from 'node:test';
import assert from 'node:assert/strict';
import { WebSocketServer } from 'ws';
import { BridgeClient } from './bridge-client.mjs';
import { OfficialQqAdapter } from './adapter.mjs';

test('unapproved sender is ignored; approved private message crosses the bridge once', async () => {
  const server = new WebSocketServer({ host: '127.0.0.1', port: 0 });
  await new Promise((resolve) => server.once('listening', resolve));
  const port = server.address().port;
  const received = [];
  server.on('connection', (socket) => socket.on('message', (raw) => {
    const frame = JSON.parse(String(raw));
    if (frame.kind === 'hello') {
      assert.equal(frame.token, 'test-token');
      socket.send(JSON.stringify({ kind: 'ready' }));
    } else {
      received.push(frame);
      socket.send(JSON.stringify({ kind: 'reply', threadId: frame.threadId, text: '', hold: true }));
      socket.send(JSON.stringify({ kind: 'reply', threadId: frame.threadId, text: '我是小白' }));
    }
  }));
  const bridge = new BridgeClient({ url: `ws://127.0.0.1:${port}`, token: 'test-token' });
  bridge.start();
  const sent = [];
  const bot = { sendText: async (target, text) => sent.push({ target, text }) };
  const unapproved = [];
  const adapter = new OfficialQqAdapter({ bot, bridge, allowed: (id) => id === 'owner',
    unapproved: (id) => unapproved.push(id) });
  const message = (id, senderId) => ({ kind: 'c2c', messageId: id, senderId, content: '你是谁',
    replyTarget: { scope: 'c2c', targetId: senderId, msgId: id } });
  adapter.handle(message('1', 'stranger'));
  adapter.handle(message('2', 'owner'));
  adapter.handle(message('2', 'owner'));
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('reply not sent')), 2_000);
    const poll = () => sent.length ? (clearTimeout(timer), resolve()) : setTimeout(poll, 10);
    poll();
  });
  assert.deepEqual(unapproved, ['stranger']);
  assert.equal(received.length, 1);
  assert.equal(received[0].threadId, 'qqbot:owner');
  assert.deepEqual(sent, [{ target: { scope: 'c2c', targetId: 'owner', msgId: '2' }, text: '我是小白' }]);
  bridge.stop();
  await new Promise((resolve) => server.close(resolve));
});
