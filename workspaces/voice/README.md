# 小白语音

当前本机链路为 **CosyVoice3 合成 → RVC 换声 → 直播舞台**。当前声线为使用新增说话素材训练的 `xiaobai_v2_curated` 第 30 轮。直播不再回退到晓伊；语音服务不可用时控制台阻止开始彩排或入场，运行中的某句合成失败则只显示字幕。

旧肥鱼模型、`xiaobai_v1` 的模型与训练目录以及淘汰的点歌实验，先集中移到项目根目录的 `待删除-旧声线与点歌实验/`，后由用户在资源管理器中删除；已核实该文件夹不存在。当前启动脚本和直播语音配置均不引用这些旧模型。

## 素材与模型

- 原始样音是用户提供的 `声音/1.mp3` 至 `声音/7.mp3`，约 32 分钟，保留原件。Demucs 清理后的人声在 `workspaces/voice/data/rvc-clean/`。
- CosyVoice3 的 6.4 秒参考片段是 `workspaces/voice/data/reference-clean.wav`；对应文字和语气提示在 `workspaces/voice/voice_config.json`。基础模型在 `models/Fun-CosyVoice3-0.5B-2512/`。
- RVC 旧实验 `xiaobai_v1` 有 522 段训练片段，完成了 40 轮训练。旧版模型、训练目录及配置已由用户删除；当前项目使用 `xiaobai_v2_curated` 第 30 轮。
- 新增的四段原始说话素材保存在 `声音/`，原文件未改动。`workspaces/voice/data/rvc-new-clean/` 是分离的人声；`outputs/voice-source-audit/curation-report.json` 记录逐段筛选结果。新实验 `xiaobai_v2_curated` 使用旧样音和新样音共 426 个筛选片段，预处理后为 936 段。当前选中的第 30 轮权重是 `vendor/rvc-official/assets/weights/xiaobai_v2_curated_e30_s6990.pth`，索引是 `vendor/rvc-official/logs/xiaobai_v2_curated/added_IVF3687_Flat_nprobe_1_xiaobai_v2_curated_v2.index`。运行参数见 `workspaces/voice/rvc_config.json`，索引混合比例为 0.6。

## 启动与查看

在项目根目录运行 `./workspaces/operations/Start-DS.ps1`。它会先尝试启动 RVC（`127.0.0.1:7392`）和 CosyVoice3（`127.0.0.1:7391`），再启动 DS 和本地控制台。控制台地址是 <http://127.0.0.1:3090/#live>，直播页显示声线的加载状态，并提供“加载小白声线”和“释放语音内存”按钮。彩排或正式开播前会自动加载声线。

两个常驻语音模型加载时，实测 Windows 可用内存从约 16.1 GB 降到 4.8 GB。语音模型空闲约两分钟后，控制台自动卸载；也可点“释放语音内存”。它只在未彩排、未公开直播时终止本项目的 CosyVoice3 与 RVC 服务，保留小白后台与点歌目录。下次彩排或入场时自动重新加载，冷启动实测约 46 秒。2026-11-05 再次卸载后可用内存回到约 16.7 GB。直播期间模型仍占用大量内存，点歌生成一次只处理一首。

2026-11-05 独立精度测试：同一句口语，CosyVoice3 FP32 峰值进程内存 7356 MB、CUDA 预留峰值 3630 MB；FP16 分别为 7361 MB、3832 MB，且生成更慢。因此直播仍用 FP32，不把 FP16 当作本机省内存开关。控制台重启后又做了手动加载、空闲自动卸载实测，卸载前后 Windows 可用内存约 5.4 GB → 15.2 GB。测试时小白未彩排、未开播。

2026-11-05 开播负载复测：32 GB 内存、8 GB 显存的本机上，语音模型就绪后 WSL 文件缓存约 3.5 GB；自动回收后约 0.8 GB，Windows 可用内存约 6.0 GB，声线仍可正常合成。控制台直播页每 15 秒显示内存与显存余量，彩排或直播期间低于 5 GB 可用内存时，会在语音服务空闲且没有点歌任务的时机尝试回收文件缓存，至少间隔 3 分钟，也可手动点“回收 WSL 文件缓存”。本地彩排中实测小白说话时 Windows 可用内存约 3.8–4.0 GB、剩余显存约 1.8–1.9 GB；尚未用具体游戏测试帧率，不能据此保证游戏流畅。CPU 版 RVC 处理约 4.8 秒音频的独立测试耗时约 37 秒，GPU 版首次约 16 秒、预热后约 7 秒，因此没有切换直播换声设备。结束彩排后已卸载语音模型。

单独检查服务：

```powershell
Invoke-RestMethod http://127.0.0.1:7391/health
Invoke-RestMethod http://127.0.0.1:7392/health
Invoke-RestMethod http://127.0.0.1:3090/api/voice
```

正常情况下，第一个接口返回 `ready: true`、`engine: cosyvoice3`、`rvc: true`；第二个接口返回 `model: xiaobai_v2_curated_e30_s6990.pth`。服务日志在 `outputs/xiaobai-voice-server*.log` 和 `outputs/xiaobai-rvc-server*.log`。

## 试听与彩排

- 基础合成试听：`outputs/xiaobai-clean-natural-tts.wav`。
- 当前第 30 轮换声试听：`outputs/xiaobai-clean-natural-rvc-v2.wav`。旧版试听：`outputs/xiaobai-clean-natural-rvc-e30.wav`。
- 通过直播插件、本机彩排和舞台事件获取的实际 MP3：`outputs/xiaobai-stage-rehearsal.mp3`。这段音频用于验证插件到舞台的链路，不代表公开直播已开播。
- 单句离线合成可用 `workspaces/voice/Render-Xiaobai.ps1`，但它每次加载模型，耗时和索引参数与常驻直播服务不同；判断直播效果应听舞台实录。

彩排只在本机播放。正式开播须先在 B 站连接直播和推流，再让小白入场；`workspaces/voice/check_stage_rehearsal.mjs` 仅用于本地舞台集成检查，会在结束时请求停止彩排。

## 当前限制

RVC 主要调整音色，不能修复上游合成的断句或咬字。实录已听到完整声音，但个别字的清晰度仍需继续改善。首句会有模型预热时间，常驻服务的短句生成目前仍需数秒；舞台合成超时已设为 60 秒，以免较长句子在 15 秒时被截断。语音服务不可用时会切换备用语音，排查时应核对控制台声线、服务健康和日志，避免把备用语音误判为 RVC 效果。

## 点歌

观众按歌名点现有歌曲时，小白声线模型不需要逐首重训。已通过用户试听的短片段可直接播放；未准备的歌由 `auto_prepare_song.py` 在后台检索 B 站视频、下载音频、截取约 35 秒、分离人声和伴奏、自动估调、换声与混音。直播插件的 `sing_prepared_song` 工具会在制作期间继续聊天，完成后把 MP3 送到本地舞台。控制台直播页可查看任务并试听。`cover_song.py` 仍可处理用户放在 `声音/点歌素材/` 的本地音频。

2026-11-04 本机验证：使用 B 站搜索结果中的《清明雨上》视频，通过 BBDownNext 本地 REST API 下载音频，再用 `cover_song.py` 完成 Demucs 分离、RVC 换声及混音。技术上生成了 218 秒 MP3，但用户试听发现整首有严重电子音，**该文件已拒收，不能作为直播素材**。用户选择的是新版声线、该歌低音段升 8 半音的 35 秒试听。粗略基频测量：新版训练语音的 p90 约 258 Hz、p99 约 310 Hz；该歌 60–90 秒副歌原唱 p90 约 384 Hz，升 8 半音后约 610 Hz，超出模型训练音域很多。这与高音处电子音相符，但不能只凭此断定每处杂音的来源；短片段也需要逐段听审。

`cover_song.py` 将 RVC 人声按 30 秒处理并交叉淡化，避免长歌一次推理卡住。`--backing-pitch` 默认跟随 `--pitch`。用户最终选定《清明雨上》用新版声线、`--pitch 8 --backing-pitch 8`，让人声与伴奏一起升 8 半音；60–95 秒的 35 秒副歌已通过用户试听。这个 +8 是此歌此片段的结果，其他歌需分别选取副歌时间和适合的调。只升人声 8 半音、伴奏保持原调会明显不和谐；换声后再降 8 半音则听起来像男声。脚本检查最终人声与伴奏是否同调，非同调组合只允许通过 `--allow-nonharmonic-experiment` 做本地比较。`--rvc-config` 可用于旧/新声线对照。现在必须显式指定 `--pitch`，默认只制作 35 秒试听；超过 45 秒须用 `--allow-long-experiment` 明确标为本地实验。输出 `settings.json` 的 `review_status` 区分试听通过、拒收和未审核。

直播不能等主人逐首听审。`song_clip_catalog.json` 逐首记录用户已听过的片段和各自音高；`song_request_policy.py` 先查目录，未知歌进入后台队列。自动制作一次只处理一首，最多再排三首，失败会告知观众换歌。生成品标为 `auto_checked`，表示已验证文件可解码、时长、体积和人声音量，**不代表听感已通过人工审查**。目前片段起点按歌曲时长约 28% 估算，无法保证恰好是副歌；音源选择、自动音高和高音电子音仍可能出错。公开直播播放第三方歌曲还需确认对应使用权限。

2026-11-05 本地彩排：模拟观众自然点《稻香》，小白将歌手和歌名分别传给工具，后台选中 B 站 BV1Qyt6zQEG9、生成 35 秒片段（估调 +10），舞台收到约 842 KB MP3，未进行公开开播。此前《星座书上》测试发现歌名和歌手可能被反传；改为独立参数后用《稻香》复测通过。`check_song_rehearsal.mjs` 可在本机重复该测试。

原创歌曲可用 `workspaces/voice/generate_song.py` 的 `--lyrics-file` 或 `--topic` 输入新歌词/主题，并指定 `--prompt`、`--bpm`、`--keyscale` 等；`workspaces/voice/prepare_original_song.py` 将生成、分离和换声串起来。此流程也仅用于离线准备。

2026-11-05 用户反馈《断桥残雪》约 20 秒的“断桥”、《晴天》27–33 秒的沙哑破音；第一轮改整体音高和去接缝仍未改善。两首保留在 `song_quality_holds.json`，直播点歌先跳过。用户认为《光年之外》新旧版差不多，暂用原版，已从拦截名单移除。第二轮使用较低的 RVC 内部音高，再将换声人声补升到与伴奏同调；试听对照见 `outputs/song-review/2026-11-05/README.md`，尚未确认听感。`cover_song.py --rvc-chunk-seconds 45` 可让 35 秒片段一次换声，排查 30 秒附近的接缝。普通说话的三段当前声线试听由 `render_speech_samples.py` 通过直播同一 TTS+RVC 服务生成，保存在 `outputs/speech-samples/2026-11-05/`。

进一步定位：《断桥残雪》第一次“断桥”的换声音高比原唱预期高近八度，第二次回落，造成主观上的突降；使用 `repair_cover_region.py` 生成只改其中一次的局部对照。《晴天》低内部升调版不破音但用户觉得失去小白音色；新增更小的升调分摊及 `--post-formant shifted` 对照。两首仍需听审，未替换自动点歌成品。

用户确认《断桥残雪》抬高第二次“断桥”的方向对，但局部拼接割裂；新候选 `review-duanqiao-f0-full` 由 `rvc_convert_f0_region.py` 在换声前修正 F0，然后对 35 秒人声一次合成。《晴天》两阶段音高修复均被否定，新候选 `review-qingtian-female-p0` 改用女声翻唱音源、重新分离，RVC 和伴奏保持原调。两者仍为本地未听审候选，策略继续拦截。

后续听审：《晴天》女声原调版获用户确认，已加入 `song_clip_catalog.json` 并解除音质拦截。《断桥残雪》第二次“断桥”在 F0 整段版被形容为声音像“卡出来”，不是停顿；该版在约 20.45–20.55 秒的人声能量明显塌陷，不作为新候选。`review-duanqiao-female-fcpe-p0` 改用女声原调演唱音源，重新分离，整段一次 RVC 换声；FCPE 避免了 RMVPE 在第一次“断”字的八度误判。此版只供本地听审，仍保持《断桥残雪》直播点歌拦截。

用户随后确认 `review-duanqiao-female-fcpe-p0` 的听感可以，已标为 `preferred_by_user`、收入 `song_clip_catalog.json` 并解除《断桥残雪》的音质拦截。历史未通过版本继续留作对照，不再被点歌解析选中。第三方歌曲公开播放的使用权限仍需由账号运营者确认。

三首新歌的本地全流程测速与试听路径见 `outputs/song-review/2026-11-05/benchmark.md`。试跑发现按原曲时长固定比例截取可能落在长伴奏段；`auto_prepare_song.py` 现用 `vocal_activity.py` 检查分离人声，失败时换位置重试。新歌仍标为 `auto_checked`，不等同用户听审通过。
