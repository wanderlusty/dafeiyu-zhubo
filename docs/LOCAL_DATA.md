# 本机数据目录

项目根目录的本机数据已按用途放进 `local-data/`：

| 目录 | 内容 |
| --- | --- |
| `accounts/` | DSH、B 站等账号会话状态 |
| `envs/` | 五个 Python 虚拟环境 |
| `dependencies/` | 第三方依赖、模型和下载包 |
| `media/` | 原始声音素材和直播素材 |
| `generated/` | 歌曲、训练输出和日志 |

为了兼容现有 Windows、WSL、DSH 和语音配置，原先位于根目录的 `.dsh-home/`、`.venv-*/`、`vendor/`、`models/`、`downloads/`、`声音/`、`assets/`、`outputs/`、`logs/` 仍可访问。它们是**隐藏的 NTFS 目录联接**，指向 `local-data/` 中的真实目录，不是第二份数据。请不要把它们当作重复文件删除。

`local-data/` 和所有本机账号、模型、音频、生成结果均不进入 Git。复制项目到另一台机器时，源码仓库不会包含这些内容；需依照 [部署说明](DEPLOYMENT.md) 重新准备。
