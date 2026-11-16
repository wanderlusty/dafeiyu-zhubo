# 小白项目交接入口

先读 `README.md` 和 `docs/HANDOFF.md`。代码分在 `workspaces/control-center`、`workspaces/voice`、`workspaces/platform`、`workspaces/operations`；本机运行数据集中在 `local-data/` 并由 `.gitignore` 排除。根目录原有数据路径保留为隐藏的 NTFS 目录联接，供现有脚本兼容使用。

修改跨工作区路径时，同步检查三个根目录启动 `.cmd`、控制台服务、语音脚本、私有配置示例和 `docs/DEPLOYMENT.md`。不要把 `.dsh-home`、模型、样音、歌声文件或任何凭据加入 Git。公开开播与本地彩排是不同操作，验收时明确说明做了哪一种。

不要删除根目录的隐藏目录联接或把它们当成多余副本；真实数据位于 `local-data/`。搬迁时先停止相关进程，检查联接目标，再操作真实目录。
