# 形象、参考与许可记录

检索和核对日期：2026-11-05。以下为非官方社区资料，不代表 DeepSeek 官方形象。

## 本次使用的参考

- 社区资产库：TreapGoGo / deepseek-whale-girl。
  - 页面：https://treapgogo.github.io/deepseek-whale-girl/
  - 仓库：https://github.com/TreapGoGo/deepseek-whale-girl
  - Q 版三视图：https://treapgogo.github.io/deepseek-whale-girl/assets/dafeiyu-chibi-character-sheet.png
  - 本地保留：`references/chibi-reference.png`、`static/reference.png`，未修改参考原图。
  - 上游 README 许可说明副本：`references/source-readme.md`。
- 社区图集及逐图出处整理：https://iphsiibl.github.io/deepseek-whale-girl-gallery/
- 萌娘百科条目：https://zh.moegirl.org.cn/DeepSeek%E5%A8%98 （此次直接访问要求 JavaScript；没有把无法读取的页面当作已读证据。）
- 中文报道辅助核对：https://finance.sina.com.cn/roll/2026-10-31/doc-inixichz2401507.shtml

社区资料所述创作链路为：上善无形的原创鲸鱼娘「溟月」→ ZipZipPipe 融入 DeepSeek 元素的女仆版 → 多位作者的 Q 版社区二创。这不是某一套唯一官方设定；本次选择资产库公开展示的 Q 版三视图作为视觉参考，不声称该资产库维护者拥有所有上游角色权利。

## 本次 GPT Image 二创

- `static/character.png`：基于上述三视图，由 GPT Image 重画的透明站姿立绘。
- `static/sheet.png`：基于社区三视图与新立绘，由 GPT Image 重画的三视图、表情和配色设定。
- 识别特征：深蓝渐变长发、呆毛、蓝瞳、鲸鳍耳、白色女仆发箍、蓝白女仆装、鲸鱼围裙图案、从身体后方伸出的鲸尾。
- 不是画师原作，也不是 DeepSeek 官方发布素材。

## 许可边界

本项目自己编写的代码使用 MIT（见 LICENSE）。**代码的 MIT 许可不覆盖角色或第三方图片。**

上游资产库 README 将网站代码、文字提示词和图片许可分别处理，明确图片应遵循各自作者或来源的授权。图集页面标注 CC BY-NC-SA 4.0，但不能据此把所有单图许可视为已经逐一核实。本包为个人非商业试用整理，保留作者与来源；不附带商用授权或对上游权利的保证。使用、分发或商用这些参考与二创图前，应核实原作者的对应授权。新生成图也须尊重上游角色和参考的权利。

## v3 动画与原生桌宠来源

新增核对日期：2026-11-05。

### 直接复用的 Q 版素材与动作数据

- 项目：[Shenshen Pet / 深深桌宠](https://github.com/schrieeeffer/shenshen-codex-pet)，Shenshen Pet contributors。
- 原文件：`assets/spritesheet-v2.png`；本项目保存为 `static/pets/chibi-atlas.png`，PNG 内容未修改。
- 原文件 SHA-256：`0dd1c39f8333f73da19389b4cda3f62c5658468e93caa5401add19bca33b5f30`。
- 原动作配置：`pet/pet.manifest.json`；副本保存为 `references/shenshen-manifest.json`。
- 本项目修改：保留动画帧顺序、帧时长、循环规则及 16 向朝向，将部分动作 ID 映射到本程序状态，增加睡觉和投喂时的演绎。未把它称作真实进食模拟。
- 许可：在上游有权许可的范围内，视觉素材与改编动作资源遵循 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)；原许可完整保存在 `references/licenses/shenshen-assets.md`，来源说明保存为 `references/licenses/shenshen-origins.md`。原角色与项目谱系按该说明署名，含上善无形及 dsh-pet 系列。
- 推荐署名：Q 版动画基于上善无形的鲸鱼娘形象及 dsh-pet 社区项目谱系，由 Shenshen Pet contributors 制作；本版映射与交互由 FatFish Companion 实现。非官方、非商业使用，CC BY-NC-SA 4.0。

### 成熟版六姿态

- 参考：https://treapgogo.github.io/deepseek-whale-girl/assets/dafeiyu-mature-character-sheet.png
- 本地原参考：`references/mature-reference.png`、`static/mature-reference.png`。
- GPT Image 在本次会话生成，并用 GPT Image 清理透明背景，保存为 `static/pets/mature-atlas.png`。没有从上游提取成熟版动画，六姿态并非上游原作者绘制。
- 动作配置对每格做一致的显示裁剪，并添加眨眼和过渡序列；没有改写 PNG 文件像素。
- 本项目有权许可的这部分二创视觉和 `static/pets/manifest.json` 动作数据按 CC BY-NC-SA 4.0 提供；上游角色与参考的权利仍受原始条款约束。

### 代码与设计参考

- 阅读了 [DeskLLMPet](https://github.com/isKage/desk-llm-pet) 的 `src/main/pet-window.js`（MIT），借鉴透明置顶、拖拽、窗口限制和气泡联动的设计。原生 Qt 代码自行实现，未直接复制其 Electron 代码。未引入它的插件加载器。
- 参考 [DSH Whale Pet](https://github.com/aceice01/dsh-whale-pet) 的任务反馈思路，没有复制其语音或注入脚本。
- Qt 运行依赖 PySide6-Essentials / Shiboken，分别遵循其发行包中的 LGPL/GPL/商业授权条款；本源码启动包不捆绑 Qt 二进制。首次安装通过 pip 获取依赖，依赖包自己的许可文件随其发行包保留。
- 本项目代码仍按 MIT 提供；上述第三方与二创视觉数据不包含在代码的 MIT 授权中。
