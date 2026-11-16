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

## 个人服务器

目前没有可直接运行的服务器部署包。迁移需实现以下工作：

1. 将 Windows PowerShell、WSL 固定路径与 `D:/bilidown` 等依赖改为可配置的 Linux 路径或容器服务。
2. 明确舞台如何渲染与采集，并用受控推流链路发送画面和声音；验证视频声量、TTS/RVC、点歌连续播放和 GPU/内存峰值。
3. 将登录态和 API 凭据置于服务器的私有存储；不要把本机 `.dsh-home` 原样上传或写进镜像。
4. 控制台需增加正式身份验证、TLS、反向代理及访问限制。当前 `127.0.0.1:3090` 的本地来源校验仅适合本机，不构成公网认证。
5. 使用新机器重新完成 B 站、QQ 平台登录及平台要求的验证；先做短时彩排，再做公开测试。
