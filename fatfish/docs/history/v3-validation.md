# v2 验证记录

验证日期：2026-11-05。环境：Linux / Python 3.12 / Playwright 1.62 / Chromium 151。

## 已通过

- Python 编译、前端 JavaScript 语法检查。
- 5 项本机 HTTP 集成测试：预设互动、密钥不回显与文件权限、模型兼容接口调用、会话隔离、签名 QQ 消息接收与自动发送、重复消息去重、允许列表与群 @ 限制、跨来源和错误令牌拦截、全局暂停、换密钥后清除旧连接检测结果。
- 模型和 QQ 的集成测试使用**显式本机测试服务**。实际请求经过 HTTP、模型响应解析和发送接口；测试没有使用真实 QQ 账号或真实商业模型密钥。
- 2 项可选真实浏览器测试：公开 HTTPS 网页文字提取与 PNG 截图；由显式模型测试接口驱动的实际滚动和工具结果回传，以及执行前停止。
- 真实浏览器 UI 操作：立绘与三视图加载、投喂互动、预设聊天、缺少密钥错误、QQ 回调配置展示、Android 设备检测、桌面和 390px 手机布局、无 JavaScript 页面错误。
- 从网页界面发起真实 https://example.com 浏览任务，任务排队、完成状态、文字和截图均通过。
- 浏览路径保持 TLS 证书校验。原 v1 的 ERR_CERT_AUTHORITY_INVALID 通过项目内使用系统 CA 校验的传输层解决，**没有修改用户全局证书库，也没有关闭 TLS 校验**。

## 尚未验证 / 不提供

- 未提供真实 API Key，所以真实商业模型的回复与计费未验证；测试接口只验证实现链路。
- 未提供真实 QQ OneBot 账号和企业微信 Webhook，所以实际账号发送与接收未验证。
- 当前没有 ADB 或 Android 设备，手机 App 真机执行未验证。代码只实现固定的打开、滑动、截图动作，没有视觉自主决策。
- 视频网站受平台登录、自动播放策略、反爬和流媒体协议影响，没有把“打开网页”算作“看完视频”。完成记录会显示是否实际观察到播放进度。
- 不提供个人微信登录或自动回复，不支持 iPhone。
- 未在真实 Windows/macOS 系统运行启动器；脚本和跨平台路径已提供，本机运行验证为 Linux。

## 重跑

```bash
python -m unittest discover -s tests -v
python check_ui.py --live-browser
FISH_LIVE_TESTS=1 python -m unittest discover -s tests -p test_browser_live.py -v
```

默认单元测试跳过外网浏览测试。集成与 UI 测试使用临时数据目录，避免更改日常配置。UI 测试会将截图写入 `preview.png`、`preview-mobile.png` 和 `preview-browser.png`。

# v3 桌宠验证增量

2026-11-05：增加 Q 版／成熟版切换、共享动作配置、网页 Canvas 逐帧预览和 Qt 原生桌宠。

已通过：

- 5 项动画测试：两张实际 PNG 的尺寸与全部动作坐标、每帧时长、眨眼与暂停、一次性动作回到待机、睡觉保持、跨形态中途切换和 Q 版朝向映射。
- 原有本地 HTTP 集成测试继续通过，新增配置字段不影响聊天和 QQ 逻辑。
- 实际 Playwright 页面操作：两种形态切换、刷新后保存、挥手、睡觉／叫醒、冻结动画帧、投喂与聊天，以及桌面／手机布局。
- `check_desktop.py`：Qt offscreen 渲染与实际事件；透明、无边框和置顶窗口标记；实际帧推进；通过真实本机 HTTP 保存形态和调用预设聊天；投喂／睡觉；缩放子菜单；鼠标拖拽事件；越界限制；暂停动画；成熟版头部与气泡不重叠；alpha 蒙版构建。
- 网页动作演示通过录制实际浏览器交互获得，不是预先合成的动画视频；原生窗口使用相同动作配置。

边界：

- 原生验证使用无桌面会话的 Qt offscreen 平台，**没有验证 Windows/macOS 合成器上的透明置顶、系统托盘、全屏覆盖、多显示器和点击穿透效果**。部分平台的窗口管理器可能限制这些行为。
- Q 版复用多帧动画；成熟版为 6 个姿态和程序过渡，没有完整走路帧、骨骼绑定或 Live2D。形态切换为交叉淡入。
- 桌面聊天验证的是无密钥预设模式；真实商业模型、QQ、微信和手机真机的原有验证边界不变。

重跑：

```bash
python -m unittest discover -s tests -v
python check_ui.py --live-browser
python check_desktop.py
```

原生检查需要先运行 `python launcher.py --install-desktop`。`check_desktop.py` 默认使用 Qt offscreen，保持临时数据目录隔离。
