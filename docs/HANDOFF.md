# 接手说明（更新至 2026-11-17）

2026-11-17 的续接进度、官方 QQ Bot 状态和 GitHub 私有备份核验步骤见 [`CONTINUATION-2026-11-17.md`](CONTINUATION-2026-11-17.md)。

QQ、刷视频、直播的三层记忆结构、运行时目录和旧归档边界见 [`MEMORY_ARCHITECTURE.md`](MEMORY_ARCHITECTURE.md)。2026-11-17 的三段真实 TTS→RVC 口语试听和本地舞台说话彩排见 [`VOICE-CHECK-2026-11-17.md`](VOICE-CHECK-2026-11-17.md)。第二次本地彩排已收到音频，约 24.7 秒才合成完首句；自然度尚待用户主观听审。

## 项目结构

| 路径 | 用途 |
| --- | --- |
| `workspaces/control-center/` | 本地可视化控制台，Node 服务和页面。默认监听 `127.0.0.1:3090`。 |
| `workspaces/voice/` | TTS、RVC、点歌、分离与训练脚本；配置示例可公开，样音和模型不公开。 |
| `workspaces/platform/config/` | DSH、刷 B 站和世界设定模板。带 `.example` 的文件可公开；本机配置已被忽略。 |
| `workspaces/platform/patches/` | 对上游直播插件源码的本地功能改动，包括新增文件。 |
| `workspaces/platform/qqbot-bridge/` | 腾讯官方 QQ Bot 私聊适配器；服务器端服务与私有凭据说明见 `docs/DEPLOYMENT.md`。 |
| `workspaces/operations/` | Windows 安装、启动和检查脚本；根目录只保留三个双击入口。 |
| `local-data/` | 本机依赖、权重、生成物、样音、虚拟环境和账号状态；均不进仓库。根目录旧路径是隐藏目录联接。 |
| `docs/history/` | 早期调研和验收记录；其中的旧路径以本说明为准。 |

## 直播插件源码

上游仓库为 `https://github.com/luckui/dsh-livestream.git`，基线提交为 `6c2f405b5520bea932808c224ba9ca6d65f41756`。本仓库只保存本地改动补丁，未复制第三方素材、完整上游仓库或 npm 包。源码许可证副本为 `workspaces/platform/patches/dsh-livestream-LICENSE.txt`；动画素材的许可证另看上游说明。

在干净目录还原源码：

```powershell
git clone https://github.com/luckui/dsh-livestream.git
cd dsh-livestream
git checkout 6c2f405b5520bea932808c224ba9ca6d65f41756
git apply ..\ds-zhubo\workspaces\platform\patches\dsh-livestream-xiaobai.patch
pnpm install --frozen-lockfile
pnpm --dir packages/dsh-livestream check
pnpm --dir packages/dsh-livestream test
pnpm --dir packages/dsh-livestream build
```

补丁已在本机同一基线的干净副本上通过 `git apply --check` 和实际 `git apply`。构建/测试需要安装依赖，本次整理没有重新构建或跑直播。

## 当前本机运行依赖

- `workspaces/operations/Setup-Local.ps1` 固定使用 DSH `0.2.1-rc.5`、`dsh-bili-scroll` `2.4.0`、`dsh-world` `0.7.0`，并校验本机两个定制 `.tgz` 的 SHA-256。
- 直播插件包在 `vendor/overrides/dsh-livestream-xiaobai-memory-v13-0.0.1.tgz`（SHA-256 `0B4E36AF3E6FF08265A8589749AB18FB22882515E8C02CC0EC73269B1F57EE8F`），刷 B 站定制包在 `vendor/overrides/dsh-bili-scroll-2.4.0.tgz`。这两个包不上传 GitHub。新的接手者需要从上面的补丁重建直播包；刷 B 站定制包目前只有本机包，需单独迁移或重新整理源码。v13 在已有构建产物中只把直播 `cwd` 从 `room` 改为 `live` 并重新打包；Windows 上 `pnpm check` 因创建依赖符号链接被拒绝而未跑通，仍需在可构建环境重建验证。
- 语音服务配置在 `workspaces/voice/voice_config.json`、`workspaces/voice/rvc_config.json`，当前版本仍含 Windows/WSL 绝对路径。公开仓库只有示例配置。
- `Start-Voice.ps1` 在语音端口健康后做一次完整 TTS→RVC 短句预热，成功才报告“已预热”；预热失败会提示检查语音日志。2026-11-17 停服务后重启验证了这一步。舞台本地彩排首句仍需约 24.7 秒，超过实时交互的理想等待。
- `workspaces/voice/song_clip_catalog.json` 指向 `outputs/covers/` 下的本机歌曲片段。公开仓库只保留空目录格式示例；实际歌单与音频须按授权情况私下迁移。
- `workspaces/platform/config/web-world.patch.yml` 存有本机 QQ 白名单及 SnowLuma 路径，公开仓库只有默认关闭 QQ 自动回复的示例。
- `local-data/media/assets/` 有直播封面等素材，未纳入 Git；根目录 `assets/` 是兼容联接，部署时需逐一确认来源与授权。

## 已知未完成项

1. ECS 已有最小后台部署，包含 DSH、角色记忆、普通 QQ OneBot 容器与腾讯官方 QQ Bot 服务。两条 QQ 入口于 2026-11-17 均通过真实私聊回复；官方 Bot 在服务重启后再次通过。普通 QQ 曾掉线并需手机身份验证，连续 24 小时稳定性仍未验收。当前状态以 `docs/DEPLOYMENT.md` 为准。Windows/WSL 路径、直播画面采集、TTS/RVC GPU 部署和 B 站登录仍未迁移。
2. 当前控制台只允许本机访问；不能直接把 3090 端口暴露到公网。
3. 点歌获取、分离、换声与播放依赖本地模型及下载工具；`README` 中的历史成功案例不代表每首歌都能稳定生成。
4. 上游插件源码与本地补丁需一起构建，不能只安装公开 npm 版就获得小白的功能。
5. 三层记忆已建立模板，并在本机及 ECS 私有目录安装；B 站和直播的新会话路由已分别改到独立工作区。一次本地说话彩排通过，但尚未跑完整值班或记忆检索回归。旧世界归档和日记未清洗，不能声称历史记忆已经完全隔离。本机旧 `workspace.json` 因根目录 `.dsh-home` 联接路径和真实目标重复登记同一会话而造成 DSH 启动失败；停服务并备份后，保留原工作区 ID、把路径改为 `local-data/accounts/.dsh-home/worlds/ds/room`，移除了重复登记，重启复查正常。其他旧机器若遇同类错误，先核对实际联接目标和会话 ID，再迁移，勿直接删除会话文件。

## 接手优先顺序

先在全新 Windows 目录还原源码与私有依赖并通过本地彩排，再拆除硬编码路径；随后设计服务器端身份验证、持久化、直播画面与音频推流。迁移时优先完成只读健康检查和私有彩排，最后再做实际开播验证。
