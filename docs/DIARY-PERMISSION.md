# 小白日记写入权限（2026-11-17）

## 问题

小白的工作区是 `/srv/xiaobai/data/dsh/worlds/ds/room/`，而 DSH 的 `workspace-write` 沙箱只允许写会话工作区。默认日记目录位于它的上一级 `/srv/xiaobai/data/dsh/worlds/ds/diary/`，所以文件工具返回“文件访问被拒绝”。这不是文件名或目录权限位错误。

DSH 的三种权限模式中，只有 `danger-full-access` 能让小白直接写兄弟目录；这样做会同时放开服务器上的其他文件，范围过大。项目因此把日记目录迁入 `room/diary/`，并让 `dsh-world` 的 `diaryDir` 指向它。

## 迁移规则

- 只迁移文件名严格为 `YYYY-MM-DD.md` 的日记。
- 同时读取旧 `diary/` 和 `room/diary-待迁/`；旧文件和非标准文件都保留。
- 目标已存在且内容哈希一致时跳过；内容不同则停止，不覆盖。
- `cordis.patch.yml` 只修改 `- id: dsh-world` 块中的 `diaryDir`，修改前生成带时间戳的备份。
- 迁移脚本默认只做 dry run，必须显式传 `--apply` 才写文件。

## 服务器执行

先做 dry run：

```bash
python3 /srv/xiaobai/app/workspaces/operations/server/migrate-diary-into-room.py \
  --world /srv/xiaobai/data/dsh/worlds/ds \
  --config /srv/xiaobai/data/dsh/profiles/web/cordis.patch.yml
```

确认输出没有冲突后执行：

```bash
python3 /srv/xiaobai/app/workspaces/operations/server/migrate-diary-into-room.py \
  --world /srv/xiaobai/data/dsh/worlds/ds \
  --config /srv/xiaobai/data/dsh/profiles/web/cordis.patch.yml \
  --apply

systemctl restart xiaobai-dsh.service
```

重启后让小白在 QQ 中写一篇当天日记，再从控制台核对 `room/diary/YYYY-MM-DD.md`。这只开放她自己的日记目录；工作区权限继续保持 `workspace-write`。
