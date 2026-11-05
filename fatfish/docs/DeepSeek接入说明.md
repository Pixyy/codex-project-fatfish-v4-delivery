# DeepSeek 接入：四步完成

1. 在「和她说说话」点击 **接入 DeepSeek**。
2. 点击 **登录 DeepSeek 官网**，在官方开放平台登录，并创建一个自己的 API Key。
3. 回到项目，粘贴 Key；可以先检测可用模型和 API 余额。
4. 点击 **检测并开始真实聊天**。收到真实检测回复后才保存配置并切换到真实 AI；网页与桌宠共用该配置。

**登录和创建 Key 都在官方页面完成。** 本项目只使用客户主动提供的 API Key，不接收官网密码、不读取浏览器 Cookie，也不把“打开官网”显示成“已登录本项目”。官方 Harness 另有自己的账号授权能力，本版不接管该流程。

检测 Key / 模型 / 余额使用官方查询接口；完成接入还会发送一次最多 64 个输出 token 的简短模型请求，可能产生少量 API 费用。当前推荐默认模型 `deepseek-flash`，可用列表以账号实际返回为准。

| 提示 | 处理方式 |
| --- | --- |
| HTTP 401 | Key 无效；重新复制完整 Key |
| HTTP 402 / 余额不足 | 到开放平台查看 API 余额或充值，再重试 |
| HTTP 429 | 速率达到上限；稍后再试 |
| 网络 / HTTPS 错误 | 检查网络、系统时间和代理证书 |
| 当前密钥来自环境变量 | 在高级配置中使用已有环境认证，或移除 `FISH_MODEL_KEY` 后再通过页面更换 |

需要退出：设置 → **断开并忘记本机密钥**。这会回到预设体验并关闭 QQ 自动回复，保留聊天记录；远程 Key 仍由客户在官网管理。

Key 只保存在这台电脑的项目数据目录，不是加密保险库；保存后输入框留空保留原值。转发程序时发送新交付包，避免把自己运行后的 `data/` 一并发送。

官方依据（核对：2026-11-05）：

- [首次 API 调用与当前模型](https://api-docs.deepseek.com/zh-cn/)
- [模型列表](https://api-docs.deepseek.com/zh-cn/api/list-models/)
- [查询余额](https://api-docs.deepseek.com/zh-cn/api/get-user-balance/)
- [错误码](https://api-docs.deepseek.com/zh-cn/quick_start/error_codes/)
- [官方 Harness 账号说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-settings-account/README.zh.md)
