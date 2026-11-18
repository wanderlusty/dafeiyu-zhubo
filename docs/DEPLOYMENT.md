# 本地数据与部署边界

## GitHub 上传范围

仓库保存脚本、控制台源码、配置示例、角色设定和直播插件源码补丁。本机数据实体统一放在 `local-data/`，根目录旧路径是隐藏的 NTFS 目录联接。`.gitignore` 排除了登录态、浏览器 profile、密钥、模型权重、样音、歌曲片段、生成视频、第三方仓库与安装包。上传前仍须检查 `git status` 和暂存清单；不要用 `git add -f` 强行加入被忽略的文件。

本机可复用但必须私下处理的内容：

| 内容 | 本机位置 | 原因 |
| --- | --- | --- |
| DSH 和 B 站登录态 | `local-data/accounts/.dsh-home/` | 含凭据与账户状态。迁移时重新登录更安全。 |
| QQ OneBot / SnowLuma 登录态 | 项目目录之外的本机安装位置 | 账号登录由持有人在新机器完成。 |
| 语音模型、RVC 权重与索引 | `local-data/dependencies/models/`、`local-data/dependencies/vendor/rvc-official/` | 体积大，需独立存储并核对授权。 |
| 原声样音、训练/分离数据 | `local-data/media/声音/`、`workspaces/voice/data/`、`workspaces/voice/separated/` | 个人/授权素材，不进公开仓库。 |
| 歌曲与点歌缓存 | `local-data/generated/outputs/covers/`、`workspaces/voice/song_clip_catalog.json` | 包含第三方音乐内容。 |
| 直播封面与第三方动画 | `local-data/media/assets/`、上游插件素材 | 按素材各自许可证处理。 |
| 当前定制插件包 | `local-data/dependencies/vendor/overrides/` | 需要从源码重建或私下迁移。 |

## 在另一台 Windows 机器上

1. 克隆仓库，安装 Node、pnpm、Python/uv、WSL 和所需音频依赖。
2. 按 `docs/HANDOFF.md` 还原直播插件源码，并准备定制 `dsh-bili-scroll` 包。把构建结果放到 `vendor/overrides/`，或者修改 `workspaces/operations/Setup-Local.ps1` 为新的包路径与哈希。
3. 从 `.example` 文件生成本机配置，填写正确的路径。账号、API Key、Cookie、QQ 白名单只能写入本机私有配置/凭据库。
4. 准备授权的语音模型与参考音频；用 `workspaces/voice/voice_config.json`、`workspaces/voice/rvc_config.json` 指向新机器路径。
5. 执行 `workspaces/operations/Setup-Local.ps1`，完成账号登录，再用根目录的 `启动小白.cmd` 启动。先验证控制台、QQ、刷视频和本地彩排，然后决定是否开播。

`workspaces/operations/Setup-Local.ps1` 会在本机配置缺失时选用脱敏示例；示例默认关闭 QQ 自动回复。两个定制插件包缺失时会明确报错，不会假称直播功能安装完成。

如使用 OpenCode Go 的自定义中转地址，把 HTTPS base URL 单独写入被 Git 忽略的 `local-data/accounts/opencode-go-base-url.txt`，每行仅一个地址。`Enable-OpenCode-Go.ps1` 会把它应用到网页、B 站值班及插件的值班模板；API Key 仍需保存在 DSH 私有凭据库的 `OPENCODE_GO_API_KEY` 引用中。重新运行 `Setup-Local.ps1` 后也会恢复该私有地址。

## 个人服务器：ECS 最小后台（2026-11-16）

当前阿里云杭州 ECS 为 Ubuntu 22.04、2 vCPU、4 GiB。`/srv/xiaobai/app` 是源码，`/srv/xiaobai/data` 是服务器私有数据。Node.js 24、DSH `0.2.1-rc.5`、`dsh-world` 和 QQ SDK 已安装。`xiaobai-dsh.service` 以非 root 用户运行并开机自启；Web 只监听 `127.0.0.1:3081`。模型中转 API 已从本机私有凭据库配置到服务器私有环境文件，服务器上模型响应测试返回 HTTP 200。不要把 `/srv/xiaobai/data` 加入 Git 或公开备份。

QQ 使用 `ghcr.io/napneko/nodenapcat:latest` 镜像，镜像摘要为 `sha256:43e600211bc1ab273e9b2fc68776359d6cfbf03f99ba0f7cf52f3c99add51316`。QQ 账号资料持久化在 `/srv/xiaobai/data/napcat/`。OneBot 3001 和 WebUI 6099 只映射到服务器 `127.0.0.1`，本机通过 SSH 转发访问；无需在 ECS 安全组开放这两个端口。QQ 容器重启后可能要求手机再次验证，须核对 OneBot 真正监听并收到消息，不能仅凭容器运行状态判定 QQ 在线。

2026-11-16 已实测：私聊白名单只允许用户主号，自动回复开启；用户从主号发送测试私聊后收到回复，服务端计数为 `sent=1`、`failed=0`。实际 QQ 号仅保存在服务器私有配置中。服务器私有配置 `/srv/xiaobai/data/dsh/profiles/web/cordis.patch.yml` 使用 `bindHomeSession: none`，让 QQ 私聊保持独立会话。原先绑定主会话时，主会话卡在一条写日记的待审批请求上，QQ 消息已收到但无法生成回复。主会话的待审批任务仍需单独处理；这次验收只证明 QQ 私聊收发，不代表自主日程和长期稳定运行已验收。无需重启 QQ 容器来调整 DSH 的私聊绑定。

2026-11-17 白天发现普通 QQ 小号在服务器上掉线：DSH 服务与 NapCat 容器都还在运行，但 OneBot WebSocket 已断开，手机登录又要求身份验证。用户扫码后普通 QQ 恢复连接；当天再次通过 OneBot `get_login_info`、DSH 状态和主号真实私聊回复验收。**这仍不等于连续 24 小时稳定性验收。**不要仅凭 systemd / Docker 的“运行中”推断 QQ 能回复。

腾讯开放平台官方 QQ Bot 已与普通 QQ 小号并行接入。适配器源码在 `workspaces/platform/qqbot-bridge/`，使用腾讯官方 Node SDK 接收 C2C 私聊，再经 DSH 本地桥送进小白角色工作区。ECS 的 `xiaobai-qqbot.service` 已启用开机自启并处于 `active`，私有凭据文件权限为 `0600`，官方 openid 白名单当前只有用户确认的一个发送者。2026-11-17 用户从主号向官方 Bot 发送真实私聊并收到回复；单独重启官方 Bot 服务后，网关恢复并再次收到真实回复。普通 QQ 也在同日完成真实私聊回复，两者都保持运行。官方机器人是新身份，不会继承原普通 QQ 小号的好友关系。2026-11-18 源码新增默认关闭的群白名单和仅 @ 响应；`allowed-groups.json` 初始为空，必须由群管理者同意并人工确认 group openid 后才加入。群聊尚未做真实平台验收。

2026-11-17 已在 ECS 私有世界目录安装 QQ／刷视频／直播的分域记忆模板；服务器当前只运行 QQ，刷视频与直播仍由本机负责。安装器 `workspaces/operations/server/install-memory-layout.py` 只新建缺失的场景文档；旧统一 `AGENTS.md` 匹配已知模板才备份并迁移，已有自写的 `我是谁.md` 仅替换过时段落并留备份。详细三层模型及旧归档限制见 [`MEMORY_ARCHITECTURE.md`](MEMORY_ARCHITECTURE.md)。后续从 Git 更新后可运行：

```bash
python3 /srv/xiaobai/app/workspaces/operations/server/install-memory-layout.py --world /srv/xiaobai/data/dsh/worlds/ds --migrate-self --migrate-persona
python3 /srv/xiaobai/app/workspaces/operations/server/check-memory-layout.py --world /srv/xiaobai/data/dsh/worlds/ds --config /srv/xiaobai/data/dsh/profiles/web/cordis.patch.yml --workspaces /srv/xiaobai/data/dsh/storages/workspace.json --bili-config /srv/xiaobai/data/dsh/bili-duty/config.json
```

小白不能直接写工作区上一级的旧 `diary/`，因为 DSH 的 `workspace-write` 只覆盖 `room/`。服务器应保持该权限，运行 [`migrate-diary-into-room.py`](DIARY-PERMISSION.md) 把标准日期日记复制到 `room/diary/` 并把 `diaryDir` 指过去；不要为了省事改成 `danger-full-access`。

本机 `Setup-Local.ps1` 将刷视频 `workspace` 设到真实的 `worlds/ds/bili-duty`，并同步修正网页 profile 中的 `bili-scroll` 配置；直播定制包 v13 将新直播会话设到 `worlds/ds/live`。**未公开开播**；第二次本地彩排的开场说话已通过，但首句约 24.7 秒且动态提问未单独验收，见 [`VOICE-CHECK-2026-11-17.md`](VOICE-CHECK-2026-11-17.md)。旧 `archive.sqlite` 与全局 `diary/` 保留，历史内容可能仍可跨场景检索。

官方 Bot 的安装、私有凭据轮换和新发送者授权步骤见 [`QQ Bot 接入说明`](../workspaces/platform/qqbot-bridge/README.md)。需要重录凭据时在 ECS Workbench 终端运行 `python3 /srv/xiaobai/app/workspaces/operations/server/configure-qqbot-credentials.py`，在终端输入 AppID 和隐藏输入的 AppSecret；**不要把 AppSecret 发到聊天或写进 Git**。脚本从 DSH 私有世界目录读取桥口令，写入权限 `0600` 的 `/srv/xiaobai/data/qqbot/qqbot.env`，并创建 openid/group 的 private 白名单与待审文件。任何新增发送者都要先核对 `pending-openids.json`，任何新增群都要先核对 `pending-groups.json` 并取得群管理者同意。用户要求官方 Bot 与普通 QQ 小号并行运行，不要因官方 Bot 已可用而关闭旧接入。

本机 SSH 隧道将 `127.0.0.1:6099` 转发到服务器 QQ WebUI，将 `127.0.0.1:13081` 转发到服务器 DSH。Workbench 网页终端断开不影响已建立的 SSH 通道或 systemd 服务。

检查命令（在 ECS 执行）：

```bash
systemctl status xiaobai-dsh.service
docker ps --filter name=xiaobai-napcat
node /srv/xiaobai/app/workspaces/operations/server/check-onebot.mjs
node /srv/xiaobai/app/workspaces/operations/server/check-qq.mjs
systemctl is-active xiaobai-qqbot.service
ss -ltn | grep -E ':(3081|3001|6099) '
```

`check-onebot.mjs` 用私有 OneBot 配置的令牌在回环 WebSocket 调用 `get_login_info`，仅输出是否登录，不输出 QQ 号或令牌。`check-qq.mjs` 再核对 DSH 通道与自动回复；只有两项都通过，并有真实私聊回复，普通 QQ 才算当前可用。它们不能证明未来 24 小时不会触发平台身份验证。官方 Bot 也需结合服务状态、真实私聊和重启后重测判断。

这只是 **24 小时在线后台**。直播间、TTS/RVC、浏览器舞台和点歌仍在本机运行，公开开播与本地彩排均未在 ECS 验收。后续迁移需实现以下工作：

1. 将 Windows PowerShell、WSL 固定路径与 `D:/bilidown` 等依赖改为可配置的 Linux 路径或容器服务。
2. 明确舞台如何渲染与采集，并用受控推流链路发送画面和声音；验证视频声量、TTS/RVC、点歌连续播放和 GPU/内存峰值。
3. 将登录态和 API 凭据置于服务器的私有存储；不要把本机 `.dsh-home` 原样上传或写进镜像。
4. 控制台需增加正式身份验证、TLS、反向代理及访问限制。当前 `127.0.0.1:3090` 的本地来源校验仅适合本机，不构成公网认证。
5. 使用新机器重新完成 B 站、QQ 平台登录及平台要求的验证；先做短时彩排，再做公开测试。
