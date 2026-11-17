# 平台接入工作区

`config/` 保存 DSH、QQ、B 站与角色设定的模板；实际账号配置只在本机，已被 Git 忽略。`patches/` 保存对上游 `dsh-livestream` 的改动，基线和应用方法见 `docs/HANDOFF.md`。

平台接口或直播插件改动应在这里记录版本与来源。登录态、Cookie、QQ token 和定制 npm 包不进入 Git。

`qqbot-bridge/` 是腾讯官方 QQ Bot 的服务器端私聊适配器。代码和无凭据示例可入 Git；AppID/AppSecret、openid 白名单、Gateway 会话与 DSH 桥口令只保存在服务器私有目录。部署与验收状态见 `docs/DEPLOYMENT.md`。

`config/memory/` 保存 QQ、B 站浏览、直播和共同身份的分域模板；运行时文档仍在被忽略的 `.dsh-home/worlds/ds/`。三层结构、旧归档边界和受控跨读见 `docs/MEMORY_ARCHITECTURE.md`。
