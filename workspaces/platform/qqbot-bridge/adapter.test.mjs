import { test } from 'node:test';
import assert from 'node:assert/strict';
import { WebSocketServer } from 'ws';
import { BridgeClient } from './bridge-client.mjs';
import { OfficialQqAdapter, sanitizeReply, splitReply } from './adapter.mjs';

test('mechanical internals are removed before a chat reply is sent', () => {
  const cleaned = sanitizeReply('## 结果\n- 路径是 `D:\\PRJ\\ds-zhubo\\README.md`，**稍等**。\nexec_command !!!!');
  assert.doesNotMatch(cleaned, /D:\\|exec_command|##|\*\*/);
  assert.match(cleaned, /这个位置/);
  assert.match(cleaned, /稍等/);
  assert.equal(cleaned.includes('!!!!'), false);
});

test('short conversational replies are not rewritten', () => {
  assert.deepEqual(splitReply('嗯，我在。'), ['嗯，我在。']);
});

test('long chat replies are capped at two readable messages', () => {
  const reply = `第一句话说完了。${'中间内容'.repeat(240)}第四句话也结束了。最后一句不会再单独发出去。`;
  const parts = splitReply(reply);
  assert.equal(parts.length, 2);
  assert.ok(parts.every((part) => [...part].length <= 360));
  assert.ok(parts[1].endsWith('…'));
});

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

test('only explicitly allowed groups receive isolated group replies', async () => {
  const asks = [];
  const sent = [];
  const unapprovedGroups = [];
  const adapter = new OfficialQqAdapter({
    bot: { sendText: async (target, text) => sent.push({ target, text }) },
    bridge: { ask: async (...args) => { asks.push(args); return '群里好呀'; } },
    allowed: () => false,
    unapproved: () => {},
    allowedGroup: (id) => id === 'approved-group',
    unapprovedGroup: (id) => unapprovedGroups.push(id),
  });
  const groupMessage = (messageId, groupOpenid, senderId = 'member') => ({
    kind: 'group',
    messageId,
    groupOpenid,
    senderId,
    senderName: '群成员',
    content: `<@!bot> 在吗`,
    rawEventType: 'GROUP_AT_MESSAGE_CREATE',
    replyTarget: { scope: 'group', targetId: groupOpenid, msgId: messageId },
  });

  adapter.handle(groupMessage('g1', 'unknown-group'));
  adapter.handle(groupMessage('g2', 'approved-group'));
  await new Promise((resolve) => setTimeout(resolve, 20));

  assert.deepEqual(unapprovedGroups, ['unknown-group']);
  assert.deepEqual(asks, [['qqgroup:approved-group', '在吗', '群聊：群成员']]);
  assert.deepEqual(sent, [{
    target: { scope: 'group', targetId: 'approved-group', msgId: 'g2' },
    text: '群里好呀',
  }]);
});
