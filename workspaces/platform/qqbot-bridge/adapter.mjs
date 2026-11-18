const MAX_CHUNK = 360;
const MAX_REPLIES = 2;
const INTERNAL_WINDOWS_PATH = /\b[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s，。！？；：]+/g;
const INTERNAL_POSIX_PATH = /(?<![A-Za-z])\/(?:srv|home|Users|var|tmp|opt|workspace)(?:\/[^\s，。！？；：]+)+/g;

export function sanitizeReply(text) {
  let cleaned = String(text ?? '').replace(/\r\n?/g, '\n').trim();
  if (!cleaned) return '';
  cleaned = cleaned
    .replace(/```[a-zA-Z0-9_-]*\s*/g, '')
    .replace(/```/g, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^(?:#{1,6}|>)\s*/gm, '')
    .replace(/^\s*(?:[-*+]|\d+\.)\s+/gm, '')
    .replace(/^\s*[-*_]{3,}\s*$/gm, '')
    .replace(/(\*\*|__)(.*?)\1/g, '$2')
    .replace(INTERNAL_WINDOWS_PATH, '这个位置')
    .replace(INTERNAL_POSIX_PATH, '这个位置')
    .replace(/\b(?:exec_command|apply_patch|function_call|tool_call|mcp__[a-z0-9_]+)\b/gi, '')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/([!?！？])\1{2,}/g, '$1')
    .trim();
  return cleaned || '我这边没整理出能直接说的内容，你换个问法试试。';
}

export function splitReply(text) {
  const chars = [...sanitizeReply(text).replace(/\n{3,}/g, '\n\n')];
  const parts = [];
  while (chars.length && parts.length < MAX_REPLIES) {
    const last = parts.length === MAX_REPLIES - 1;
    let size = last && chars.length > MAX_CHUNK ? MAX_CHUNK - 1 : Math.min(MAX_CHUNK, chars.length);
    if (last && chars.length > MAX_CHUNK) {
      const window = chars.slice(0, size).join('');
      const boundary = Math.max(window.lastIndexOf('。'), window.lastIndexOf('！'), window.lastIndexOf('？'), window.lastIndexOf('\n'));
      if (boundary >= 100) size = [...window.slice(0, boundary + 1)].length;
    }
    const chunk = chars.splice(0, size);
    parts.push(chunk.join('') + (last && chars.length ? '…' : ''));
  }
  return parts;
}

export class OfficialQqAdapter {
  constructor({ bot, bridge, allowed, unapproved, allowedGroup = () => false,
    unapprovedGroup = () => {}, logger = console }) {
    this.bot = bot;
    this.bridge = bridge;
    this.allowed = allowed;
    this.unapproved = unapproved;
    this.allowedGroup = allowedGroup;
    this.unapprovedGroup = unapprovedGroup;
    this.logger = logger;
    this.seen = new Map();
    this.queues = new Map();
  }

  handle(message) {
    const scope = message.replyTarget?.scope;
    const isGroup = message.kind === 'group' && scope === 'group';
    if (!isGroup && (message.kind !== 'c2c' || scope !== 'c2c')) return;
    const id = String(message.messageId ?? '');
    const sender = String(message.senderId ?? '');
    const group = String(message.groupOpenid ?? '');
    if (!id || !sender || (isGroup && !group)) return;
    if (this.seen.has(id)) return;
    this.seen.set(id, Date.now());
    while (this.seen.size > 1_000) this.seen.delete(this.seen.keys().next().value);
    if (isGroup) {
      if (!this.allowedGroup(group)) {
        this.unapprovedGroup(group);
        this.logger.warn('Unapproved QQ Bot group ignored');
        return;
      }
      const mentioned = message.rawEventType === 'GROUP_AT_MESSAGE_CREATE' ||
        (Array.isArray(message.mentions) && message.mentions.some((mention) => mention?.is_you === true));
      if (!mentioned) return;
    }
    let content = String(message.content ?? '').trim();
    if (isGroup) content = content.replace(/^<@!?[^>]+>\s*/, '') || '叫了你一下。';
    if (!content) return;
    if (!isGroup && !this.allowed(sender)) {
      this.unapproved(sender);
      this.logger.warn('Unapproved QQ Bot sender ignored');
      return;
    }
    const conversation = isGroup ? `qqgroup:${group}` : `qqbot:${sender}`;
    const from = isGroup
      ? `群聊：${String(message.senderName ?? '群成员').slice(0, 64)}`
      : String(message.senderName ?? 'QQ 用户').slice(0, 64);
    const prior = this.queues.get(conversation) ?? Promise.resolve();
    const next = prior.catch(() => {}).then(async () => {
      const reply = await this.bridge.ask(conversation, content.slice(0, 4_000), from);
      for (const part of splitReply(reply)) await this.bot.sendText(message.replyTarget, part);
    }).catch((error) => this.logger.error(`QQ Bot reply failed: ${error?.message ?? String(error)}`));
    this.queues.set(conversation, next);
    next.finally(() => { if (this.queues.get(conversation) === next) this.queues.delete(conversation); });
  }
}
