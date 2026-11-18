# 腾讯官方 QQ Bot → 小白

这个适配器使用腾讯 `@tencent-connect/qqbot-nodejs` 的 WebSocket Gateway 接收 **C2C 私聊**，再把文字送到 DSH 世界的本地 QQ Bridge。它仅监听官方机器人的新身份，不会接管普通 QQ 小号。只有 `allowed-openids.json` 中的 openid 可以触发私聊模型；陌生人的 openid 只记录到服务器私有的 `pending-openids.json`，不回复。群聊默认关闭，只有 `allowed-groups.json` 中的 group openid 且明确 @ 机器人时才回复；未授权群只记录到 `pending-groups.json`。每个群使用独立会话，图片与语音消息目前忽略。长回答最多拆成两条，每条 360 字符；聊天提示要求模型通常只说一两句。

代码不保存 AppSecret、桥口令或 QQ 消息。凭据和会话文件都放在 `/srv/xiaobai/data/qqbot/`，由 `xiaobai` 用户读取，不加入 Git。网关断线由官方 SDK 重连，进程异常由 systemd 重启。DSH Bridge 只监听服务器回环地址 `127.0.0.1:3210`。

2026-11-17 在 ECS 已完成官方 C2C 私聊和单独重启服务后的回复验收；普通 QQ 小号也在并行运行。下列步骤用于新部署、凭据轮换或新发送者授权。

本地可用 `node check-chat-latency.mjs <qq-bridge.json> "在吗？"` 通过真实 DSH 桥测量一条聊天回复的端到端耗时；桥端口默认 `3210`，可用 `XIAOBAI_QQ_BRIDGE_PORT` 覆盖。它不会发送到 QQ。

## 启用顺序

1. 在 [QQ 开放平台](https://q.qq.com/) 创建机器人，获取 AppID 和 AppSecret，启用 C2C 私聊消息能力。平台可能要求审核或测试白名单；以创建页面实际提示为准。不要在聊天或 Git 中发送 AppSecret。
2. 在 DSH 的服务器私有 `cordis.patch.yml` 中，为已启用的 `qqNative` 增加 `bridge: { port: 3210 }`，重启 `xiaobai-dsh.service`。普通 QQ 的 OneBot 配置不需要改。确认 `ss -ltn` 显示端口只在 `127.0.0.1:3210` 监听。
3. 从世界目录的私有 `qq-bridge.json` 读取桥口令，填入 `/srv/xiaobai/data/qqbot/qqbot.env` 的 `DSH_QQ_BRIDGE_TOKEN`；将 AppID/AppSecret 也只填在这个私有文件，权限设为 `0600`。
4. 安装依赖后启用 `xiaobai-qqbot.service`。先向新机器人发一条测试私聊；服务端会在 `pending-openids.json` 记录发送者 openid。核对测试时间与发送者后，才把该 openid 加入 `allowed-openids.json`，再次发消息验收。
5. 官方私聊收发通过且重启后仍可用后，**继续保留普通 QQ 的自动回复与 NapCat**。这是两个并行入口：普通号按数字 QQ 白名单运行，官方 Bot 按 openid 白名单运行，各自使用独立会话。先前普通 QQ 账号的好友关系和数字 QQ 号不会转移到官方机器人。

`qqbot.env.example` 只是字段说明，不含有效凭据。`npm test` 用本地模拟 WebSocket 桥验证白名单、去重和消息传递，不会连接 QQ 平台或调用模型。真实私聊必须在机器人创建后另行验收。
