# 小白主播

小白是本地运行的 AI 主播实验项目。当前入口是 Windows 上的控制台，整合 QQ 私聊、B 站浏览和 B 站直播；语音使用 CosyVoice3 与 RVC，点歌会调用本地音频处理流程。历史测试记录见 [功能验收清单](docs/history/功能验收清单.md)，不能当作新机器上的验收结果。

## 工作区

| 目录 | 负责内容 |
| --- | --- |
| [`workspaces/control-center/`](workspaces/control-center/README.md) | QQ、刷视频、直播的统一网页控制台 |
| [`workspaces/voice/`](workspaces/voice/README.md) | 说话、RVC 换声、点歌和训练工具 |
| [`workspaces/platform/`](workspaces/platform/README.md) | DSH、B 站、QQ 接入配置与直播插件补丁 |
| [`workspaces/operations/`](workspaces/operations/README.md) | 本机安装、启动、检查和资源管理脚本 |
| [`docs/`](docs/HANDOFF.md) | 交接、部署说明和历史记录 |

本机运行数据已集中到 [`local-data/`](docs/LOCAL_DATA.md)。原来的 `.dsh-home/`、`vendor/`、`models/`、`outputs/`、虚拟环境等路径是隐藏的 NTFS 目录联接，现有脚本仍可按旧路径访问；这些数据不进 Git。

## 从哪里开始

1. 接手开发：读 [交接说明](docs/HANDOFF.md)。
2. 看清哪些文件需要私下迁移：读 [本地数据与部署](docs/DEPLOYMENT.md)。
3. 本机已有依赖与账号时，运行 `启动小白.cmd`，控制台地址为 `http://127.0.0.1:3090/`。

源码与配置示例可以放到 GitHub。`local-data/`、根目录兼容联接、模型、训练音频、生成歌曲、浏览器会话、账号配置和 `待删除_*` 不进入 Git。不要把本机目录整体压缩后上传。

项目已拆出一个最小 Linux 后台：ECS 可以运行 DSH 世界设定与 QQ 接入，部署现状见 [部署文档](docs/DEPLOYMENT.md)。控制台、B 站浏览、直播画面、语音及点歌仍由本机 Windows 负责；不能将根目录的 Windows 启动脚本直接用于 Linux。
