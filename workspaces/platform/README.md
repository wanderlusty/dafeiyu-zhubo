# 平台接入工作区

`config/` 保存 DSH、QQ、B 站与角色设定的模板；实际账号配置只在本机，已被 Git 忽略。`patches/` 保存对上游 `dsh-livestream` 的改动，基线和应用方法见 `docs/HANDOFF.md`。

平台接口或直播插件改动应在这里记录版本与来源。登录态、Cookie、QQ token 和定制 npm 包不进入 Git。
