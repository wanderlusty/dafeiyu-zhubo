import { readFileSync } from 'node:fs';

const root = '/srv/xiaobai/data';
const envText = readFileSync(`${root}/opencode.env`, 'utf8');
const patchText = readFileSync(`${root}/dsh/profiles/web/cordis.patch.yml`, 'utf8');
const key = envText.match(/^OPENCODE_GO_API_KEY=(.+)$/m)?.[1];
const baseUrl = patchText.match(/^        baseURL: (https:\/\/\S+)$/m)?.[1];
if (!key || !baseUrl) throw new Error('Missing private API configuration');

const response = await fetch(`${baseUrl}/chat/completions`, {
  method: 'POST',
  headers: {
    authorization: `Bearer ${key}`,
    'content-type': 'application/json',
    'user-agent': 'Mozilla/5.0',
  },
  body: JSON.stringify({
    model: 'deepseek-v4.1-flash',
    messages: [{ role: 'user', content: '只回复 OK' }],
    max_tokens: 8,
    reasoning_effort: 'high',
  }),
  signal: AbortSignal.timeout(20000),
});
const data = await response.json().catch(() => ({}));
const ok = response.ok && Array.isArray(data.choices) && data.choices.length > 0;
console.log(JSON.stringify({ status: response.status, model_responded: ok }));
if (!ok) process.exitCode = 1;
