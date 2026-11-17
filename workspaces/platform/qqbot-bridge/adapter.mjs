const MAX_CHUNK = 1_500;
const MAX_REPLIES = 5;

export function splitReply(text) {
  const chars = [...text.trim()];
  const parts = [];
  while (chars.length && parts.length < MAX_REPLIES) {
    const last = parts.length === MAX_REPLIES - 1;
    const chunk = chars.splice(0, last && chars.length > MAX_CHUNK ? MAX_CHUNK - 1 : MAX_CHUNK);
    parts.push(chunk.join('') + (last && chars.length ? '…' : ''));
  }
  return parts;
}

export class OfficialQqAdapter {
  constructor({ bot, bridge, allowed, unapproved, logger = console }) {
    this.bot = bot;
    this.bridge = bridge;
    this.allowed = allowed;
    this.unapproved = unapproved;
    this.logger = logger;
    this.seen = new Map();
    this.queues = new Map();
  }

  handle(message) {
    if (message.kind !== 'c2c' || message.replyTarget?.scope !== 'c2c') return;
    const id = String(message.messageId ?? '');
    const sender = String(message.senderId ?? '');
    const content = String(message.content ?? '').trim();
    if (!id || !sender || !content) return;
    if (this.seen.has(id)) return;
    this.seen.set(id, Date.now());
    while (this.seen.size > 1_000) this.seen.delete(this.seen.keys().next().value);
    if (!this.allowed(sender)) {
      this.unapproved(sender);
      this.logger.warn('Unapproved QQ Bot sender ignored');
      return;
    }
    const prior = this.queues.get(sender) ?? Promise.resolve();
    const next = prior.catch(() => {}).then(async () => {
      const reply = await this.bridge.ask(`qqbot:${sender}`, content.slice(0, 4_000), String(message.senderName ?? 'QQ 用户').slice(0, 64));
      for (const part of splitReply(reply)) await this.bot.sendText(message.replyTarget, part);
    }).catch((error) => this.logger.error(`QQ Bot reply failed: ${error?.message ?? String(error)}`));
    this.queues.set(sender, next);
    next.finally(() => { if (this.queues.get(sender) === next) this.queues.delete(sender); });
  }
}
