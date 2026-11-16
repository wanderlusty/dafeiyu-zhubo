const $ = (id) => document.getElementById(id);
document.querySelector('#live-save').insertAdjacentHTML('beforebegin', `
  <div class="cover-choice"><img src="/assets/live-cover-xiaobai.jpg" alt="小白直播封面预览"><label class="field"><span>直播封面 · 4:3</span><span class="cover-toggle"><input id="live-use-cover" type="checkbox" checked> 开播时使用这张封面</span></label></div>
  <div class="audio-settings"><h3>声音混合</h3><p class="muted">保存后，正在打开的舞台视频会立即采用新音量；小白的新句子采用新语音增益。</p>
    <div class="audio-fields"><label class="field"><span>视频常态音量 (%)</span><input id="live-video-volume" type="number" min="0" max="100" step="1" value="40"></label>
    <label class="field"><span>小白说话时视频音量 (%)</span><input id="live-video-duck" type="number" min="0" max="100" step="1" value="12"></label>
    <label class="field"><span>小白语音增益 (%)</span><input id="live-voice-gain" type="number" min="0" max="200" step="1" value="160"></label></div>
  </div>`);
$('live-save').textContent = '保存节目、声音与节奏';
document.querySelector('.audio-settings').insertAdjacentHTML('afterend', '<label class="field"><span>冷场后自己找话说（秒）</span><input id="live-idle-after" type="number" min="10" max="600" step="1" value="20"><small>从小白上一句说完起算；模型生成和语音合成还需要几秒。</small></label>');
$('live-start').textContent = '先开 B 站直播';
$('live-start').insertAdjacentHTML('afterend', '<button id="live-onair" class="button primary">观众到场后，让小白入场</button>');
const stageLink = document.createElement('a');
stageLink.id = 'live-open-stage';
stageLink.className = 'button ghost';
// Reuse the same audible stage tab when the button is clicked again.
stageLink.target = 'xiaobai-live-stage';
stageLink.textContent = '打开完整舞台（可听声音）';
stageLink.style.cssText = 'display:inline-flex;align-items:center;text-decoration:none';
$('live-copy-stage').after(stageLink);
document.querySelector('.preview').insertAdjacentHTML('afterend', '<p class="muted" id="stage-preview-help">这里是静音的缩略图。要听小白实时说话，先开始本地彩排，再打开完整舞台；若浏览器拦截声音，请在舞台页点“开启声音”。</p>');
document.querySelector('.broadcast-box p').textContent = '先向 B 站申请开播并推流。观众进来后，再点“让小白入场”；在此之前她不会自我介绍。';
document.querySelector('.voice-preview').insertAdjacentHTML('afterend', '<p id="stage-audio-warning" class="audio-warning" hidden></p>');
$('stage-audio-warning').insertAdjacentHTML('afterend', `
  <div class="voice-actions"><button id="voice-prepare" class="button ghost">加载小白声线</button><button id="voice-release" class="button ghost">释放语音内存</button><small>彩排或入场会自动加载；空闲约两分钟自动释放。</small></div>
  <div class="resource-panel"><strong>开播资源余量</strong><span id="resource-status">正在读取内存与显存…</span><small>显示 Windows 可用内存和显卡剩余显存。游戏是否流畅，还需用目标游戏做本地彩排。</small><button id="voice-reclaim-cache" class="button ghost">回收 WSL 文件缓存</button></div>
  <div class="voice-preview" id="song-preview">
    <strong>小白唱歌 · 本地试听</strong>
    <small>原创短版 · 当前小白声线（新素材训练第 30 轮）</small>
    <audio controls preload="none" src="/preview/xiaobai-song-clean.mp3"></audio>
    <details><summary>声线对比试听</summary>
      <small>同一首原创歌 · 旧版 v4</small>
      <audio controls preload="none" src="/preview/xiaobai-song-v4.mp3"></audio>
      <small>同一句日常说话 · 当前声线</small>
      <audio controls preload="none" src="/preview/xiaobai-speech-v2.wav"></audio>
    </details>
    <small>《彩虹》片段 · 小白第 30 轮声线换声</small>
    <audio controls preload="none" src="/preview/xiaobai-rainbow.mp3"></audio>
    <small>《彩虹》使用你放在本机的音频，试听只在本地；尚未接入直播自动演唱。</small>
    <details><summary>问题句对比试听</summary>
      <small>原创版 9–22 秒 · 当前版本</small>
      <audio controls preload="none" src="/preview/compare/xiaobai-v4.mp3"></audio>
      <small>原创版 9–22 秒 · 加强辅音保护</small>
      <audio controls preload="none" src="/preview/compare/xiaobai-v4-clear.mp3"></audio>
      <small>原创版 9–22 秒 · 保留原调，保护辅音和音量起伏</small>
      <audio controls preload="none" src="/preview/compare/xiaobai-v4-protect10.mp3"></audio>
      <small>原创版 9–22 秒 · 保留原调，降低音色检索权重</small>
      <audio controls preload="none" src="/preview/compare/xiaobai-v4-index30.mp3"></audio>
      <small>《彩虹》39–50 秒 · 原升调 8 半音</small>
      <audio controls preload="none" src="/preview/compare/rainbow-high.mp3"></audio>
      <small>《彩虹》39–50 秒 · 不升调，保留原唱音量起伏</small>
      <audio controls preload="none" src="/preview/compare/rainbow-low.mp3"></audio>
    </details>
  </div>`);
$('song-preview').insertAdjacentHTML('afterend', `
  <div class="voice-preview" id="song-request">
    <strong>按歌名点歌 · 片段准备情况</strong>
    <p class="muted">已备好的片段可直接唱；新歌会在后台搜索、下载、分离、估调并生成约 35 秒片段。自动检查只验证文件和音频结构，不能保证每句都好听。</p>
    <div class="form-row"><label class="field"><span>歌名或歌手</span><input id="song-query" type="text" maxlength="80" placeholder="例如：许嵩 清明雨上"></label></div>
    <button id="song-search" class="button ghost">检查点歌</button>
    <button id="song-prepare" class="button ghost">准备新歌并试听</button>
    <p id="song-result" class="muted">尚未查询。</p>
    <audio id="song-ready-audio" controls preload="none" hidden></audio>
  </div>`);
let csrf = '';
let state = {};
let qrPoll = null;
const dirtyFields = new Set();
const settingFields = ['qq-auto', 'qq-allow', 'bili-perday', 'bili-fetch', 'bili-night', 'bili-comment', 'live-title', 'live-room', 'live-area', 'live-kbps', 'live-use-cover', 'live-video-volume', 'live-video-duck', 'live-voice-gain', 'live-idle-after'];
for (const id of settingFields) {
  $(id).addEventListener('input', () => dirtyFields.add(id));
  $(id).addEventListener('change', () => dirtyFields.add(id));
}
function setField(id, value) {
  if (dirtyFields.has(id) || document.activeElement === $(id)) return;
  if ($(id).type === 'checkbox') $(id).checked = !!value;
  else $(id).value = value;
}

async function api(path, body) {
  const options = body === undefined ? {} : { method: 'POST', headers: { 'content-type': 'application/json', 'x-xiaobai-csrf': csrf }, body: JSON.stringify(body) };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || data.message || `请求失败 (${response.status})`);
  return data;
}

let noticeTimer;
function notify(message, bad = false) {
  const box = $('notice'); box.textContent = message; box.style.background = bad ? '#9d4037' : '#263747'; box.hidden = false;
  clearTimeout(noticeTimer); noticeTimer = setTimeout(() => { box.hidden = true; }, 5000);
}
function pill(id, text, tone = '') { const el = $(id); el.textContent = text; el.className = `pill ${tone}`; }
function showPage(name) {
  document.querySelectorAll('.nav').forEach(n => n.classList.toggle('active', n.dataset.page === name));
  document.querySelectorAll('.page').forEach(n => n.classList.toggle('active', n.id === name));
  const titles = { overview: ['今天，小白在做什么？', '聊天、发现视频、直播准备，都在这里查看。'], qq: ['QQ 聊天', '查看小白和你的连接、回复开关与白名单。'], bili: ['B 站刷视频', '浏览设置、视频记录和当日发现。'], live: ['B 站直播', '从彩排到正式推流，按步骤准备。'] };
  $('page-title').textContent = titles[name][0]; $('page-subtitle').textContent = titles[name][1];
  history.replaceState(null, '', `#${name}`);
  if (name === 'bili') loadBiliDetails();
}
document.querySelectorAll('.nav').forEach(n => n.onclick = () => showPage(n.dataset.page));
document.querySelectorAll('[data-go]').forEach(n => n.onclick = () => showPage(n.dataset.go));

async function refresh() {
  const names = [['qq', '/api/qq'], ['bili', '/api/bili'], ['live', '/api/live'], ['account', '/api/live/account'], ['room', '/api/live/room-info'], ['voice', '/api/voice']];
  const results = await Promise.allSettled(names.map(([, path]) => api(path)));
  names.forEach(([name], index) => { state[name] = results[index].status === 'fulfilled' ? results[index].value : { error: results[index].reason.message }; });
  render();
}
async function refreshResources() {
  try {
    const resources = await api('/api/resources');
    const ram = (resources.freeRamMiB / 1024).toFixed(1);
    const gpu = resources.gpu ? ` · 显存剩余 ${(resources.gpu.freeMiB / 1024).toFixed(1)} GB / ${(resources.gpu.totalMiB / 1024).toFixed(1)} GB` : ' · 显存不可用';
    const low = resources.freeRamMiB < 4096 || (resources.gpu && resources.gpu.freeMiB < 2048);
    const element = $('resource-status');
    element.textContent = `内存可用 ${ram} GB / ${(resources.totalRamMiB / 1024).toFixed(1)} GB${gpu}${low ? ' · 余量偏低' : ''}`;
    element.classList.toggle('resource-low', !!low);
  } catch (error) { $('resource-status').textContent = `资源读取失败：${error.message}`; }
}
function render() {
  const qq = state.qq || {}, bili = state.bili || {}, live = state.live || {}, account = state.account?.account;
  const voice = state.voice || {};
  const voiceLabel = voice.ready && voice.rvc ? '小白 · CosyVoice3 + RVC（已加载）' : '小白 · CosyVoice3 + RVC（待加载，彩排或入场时自动启动）';
  document.querySelector('.voice-preview strong').textContent = `直播声线：${voiceLabel}`;
  const voiceAudio = document.querySelector('.voice-preview audio');
  const previewUrl = '/preview/xiaobai-rvc.wav';
  if (voiceAudio.getAttribute('src') !== previewUrl) voiceAudio.setAttribute('src', previewUrl);
  pill('qq-pill', qq.error ? '连接异常' : qq.connected ? '已连接' : '未连接', qq.connected ? 'ok' : 'bad');
  pill('qq-state', qq.connected ? '已连接' : '未连接', qq.connected ? 'ok' : 'bad');
  $('qq-summary').textContent = qq.error || (qq.connected ? `自动回复${qq.autoReply ? '开启' : '关闭'} · 已发 ${qq.sent || 0} 条` : 'QQ 通道尚未连接');
  $('qq-connection').textContent = qq.connected ? '在线' : '离线'; $('qq-sent').textContent = qq.sent ?? '—'; $('qq-conversations').textContent = qq.conversations ?? '—';
  if (!qq.error) { setField('qq-auto', qq.autoReply); setField('qq-allow', (qq.allowPrivateIds || []).join(', ')); }
  $('qq-last').textContent = qq.lastError || (qq.lastEventAt ? `最近消息：${new Date(qq.lastEventAt).toLocaleString('zh-CN')}` : '还没有收到消息');
  $('qq-home').textContent = state.world?.life?.homeSessionId || '读取中';
  pill('bili-pill', bili.error ? '连接异常' : bili.loggedIn ? '已登录' : '未登录', bili.loggedIn ? 'ok' : 'warn');
  pill('bili-state', bili.running ? '浏览中' : bili.loggedIn ? '已登录' : '未登录', bili.loggedIn ? 'ok' : 'warn');
  $('bili-summary').textContent = bili.error || `今天挑了 ${bili.pickedToday ?? 0} 条 · ${bili.running ? '正在浏览' : '等待下次浏览'}`;
  $('bili-picked').textContent = bili.pickedToday ?? '—'; $('bili-left').textContent = bili.autoLeft ?? '—'; $('bili-running').textContent = bili.running ? '进行中' : '空闲';
  if (!bili.error) { setField('bili-perday', bili.config?.perDay ?? 1); setField('bili-fetch', bili.config?.fetchPerRound ?? 2); setField('bili-night', bili.config?.night); setField('bili-comment', bili.config?.autoComment); }
  $('workspace-path').textContent = bili.config?.workspace || '—';
  const phase = live.broadcast?.phase || 'idle';
  const onAir = !!live.show?.onAir;
  const roomLive = live.show?.live?.stats?.live === true;
  const label = roomLive ? (onAir ? '小白正在直播' : 'B 站已开播，等待小白入场') : onAir ? '本地彩排中' : phase === 'face' ? '等待人脸验证' : phase === 'preparing' ? '开播准备中' : '未开播';
  pill('live-pill', label, phase === 'streaming' ? 'ok' : onAir || phase === 'preparing' ? 'warn' : '');
  pill('live-state', label, phase === 'streaming' ? 'ok' : onAir || phase === 'preparing' ? 'warn' : '');
  $('live-summary').textContent = live.error || `${account?.name ? account.name + ' · ' : ''}${label}`;
  $('live-step').textContent = roomLive && !onAir ? `B 站已开播 · 在线 ${live.show?.live?.stats?.online ?? '—'} 人。观众到场后点“让小白入场”。` : live.broadcast?.step || (onAir ? '小白已进入舞台，正在等待互动。' : account ? (state.room?.roomId ? `直播间 ${state.room.roomId} · 分区 ${live.settings?.areaId || state.room.preLive?.areaId || '待选择'}` : '账号已登录，尚无直播间；正式开播时将尝试开通。') : '扫码登录后，先在本地彩排。');
  $('live-account').textContent = account?.name ? `${account.name} (${account.uid})` : '直播账号未登录';
  if (!live.error) {
    setField('live-title', live.settings?.liveTitle || ''); setField('live-room', live.settings?.roomId || state.room?.roomId || '');
    setField('live-area', live.settings?.areaId || state.room?.preLive?.areaId || '');
    setField('live-kbps', live.settings?.streamKbps || 4500);
    setField('live-use-cover', !!live.settings?.liveCover);
    setField('live-video-volume', Math.round((live.settings?.videoVolume ?? 0.4) * 100));
    setField('live-video-duck', Math.round((live.settings?.videoDuckVolume ?? 0.12) * 100));
    setField('live-voice-gain', Math.round((live.settings?.voiceGain ?? 1.6) * 100));
    setField('live-idle-after', live.settings?.idleAfterSec ?? 45);
  }
  $('live-phase').textContent = roomLive && phase !== 'streaming' ? 'LIVEHIME' : phase.toUpperCase();
  const audioWarning = $('stage-audio-warning');
  const speakers = Number(live.show?.stageWatchers || 0);
  audioWarning.hidden = speakers <= 1;
  audioWarning.textContent = speakers > 1 ? `当前有 ${speakers} 个舞台页连接。若听到重音或发闷，请关掉多余的舞台标签页；控制台里的预览是静音的。` : '';
  const face = $('face-qr');
  face.hidden = phase !== 'face' || !live.broadcast?.faceQrData;
  if (!face.hidden) $('face-qr-image').src = live.broadcast.faceQrData;
  $('live-error').hidden = roomLive || !live.broadcast?.error; $('live-error').textContent = roomLive ? '' : live.broadcast?.error || '';
  if (live.stageUrl) {
    const previewUrl = new URL(live.stageUrl);
    previewUrl.searchParams.set('preview', '1');
    if ($('stage-preview').src !== previewUrl.href) $('stage-preview').src = previewUrl.href;
    stageLink.href = live.stageUrl;
  } else {
    stageLink.removeAttribute('href');
  }
  $('live-rehearsal').disabled = phase === 'preparing' || phase === 'face' || phase === 'streaming' || onAir || roomLive;
  $('live-start').disabled = phase === 'preparing' || phase === 'face' || phase === 'streaming' || onAir || roomLive;
  $('live-onair').disabled = !roomLive || onAir;
  $('live-stop').disabled = phase !== 'streaming';
  $('live-offair').textContent = roomLive ? '让小白退场（直播姬继续播）' : '结束彩排 / 下播';
}
async function loadWorld() { try { state.world = await api('/api/world'); $('qq-home').textContent = state.world.life?.homeSessionId || '—'; } catch {} }
async function loadBiliDetails() {
  try {
    const [watched, report] = await Promise.all([api('/api/bili/watched'), api('/api/bili/report')]);
    $('watched-count').textContent = `${watched.total || 0} 条记录`;
    const list = $('watched-list'); list.replaceChildren();
    if (!watched.rows?.length) list.textContent = '还没有浏览记录。';
    for (const row of watched.rows || []) {
      const item = document.createElement('div'); item.className = 'watched-item';
      const left = document.createElement('div'); left.textContent = row.title || row.bvid || '未命名视频';
      const right = document.createElement('small'); right.textContent = `${row.bvid || ''} · ${row.picked ? '挑中' : '跳过'}`;
      item.append(left, right); list.append(item);
    }
    $('bili-report').textContent = report.exists ? report.text : '今天还没有报告。';
  } catch (error) { $('bili-report').textContent = error.message; }
}
async function action(path, body, done = '已完成', clear = []) {
  try { await api(path, body); clear.forEach(id => dirtyFields.delete(id)); notify(done); await refresh(); }
  catch (error) { notify(error.message, true); }
}

$('refresh').onclick = () => refresh().then(() => notify('状态已刷新')).catch(e => notify(e.message, true));
$('qq-save').onclick = () => action('/api/qq/settings', { autoReply: $('qq-auto').checked, allowPrivate: $('qq-allow').value.split(/[，,\s]+/).filter(Boolean) }, 'QQ 设置已保存', ['qq-auto', 'qq-allow']);
$('bili-save').onclick = () => action('/api/bili/settings', { perDay: Number($('bili-perday').value), fetchPerRound: Number($('bili-fetch').value), night: $('bili-night').checked, autoComment: $('bili-comment').checked }, '刷视频设置已保存', ['bili-perday', 'bili-fetch', 'bili-night', 'bili-comment']);
$('bili-run').onclick = () => action('/api/bili/run', {}, '已请求手动浏览，请稍后看报告');
$('bili-report-refresh').onclick = loadBiliDetails;
$('live-save').onclick = () => action('/api/live/settings', { liveTitle: $('live-title').value, ...(Number($('live-room').value) > 0 ? { roomId: Number($('live-room').value) } : {}), areaId: Number($('live-area').value) || null, streamKbps: Number($('live-kbps').value), useCover: $('live-use-cover').checked, videoVolume: Number($('live-video-volume').value) / 100, videoDuckVolume: Number($('live-video-duck').value) / 100, voiceGain: Number($('live-voice-gain').value) / 100, idleAfterSec: Number($('live-idle-after').value) }, '直播设置已保存', ['live-title', 'live-room', 'live-area', 'live-kbps', 'live-use-cover', 'live-video-volume', 'live-video-duck', 'live-voice-gain', 'live-idle-after']);
$('live-import').onclick = () => action('/api/live/login/import-duty', {}, '已沿用刷视频账号的登录态');
async function startWithVoice(button, path, done, body = {}) {
  const label = button.textContent;
  button.disabled = true;
  button.textContent = '正在加载小白声线…';
  notify('正在加载小白声线，首次可能需要约一分钟');
  try { await api(path, body); notify(done); await refresh(); }
  catch (error) { notify(error.message, true); }
  finally {
    button.textContent = label;
    button.disabled = false;
    if (button.id === 'live-rehearsal' || button.id === 'live-onair' || button.id === 'live-start') render();
  }
}
$('live-rehearsal').onclick = () => startWithVoice($('live-rehearsal'), '/api/live/rehearsal/start', '本地彩排已启动');
$('voice-prepare').onclick = () => startWithVoice($('voice-prepare'), '/api/voice/prepare', '小白声线已加载');
$('voice-release').onclick = () => action('/api/voice/release', {}, '语音内存已释放');
$('voice-reclaim-cache').onclick = async () => {
  const button = $('voice-reclaim-cache');
  button.disabled = true;
  try { await api('/api/resources/reclaim', {}); await refreshResources(); notify('WSL 文件缓存已回收，声线仍在运行'); }
  catch (error) { notify(error.message, true); }
  finally { button.disabled = false; }
};
$('live-obs').onclick = async () => { try { const r = await api('/api/live/obs/check', {}); notify(r.ok ? 'OBS 画面检查通过' : 'OBS 检查未通过'); await refresh(); } catch (e) { notify(e.message, true); } };
$('live-copy-stage').onclick = async () => {
  try {
    if (!state.live?.stageUrl) await refresh();
    if (!state.live?.stageUrl) throw new Error('小白舞台尚未启动，请先启动小白服务');
    await navigator.clipboard.writeText(state.live.stageUrl);
    notify('小白舞台地址已复制，请粘贴到直播姬的浏览器 URL');
  } catch (error) { notify(`复制失败：${error.message}`, true); }
};
stageLink.onclick = (event) => {
  if (stageLink.href) return;
  event.preventDefault();
  notify('小白舞台尚未启动，请先启动小白服务', true);
};
$('live-sim').onclick = () => action('/api/live/simulate', { kind: 'chat', name: $('sim-name').value, text: $('sim-text').value }, '测试弹幕已发送');
$('live-offair').onclick = () => action('/api/live/offair', {}, '已请求结束彩排 / 下播');
$('live-start').onclick = async () => { if (!confirm('将先在 B 站开播并启动 OBS。小白会等待你手动让她入场。确认开播吗？')) return; await startWithVoice($('live-start'), '/api/live/broadcast/start', '正在连接 B 站；小白仍在等待', { confirm: '开播' }); };
$('live-onair').onclick = () => startWithVoice($('live-onair'), '/api/live/broadcast/onair', '小白开始入场');
$('live-stop').onclick = () => action('/api/live/broadcast/stop', {}, '已停止推流');
$('song-search').onclick = async () => {
  const query = $('song-query').value.trim();
  if (!query) { $('song-result').textContent = '请先输入歌名。'; return; }
  try {
    const decision = await api(`/api/song/resolve?q=${encodeURIComponent(query)}`);
    const audio = $('song-ready-audio');
    if (decision.decision === 'play_prepared_clip') {
      $('song-result').textContent = `已备好《${decision.title}》的 ${decision.duration} 秒片段，人声升 ${decision.pitch}、伴奏升 ${decision.backing_pitch} 个半音；点歌策略会自动选择这版。`;
      audio.src = `/preview/song?q=${encodeURIComponent(query)}`;
      audio.hidden = false;
      return;
    }
    audio.pause(); audio.removeAttribute('src'); audio.hidden = true;
    $('song-result').textContent = decision.decision === 'prepare_in_background'
      ? '这首歌还没备好。直播点歌会在后台自动准备；你也可以点“准备新歌并试听”做本机测试。'
      : decision.reply || '这首歌暂时不能准备。';
  } catch (error) { $('song-result').textContent = error.message; }
};
$('song-prepare').onclick = async () => {
  const query = $('song-query').value.trim();
  if (!query) { $('song-result').textContent = '请先输入歌名。'; return; }
  try {
    const requested = await api('/api/song/request', { query });
    if (requested.decision === 'play_prepared_clip') { $('song-search').click(); return; }
    if (requested.decision === 'decline') { $('song-result').textContent = requested.reply; return; }
    $('song-result').textContent = `《${query}》已加入后台任务，正在准备。`;
    for (let count = 0; count < 120; count++) {
      const job = await api(`/api/song/job?id=${encodeURIComponent(requested.id)}`);
      if (job.status === 'ready') {
        $('song-result').textContent = `《${query}》已生成 ${job.result.duration} 秒片段（自动估调 +${job.result.pitch}）。已通过文件检查，尚未经人工听审。`;
        const audio = $('song-ready-audio');
        audio.src = `/api/song/audio?id=${encodeURIComponent(requested.id)}`;
        audio.hidden = false;
        return;
      }
      if (job.status === 'failed') { $('song-result').textContent = `准备失败：${job.error}`; return; }
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
    $('song-result').textContent = '准备超时，可以稍后再试。';
  } catch (error) { $('song-result').textContent = error.message; }
};
$('song-query').addEventListener('keydown', event => { if (event.key === 'Enter') $('song-search').click(); });

// 试听和舞台一样，用 Web Audio 直接加音量，不重新压缩音频。
const voicePreview = document.querySelector('.voice-preview audio');
let previewContext;
let previewGain;
voicePreview.addEventListener('play', () => {
  try {
    if (!previewContext) {
      previewContext = new AudioContext();
      previewGain = previewContext.createGain();
      previewContext.createMediaElementSource(voicePreview).connect(previewGain).connect(previewContext.destination);
    }
    previewGain.gain.value = Number($('live-voice-gain').value) / 100;
    void previewContext.resume();
  } catch { /* 不支持 Web Audio 时仍能播放原声 */ }
});
$('live-voice-gain').addEventListener('input', () => {
  if (previewGain && previewContext) previewGain.gain.setTargetAtTime(Number($('live-voice-gain').value) / 100, previewContext.currentTime, 0.01);
});
$('live-login').onclick = async () => {
  try {
    const r = await api('/api/live/login/start', {});
    $('qr-image').replaceChildren(); const image = document.createElement('img'); image.src = r.qrData; image.alt = 'B 站登录二维码'; $('qr-image').append(image);
    $('live-qr').hidden = false; $('qr-status').textContent = '请用 B 站 App 扫码并确认';
    clearInterval(qrPoll); qrPoll = setInterval(async () => {
      try {
        const result = await api('/api/live/login/poll', { key: r.key });
        if (result.state === 'ok') { clearInterval(qrPoll); $('live-qr').hidden = true; notify('B 站直播账号登录成功'); await refresh(); }
        else if (result.state === 'expired' || result.state === 'error') { clearInterval(qrPoll); $('qr-status').textContent = result.message || '二维码已过期，请重新获取'; }
        else $('qr-status').textContent = result.state === 'scanned' ? '已扫码，请在手机上确认' : '请用 B 站 App 扫码并确认';
      } catch (error) { clearInterval(qrPoll); notify(error.message, true); }
    }, 2200);
  } catch (error) { notify(error.message, true); }
};

(async () => { try { csrf = (await api('/api/bootstrap')).csrf; await Promise.all([refresh(), loadWorld(), refreshResources()]); if (location.hash && document.querySelector(`.nav[data-page="${location.hash.slice(1)}"]`)) showPage(location.hash.slice(1)); setInterval(refresh, 60000); setInterval(refreshResources, 15000); } catch (error) { notify(error.message, true); } })();
