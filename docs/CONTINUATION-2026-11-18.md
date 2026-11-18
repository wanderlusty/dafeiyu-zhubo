# 小白项目续接记录（2026-11-18）

给接手 Agent：先读根目录 `AGENTS.md`、`README.md`、`docs/HANDOFF.md`、`docs/DEPLOYMENT.md` 和本文件。运行数据在 `local-data/`，根目录 `.dsh-home` 等是兼容联接，不是可删除副本。不要把 `local-data/`、凭据、模型、样音、歌声或运行日志加入 Git。

## 本轮结果

### 已实现并本地验收

- 三层记忆：QQ `room/memory/qq.md`、刷视频 `bili-duty/memory.md`、直播 `live/memory.md`、客服 `service/memory.md` 与共同身份 `shared.md` 已安装。
- 日记权限：`diaryDir` 指向 `room/diary`，没有使用 `danger-full-access`。迁移脚本只复制 `YYYY-MM-DD.md`，冲突停止，默认 dry run，写配置前备份。
- 分域路由缺口：网页 profile 的 `bili-scroll.config.workspace` 原先仍指向 QQ `room`；已修正为真实的 `local-data/accounts/.dsh-home/worlds/ds/bili-duty`。本机配置已备份后更新，`Setup-Local.ps1` 后续会重复保证该路由。
- QQ 延迟与自然度：`batchQuietMs=800`、`bindHomeSession=none`、`reasoningEffort=low` 已加载。官方 Bot 分条改为最多两条、每条 360 字，并在发送前清洗 Markdown、内部工具名和常见绝对路径。
- 群聊准备：官方 Bot 群聊默认关闭；只响应 `allowed-groups.json` 白名单内的 @ 消息，未授权群只写私有 `pending-groups.json`，每个群使用独立 `qqgroup:` 会话。
- 客服准备：新增 `service/AGENTS.md`、`service/memory.md` 和 `docs/SERVICE-OPERATIONS.md`。定价、免费额度、报错查询和账户操作尚无线上接口，客服未上线。
- 刷视频：新增 `docs/BILI-DUTY.md`，明确先看已看记录、再推荐/检索、写去重与日报、只读不评论。当前配置保持 `autoComment=false`、`replyToComments=false`、`dmMode=off`。

### 固定验收命令

```powershell
py -3 -m unittest discover -s workspaces\operations\tests -p 'test_*.py'
npm test --prefix workspaces\platform\qqbot-bridge
py -3 workspaces\operations\server\check-memory-layout.py `
  --world local-data\accounts\.dsh-home\worlds\ds `
  --config local-data\accounts\.dsh-home\profiles\web\cordis.patch.yml `
  --workspaces local-data\accounts\.dsh-home\storages\workspace.json `
  --bili-config local-data\accounts\.dsh-home\bili-duty\config.json
```

本文件生成前结果：Python 7 项通过，Node 5 项通过；记忆检查的 10 个场景文件、`room/diary`、`diaryDir`、`bili-scroll.workspace`、QQ 0.8 秒合并、独立会话、低思考、3 个工作区且 0 个重复会话、B 站只读配置全部 PASS。

## 当前运行状态

- 本轮检查时 `3090`（控制台）、`3210`（QQ Bridge）、`7391/7392`（TTS/RVC）和 `3081`（ECS DSH 本地转发）均未监听；没有启动服务，也没有公开开播。
- 未在本轮重新播放或主观听审语音。历史语音文件仍存在；第二次本地彩排的开场说话链路曾通过，但首句约 24.7 秒，动态提问未单独验收。语音自然度仍需主人听审。
- 没有可用 ECS SSH 主机别名，本轮没有修改或重启 ECS。服务器部署状态以 `docs/DEPLOYMENT.md` 的 11 月 17 日记录为准。
- 没有真实 QQ 群授权，因此群聊只完成代码和模拟测试，不能说群聊已上线。

## 新容器接手顺序

1. 克隆或拉取包含本文件的提交，确认 `git status --short`；不要复制整个 `local-data/` 到公开位置。
2. 运行上面四条验收命令；缺失私有包时 `Setup-Local.ps1` 会明确失败，不会假装完成。
3. 若在本机继续：确认根目录联接目标，启动本机服务，先用私聊和本地彩排，不要直接公开开播。
4. 若更新 ECS：拉取源码后运行 `install-memory-layout.py` 和 `check-memory-layout.py`；日记迁移先 dry run，再 `--apply`；更新后重启 `xiaobai-dsh.service` 与 `xiaobai-qqbot.service`。
5. 真实 QQ 私聊验收：手机主号发送一条，服务端确认回复；普通 QQ 与官方 Bot 两个入口都保留。官方 Bot 重启后也要重测。
6. 群聊验收前先取得群管理者同意；从 `pending-groups.json` 核对 group openid，再加入 `allowed-groups.json`。只能测白名单群 @ 消息，不能自动放行所有群。

## 尚未完成

- ECS 尚未应用本轮客服模板、群聊白名单和 B 站路由修正，也未做新的真实 QQ 私聊/群聊验收。
- 私人手机 QQ 的 P50 首回复目标 5 秒、10 句短回复和主观自然度尚未做本轮真实测试。
- 梗库采集/审核流水线、QQ 表情包发送、视频制作学习、直播语音内存优化和游戏能力仍在后续阶段；当前适配器只发送文字。
- 旧 `archive.sqlite`、`conversations/` 和旧日记没有清洗，历史记忆仍可能跨场景检索，不能声称历史已经完全隔离。

## 重要文件

- 记忆架构：`docs/MEMORY_ARCHITECTURE.md`
- 日记迁移：`docs/DIARY-PERMISSION.md`、`workspaces/operations/server/migrate-diary-into-room.py`
- 记忆检查：`workspaces/operations/server/check-memory-layout.py`
- QQ 桥：`workspaces/platform/qqbot-bridge/`
- 聊天自然度：`docs/CHAT-NATURALNESS.md`
- 刷视频逻辑：`docs/BILI-DUTY.md`
- 客服边界：`docs/SERVICE-OPERATIONS.md`
