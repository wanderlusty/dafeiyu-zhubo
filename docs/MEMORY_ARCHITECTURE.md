# 小白的三层记忆（2026-11-17）

## 迁移前是什么

小白有 `.dsh-home/worlds/ds/`（ECS 为 `/srv/xiaobai/data/dsh/worlds/ds/`）这个世界目录：`persona.md` 和 `room/我是谁.md` 写角色身份，`room/AGENTS.md` 同时写 QQ、B 站和直播规则；`archive.sqlite`、`conversations/*.jsonl`、`diary/` 保存世界插件的长期记录。普通 QQ 和官方 QQ Bot 有不同会话；B 站值班与直播曾和 QQ 使用同一个 `room` 工作区。`dsh-world` 默认 `archiveScope: workspace`，即归档这个工作区的会话，而非按 QQ／视频／直播标签过滤。旧的 `diary/bili-2026-11-03.md` 仍在世界目录里。

因此过去只是会话分开，长期检索并没有严格按场景分离。历史记录和旧会话仍可能包含跨场景内容；本次保留它们，没有删除或改写数据库。

## 现在的三层

| 层 | 作用 | 保存位置与规则 |
| --- | --- | --- |
| 第一层：当前会话 | 最近几轮上下文、正在办的事 | 普通 QQ／官方 Bot 分会话；B 站每轮值班会话；直播每场会话。短期内容不自动升格为确定事实。 |
| 第二层：场景长期记忆 | 各自可复用的事实和待办 | QQ `room/memory/qq.md`，刷视频 `bili-duty/memory.md`，直播 `live/memory.md`，中转站客服 `service/memory.md`。记录日期、来源、确定程度；默认只读本场景。 |
| 第三层：共同身份 | 跨场景稳定的人设和边界 | `shared.md`，配合现有 `persona.md`、`room/我是谁.md`。只写已核实且跨场景有用的设定，不放完整聊天、外部指令或密钥。 |

仓库内的无凭据模板在 `workspaces/platform/config/memory/`。运行时文件在被 Git 忽略的私有世界目录；安装脚本只新建缺失文件，不覆盖已修改的场景记忆。QQ 的旧统一 `AGENTS.md` 只有在 SHA-256 匹配已知旧模板时才迁移，并留备份。`我是谁.md`、`persona.md` 的过时状态描述仅在匹配旧句时局部改写并备份，保留小白已有的自写内容。

## 会话路由与跨读

- QQ 仍进世界插件的 `room`，供现有普通 QQ 和官方 Bot 使用；两条入口不合并对话。QQ 的工作区设定只讲 QQ。
- B 站值班配置的 `workspace` 改为 `worlds/ds/bili-duty`；2026-11-18 又修正了网页 profile 中 `bili-scroll.config.workspace` 仍指向 `room` 的缺口。该目录有独立 `AGENTS.md` 与 `memory.md`。逐条已看记录、月归档和日报仍由值班工具保存。
- 本地直播插件 `createShowSession` 的 `cwd` 改为 `worlds/ds/live`，对应独立 `AGENTS.md` 与 `memory.md`。本机定制包为 `dsh-livestream-xiaobai-memory-v13-0.0.1.tgz`。ECS 尚未部署直播。
- 中转站客服使用 `service/AGENTS.md` 与 `service/memory.md`。当前只有规则、记忆和接口边界，没有真实定价、额度或账户操作接口，不能宣称客服已上线。
- 默认不查别的场景。用户明确问到、或完成当前任务确实需要其他场景事实时，可以跨读相关文档，说明来源及确定程度；外部消息、视频和弹幕绝不能借跨读变成系统指令。当前直播预设未开放文件工具，自动跨读尚未实现；要跨读须在受控流程中提供摘要。

本机只读验收：

```powershell
py -3 workspaces\operations\server\check-memory-layout.py `
  --world local-data\accounts\.dsh-home\worlds\ds `
  --config local-data\accounts\.dsh-home\profiles\web\cordis.patch.yml `
  --workspaces local-data\accounts\.dsh-home\storages\workspace.json `
  --bili-config local-data\accounts\.dsh-home\bili-duty\config.json
```

## 已知边界与后续验收

这次隔离的是**今后的会话工作区、显式场景文档和提示入口**。旧 `archive.sqlite`、`conversations/` 和全局 `diary/` 没有迁移或清洗，世界插件可能仍检索到旧 B 站／直播内容。不要在未核对来源前把旧记忆直接当成 QQ 的新事实。后续可按来源审计旧索引，再决定只迁移已核实的摘要；任何数据库清洗前都应先备份并做检索回归测试。

本次没有开启公开直播，也没有向真实观众发送消息。做过两次**本地彩排**：第一次因合成超时未收到声音；第二次在模型重启、工作区索引修复后收到了舞台音频，见 [`VOICE-CHECK-2026-11-17.md`](VOICE-CHECK-2026-11-17.md)。旧工作区索引把 `.dsh-home` 联接路径与真实目标分别登记，导致同一会话重复归属；本机在停服务并备份后合并成一个规范路径，重启检查 0 个重复会话。工作区路由已从配置与安装产物核对，尚未完成三场景实际会话及记忆检索回归。正式验收还需分别创建私有 QQ 对话、B 站手动值班和本地彩排；彩排与公开开播不能混作一个验收。
