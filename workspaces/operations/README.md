# 本机运维工作区

这里是安装、启动、资源管理和检查脚本。项目根目录只保留 `启动小白.cmd`、`启动DS.cmd`、`释放语音内存.cmd` 三个可双击入口；它们调用此目录中的 PowerShell 脚本。

全部脚本以项目根目录为路径基准。`Setup-Local.ps1` 依赖 `workspaces/platform/config` 和本机 `vendor/overrides`；语音服务启动脚本依赖 `workspaces/voice` 与 WSL。迁移到服务器前须替换 Windows/WSL 固定路径。

服务器与私有数据相关回归：`py -3 -m unittest discover -s workspaces\operations\tests -p 'test_*.py'`。`server/check-memory-layout.py` 只读核对场景文件、日记目录、B 站工作区与只读开关、QQ 延迟/会话配置和重复会话索引，不修改运行时数据。
