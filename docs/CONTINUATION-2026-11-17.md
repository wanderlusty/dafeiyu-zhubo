# 小白项目续接记录（2026-11-17）

给接手 Agent：先读根目录 `AGENTS.md`、`README.md`、`docs/HANDOFF.md` 和 `docs/DEPLOYMENT.md`。本记录是本轮工作快照，先核对实际状态再操作。不要把 `local-data/`、任何凭据、模型、样音或歌曲文件提交到 Git。

## 用户目标与当前边界

- 用户发现服务器上的普通 QQ 小号在电脑关机期间掉线，并收到安全验证提示；现在要求腾讯开放平台官方 QQ Bot 和普通 QQ 小号 **两条入口并行保留**。2026-11-17 两条入口均已完成真实私聊回复验收。
- 用户给出 B 站视频 `BV1W2nr6yERy`，要求核对“QQ 机器人风控防范指南”。视频主张官方通道与普通 QQ 客户端通道不同，并讨论普通号的登录环境、频率和内容风险。这些是作者经验，不能当作腾讯平台承诺。对本项目的实际结论：继续官方 Bot 迁移；普通 QQ 在线状态须以真实收发验证，不能只看 Docker/systemd。
- 用户要求把上游 `TomyJan/SnowLuma`、`VanillaNahida/NapCatQQ` 备份到自己 GitHub 的私有仓库。目标账号是 `wanderlusty`；本机 Git Credential Manager 同时存有 `Wanderkily`，操作时必须显式选择 `wanderlusty` 并验证归属与 private 状态。
- 用户需要本交接文档，便于 5 小时额度用尽后让其他 Agent 接手。

## 官方 QQ Bot 准备情况

- 适配器源码：`workspaces/platform/qqbot-bridge/`。使用腾讯官方 `@tencent-connect/qqbot-nodejs` 的 C2C 私聊事件，经本机回环 WebSocket 接入 DSH。私聊 sender openid 白名单、去重、串行回复和独立会话已实现。
- 本地模拟测试：在 ECS 上运行 `npm test`，1 个适配器测试通过；`check-bridge.mjs` 已对 DSH 的 `127.0.0.1:3210` 桥做认证连通检查。**这不是官方 QQ 真实收发验收。**
- ECS `xiaobai-qqbot.service` 已 `enabled/active`，QQ 网关连接成功。服务器私有目录为 `/srv/xiaobai/data/qqbot/`，源码为 `/srv/xiaobai/app/`。AppID/AppSecret 只在权限 `0600` 的服务器私有文件中。普通 QQ NapCat 仍在，官方接入完成后也要保留。
- 用户在 `q.qq.com` 创建了“小白”机器人，并在 ECS Workbench 终端通过 `configure-qqbot-credentials.py` 隐藏输入 AppSecret。首次私聊进入 `pending-openids.json` 后，用户确认发送时间；唯一对应 openid 加入私有白名单。第二次私聊得到回复；仅重启 `xiaobai-qqbot.service` 后网关恢复，再次私聊也得到回复。后续凭据轮换、新用户授权及检查命令见 `workspaces/platform/qqbot-bridge/README.md`、`docs/DEPLOYMENT.md`。
- 官方 Bot 是新的平台身份，不继承原普通 QQ 小号的好友关系。普通 QQ 于 2026-11-17 再次通过 OneBot `get_login_info`、DSH 状态及用户主号真实私聊回复验收。两条入口都能当前收发，但普通 QQ 连续 24 小时稳定性仍未通过。实际账号标识仅保存在私有配置中。

## GitHub 私有备份进度与操作提醒

- 目标仓库已在 `wanderlusty` 创建为私有并完成 `main` **源码快照**备份：[`SnowLuma-backup`](https://github.com/wanderlusty/SnowLuma-backup)（上游 `f2ea3354f8bbe8672cbb4ae6a2b4e1fbeff44faf`，1,367 个文件）和 [`NapCatQQ-backup`](https://github.com/wanderlusty/NapCatQQ-backup)（上游 `72912f293924f43463b5976b01fc094a8ae11481`，1,111 个文件）。上传脚本把归档逐文件写成 Git 树，随后用 Git blob SHA 逐一校验，GitHub 插件也确认两库为 private、`LICENSE` 可读。**这不是完整 Git 历史镜像；其他分支、标签和 Release 二进制未备份。**
- 本机凭据的默认账号是 `Wanderkily`；误用默认账号会把备份推错地方。`local-data/generated/github-backups/create-private-repos.py` 显式要求 `wanderlusty`；此脚本位于被忽略目录，未提交。此前默认账号下误建了两个**空**私有仓库，未复制源码，后续可由账号持有人决定是否删除。
- 本机环境变量 `HTTP_PROXY`/`HTTPS_PROXY` 指向 `127.0.0.1:7900`，该代理对 GitHub TLS 握手失败；直连 `github.com` 的 Git 传输也不稳定。本轮仅在命令进程内移除这两个变量；没有改系统代理。最终通过 GitHub API 下载源码 ZIP，再用 Git Trees API 写入私有仓库。下载的 ZIP 和上传脚本位于被忽略的 `local-data/generated/github-backups/`。
- 两个私有备份仓库的 GitHub Actions 已禁用，以免复制上游工作流后意外运行。SnowLuma 上游 EULA 对原生扩展有特别限制，仅复制了上游 Git `main` 中已经跟踪的文件，没有额外收集 Release 二进制。若以后网络恢复且要补完整历史，先检查原 LICENSE/EULA、`.gitattributes`、大文件和特殊 Git refs；不要把当前快照误称为完整镜像。
- 本轮 Git 备份说明和交接文档已随主项目提交 `df296e9` 推送到 `wanderlusty/dafeiyu-zhubo`。接手仍先看 `git status --short`，保留用户原有修改，不要盲目覆盖。

## 音频教程复核

本地临时目录 `local-data/generated/video-review/` 有下载的 B 站视频音频和自动转写 `transcript.txt`；它们被忽略，不进 Git。Whisper 自动转写有不少同音字错误，涉及准确措辞时以视频原声和腾讯官方文档为准。视频约 12 分 35 秒；其建议中“固定机器/IP、降低消息频率、避免多端反复登录”等主要针对普通 QQ 客户端接入，不能保证不受风控，也不能替代官方平台规则。

## 验收清单

1. GitHub 两个目标仓库 `private=true`，当前 `main` 文件内容与所记录的上游提交逐文件一致。备份仓库的提交 SHA 与上游不同，因为这是源码快照；完整历史若需要须后续单独处理。
2. 官方 QQ Bot 只开 C2C，陌生 openid 不触发回复；用户的 openid 白名单已实测收发。
3. ECS 重启官方 Bot 服务后再次实测收发；普通 QQ 与官方 Bot 并行，各自用独立白名单和会话。不要关闭普通 QQ 接入。普通 QQ 也已在同日实测回复；24 小时稳定性需继续观察。
4. 公开开播与本地彩排分开说明；本轮未开播，也未做直播彩排。
