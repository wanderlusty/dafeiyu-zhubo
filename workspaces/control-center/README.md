# 统一控制台工作区

`server.mjs` 提供本地网页入口，`index.html`、`app.js`、`style.css` 是界面。它从项目根目录读取 DSH token、直播封面与点歌任务，并调用 `workspaces/voice` 和 `workspaces/operations`。默认只监听 `127.0.0.1:3090`。

独立语法检查：`node --check workspaces/control-center/server.mjs` 和 `node --check workspaces/control-center/app.js`。真实功能验证需要本机 DSH、语音服务和登录态。不要将当前服务直接暴露到公网。
