import { WebSocket } from 'ws';

export class BridgeClient {
  constructor({ url, token, timeoutMs = 10 * 60_000, logger = console }) {
    this.url = url;
    this.token = token;
    this.timeoutMs = timeoutMs;
    this.logger = logger;
    this.socket = null;
    this.ready = false;
    this.stopped = false;
    this.reconnectMs = 1_000;
    this.pending = new Map();
    this.waiters = new Set();
  }

  start() { this.connect(); }

  connect() {
    if (this.stopped || this.socket) return;
    const socket = new WebSocket(this.url);
    this.socket = socket;
    socket.on('open', () => socket.send(JSON.stringify({ kind: 'hello', token: this.token })));
    socket.on('message', (raw) => this.receive(raw));
    socket.on('error', () => this.logger.warn('DSH bridge socket error'));
    socket.on('close', () => {
      if (this.socket !== socket) return;
      this.socket = null;
      this.ready = false;
      for (const item of this.pending.values()) item.reject(new Error('DSH bridge disconnected'));
      this.pending.clear();
      if (!this.stopped) {
        setTimeout(() => this.connect(), this.reconnectMs).unref();
        this.reconnectMs = Math.min(this.reconnectMs * 2, 30_000);
      }
    });
  }

  receive(raw) {
    let frame;
    try { frame = JSON.parse(String(raw)); }
    catch { return; }
    if (frame.kind === 'ready') {
      this.ready = true;
      this.reconnectMs = 1_000;
      for (const wake of this.waiters) wake();
      this.waiters.clear();
      return;
    }
    const item = this.pending.get(frame.threadId);
    if (!item) return;
    if (frame.kind === 'error') {
      item.reject(new Error(`DSH bridge rejected message: ${String(frame.message).slice(0, 160)}`));
      this.pending.delete(frame.threadId);
    } else if (frame.kind === 'reply' && !frame.hold) {
      item.resolve(typeof frame.text === 'string' ? frame.text : '');
      this.pending.delete(frame.threadId);
    }
  }

  async whenReady() {
    if (this.ready) return;
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.waiters.delete(wake);
        reject(new Error('DSH bridge unavailable'));
      }, 30_000);
      timer.unref();
      const wake = () => { clearTimeout(timer); resolve(); };
      this.waiters.add(wake);
    });
  }

  async ask(threadId, text, from) {
    await this.whenReady();
    if (this.pending.has(threadId)) throw new Error('Concurrent request for the same QQ conversation');
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(threadId);
        reject(new Error('DSH reply timed out'));
      }, this.timeoutMs);
      timer.unref();
      const item = {
        resolve: (value) => { clearTimeout(timer); resolve(value); },
        reject: (error) => { clearTimeout(timer); reject(error); },
      };
      this.pending.set(threadId, item);
      try {
        this.socket.send(JSON.stringify({ kind: 'message', threadId, text, from }));
      } catch (error) {
        this.pending.delete(threadId);
        item.reject(error);
      }
    });
  }

  stop() {
    this.stopped = true;
    this.socket?.close();
    for (const item of this.pending.values()) item.reject(new Error('DSH bridge stopped'));
    this.pending.clear();
  }
}
