# Campfire / 夜间篝火

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.ja.md">日本語</a>
</p>

一个基于 Three.js 的自包含夜间篝火互动场景。  
项目主体集中在单个 `index.html` 文件中，Three.js 通过 CDN 加载，无需构建工具，也无需安装依赖。

---

## 项目简介

**Campfire** 是一个可直接在浏览器中运行的夜间篝火演示项目。它结合了粒子火焰、火星、烟雾、月光、雾气、天气控制和 Web Audio 程序化音效，营造出一个安静的夜间露营氛围。

适合用于学习和实验：

- Three.js 场景搭建
- 粒子火焰、火星与烟雾效果
- Web Audio 程序化音效
- 3D 空间声音与距离衰减
- 简单物理模拟
- 实时参数调节
- 多语言 UI 交互

---

## 主要功能

### 夜间篝火场景

场景包含火焰、木柴、火星、烟雾、月光、雾气、云量、细雨和夜间环境光，形成一个可交互的夜间露营环境。

自然环境全部为程序化建模：

- **针叶树**：云杉（多层下垂轮生枝、带尖梢的枝簇）与松树（高干 + 团簇状树冠），树干贯穿树冠、带板根与树皮贴图；中景另有实例化的背景林
- **远山**：一整圈脊状多重分形山脉，内缘与地面无缝衔接，山脚林带、岩壁、雪顶按海拔与坡度着色；朝月亮/湖面方向压低，留出赏月视野
- **地形**：梯度噪声 fBm 起伏，营地与湖区平整，向山脚渐起林地缓坡
- **海边**：海岸丘陵（两翼没入海中成岬角）、礁岛、羽状复叶棕榈

### 参数调节面板

右上角参数面板提供实时滑块，可调节：

- 火焰强度
- 热浮升力
- 火星生成率
- 烟雾量
- 风速
- 总音量
- 噼啪声频率
- 距离衰减
- 空气高频吸收
- 细雨
- 云量
- 月相
- 月光强度
- 雾浓度
- 画面曝光

所有参数都会即时生效。

### 加柴交互

点击底部的 **加柴** 按钮后，木柴会从镜头一侧飞入火堆。该过程包含：

- 抛物线运动
- 翻滚动画
- 火星迸发
- 烟尘上升
- 3D 定位闷响
- 燃料增长
- 火势增强
- 噼啪声短时间增多

燃料会随时间逐渐燃烧衰减，火势也会自然回落。

### 营火互动

项目提供四种可并行进行的营火互动：

- **烤棉花糖**：棉花糖伸入火焰，并逐渐焦糖化。
- **煮水**：水壶悬挂在火焰上方，加热后产生蒸汽。
- **点燃火把**：火把伸入火焰后被点燃，再次点击可熄灭。
- **投掷松果**：松果落入火堆，迸出火星并补充少量燃料。

### 三语界面

界面支持三种语言即时切换：

- 中文
- English
- 日本語

按钮、状态提示和进度反馈都会随语言切换更新。

### 程序化声音

所有声音均由 Web Audio API 实时合成，无需外部音频文件。

声音包括：

- 火焰低频轰鸣
- 木柴噼啪声
- 偶发爆裂声
- 加柴闷响
- 基于距离的声音衰减
- 空气吸收造成的远距离声音变暗

---

## 运行方式

由于项目使用 ES Module，建议通过本地 HTTP 服务打开。

```bash
python -m http.server 8341
```

然后在浏览器访问：

```text
http://localhost:8341
```

进入页面后，点击任意位置以开启声音。  
这是浏览器对 Web Audio 的限制：音频通常需要用户手势后才能播放。

---

## 操作方式

| 操作 | 说明 |
|---|---|
| 鼠标拖动 | 旋转视角 |
| 鼠标滚轮 | 缩放视角 |
| 点击页面 | 启动声音 |
| 点击“加柴” | 向火堆添加木柴 |
| 点击互动按钮 | 触发烤棉花糖、煮水、点火把或投掷松果 |
| 调节参数面板 | 实时改变火焰、声音、天气和环境效果 |

---

## 物理与视觉模拟

| 现象 | 实现方式 |
|---|---|
| 声音随距离衰减 | `PositionalAudio` 与 inverse 距离模型 |
| 双耳定位 | HRTF 空间音频 |
| 空气吸收高频 | 距离越远，高频越少 |
| 火光衰减 | 点光源平方反比衰减 |
| 火焰上升 | 热浮升力、空气阻力、湍流扰动和向轴心收束 |
| 焰体分层 | 焰底幽蓝、内焰白黄、外焰橙红半透明 |
| 火星轨迹 | 重力、空气阻力、热羽流升力 |
| 烟雾飘散 | 上升、扩散、受风偏移、逐渐消散 |
| 噼啪声 | 随机过程触发的短促爆裂音 |
| 燃烧轰鸣 | 低频噪声与火势强度联动 |

---

## 3D 资产管线（2.0）

营地里的现实物品正逐步从"Three.js 程序几何拼装"升级为 **Blender 制作的 `.glb` 正式资产**：

- 审计：[`docs/model-audit.md`](docs/model-audit.md) —— 每个物品的生成函数、几何、材质、动画/互动依赖与必须保留的锚点
- 视觉方向：[`docs/art-direction.md`](docs/art-direction.md) —— 安静、温暖、有人住过、略有风霜的写实夜营地；冷月光 + 暖篝火
- 管线规范：[`docs/asset-pipeline.md`](docs/asset-pipeline.md) —— 坐标标准、模型契约、PBR、性能预算、分阶段计划
- 运行时：`src/assets/AssetManager.js`（GLTFLoader 加载/缓存/实例化）+ `src/assets/ModelRegistry.js`（节点契约）
- 资产源：`tools/blender/*.py`（可复现的 Blender 构建脚本）→ `assets/source/*/*.blend` → `assets/models/*.glb`

| 阶段 | 模型 | 状态 |
|---|---|---|
| Stage 1 | 帐篷 Tent | ✔ `assets/models/tent.glb`（帆布织纹、接缝、张力褶皱、门帘、拉绳、帐内陈设；约 2.6 万三角形、1.3 MB） |
| Stage 2 | 背包、折叠椅 | ✔ `backpack.glb`（装满的软体包身、贴合包面的压缩带、扣具、弹力绳、防潮垫、缝线；约 1.5 万三角形、1.4 MB）· `chair.glb`（X 型折叠露营椅、下垂的座/背布、管套、杯托；约 6 千三角形、0.7 MB） |
| Stage 3 | 提灯 | ✔ `lantern.glb`（防风煤油灯：冲压油壶、两侧进气管、烟罩、黄铜燃烧器与灯芯旋钮、护丝内的玻璃灯罩、提梁；搪瓷漆掉漆露钢、烟熏；约 1.1 万三角形、0.7 MB） |
| Stage 4 | 水壶 + 支架 | 待制作 |
| Stage 5 | 火把、松果、木柴、斧头、树桩等 | 待制作 |

重新生成资产（需要 Blender 4.x，或 `pip install bpy`）：

```bash
blender --background --python tools/blender/build_tent.py      # 输出 assets/models/tent.glb 与 assets/source/tent/tent.blend
blender --background --python tools/blender/build_backpack.py  # backpack.glb + assets/source/backpack/backpack.blend
blender --background --python tools/blender/build_chair.py     # chair.glb + assets/source/chair/chair.blend
blender --background --python tools/blender/build_lantern.py   # lantern.glb + assets/source/lantern/lantern.blend
```

也可以直接打开 `assets/source/<名称>/<名称>.blend` 修改，再按 `docs/asset-pipeline.md` §6 的设置导出覆盖 `assets/models/<名称>.glb`。
正式资产加载失败（如文件缺失）时，页面自动回退到原来的程序化模型。

---

## Blender 模型互通（程序化模型）

场景中的模型可以导出为 **glTF 2.0（.glb）**，在 Blender 中直接打开、微调，再放回页面替换程序化模型。

### 1. 导出

右上角参数面板底部 **「Blender 模型」**：选择目标 → 点击 **导出 .glb**，浏览器下载 `<名称>.glb`。

| 目标 | 内容 | 可覆盖回页面 |
|---|---|---|
| 整个场景（当前） | 当前森林/海边环境 + 营地 + 火堆 + 灯光 + 相机 | — |
| 地形 | 当前场景的地面网格 | — |
| 远山（森林） / 海岸丘陵与礁岛 | 远景山体 + 林带剪影 | ✓ |
| 云杉 / 松树 / 棕榈 | 单棵树模板（树根在原点，高约 7~9 m） | ✓ 替换该树种的全部树 |
| 帐篷 / 折叠椅 / 背包 / 提灯 | 当前场景中的模型（已是正式 GLB 资产） | —（直接编辑 `assets/source/<名称>/<名称>.blend`） |
| 柴垛 / 劈柴桩与斧头 / 搪瓷杯 | 单个道具（以自身原点导出） | ✓ |
| 火堆（石圈与木柴） | 石块、木柴、炭块 | —（木柴有坍塌动画） |

`assets/models/procedural/` 中已附带 8 个可覆盖模型的 .glb，可直接用 Blender 打开。

### 2. 在 Blender 中打开

`文件 ▸ 导入 ▸ glTF 2.0 (.glb/.gltf)`。单位为米，Y-up 会自动转换为 Blender 的 Z-up，材质为 Principled BSDF。导出时已做以下处理：

- 火焰粒子、星空、月亮、碎光等运行时特效不导出
- 实例化对象（背景林、碎石等）导出为**关联复制**，编辑一个全部同步
- 凹凸贴图转换为法线贴图；法线贴图绿通道已按 glTF 约定校正
- 树木/山体使用**顶点色**表达明暗层次（材质中的 Color Attribute 节点）
- 对象、材质均有可读名称（如 `Tree_spruce_03 › Spruce › Foliage`、`TentFabric`）

### 3. 微调后放回页面

1. 在 Blender 中 `文件 ▸ 导出 ▸ glTF 2.0`，格式选 **glTF Binary (.glb)**，以**同名**保存到 `assets/models/procedural/`（如 `mug.glb`）
2. 编辑 `assets/models/procedural/models.json`，把对应项改为 `true`（也可以写成文件名，如 `"mug": "mug_v2.glb"`）
3. 刷新页面（需通过 HTTP 服务打开）。浏览器控制台会打印 `[models] mug ← assets/models/procedural/mug.glb`

注意事项：

- **保持根对象在原点、不要移动整体位置**：摆放位置与朝向由页面决定，模型文件只描述模型本身
- 劈柴桩：斧头对象名为 `Axe`（劈柴动画依赖）；若删掉则沿用程序化斧头
- 导出时勾选 `Include ▸ Custom Properties`，可保留 `noCastShadow` 等阴影标记
- 灯光强度单位与 Blender 不同，若导入整个场景后灯光过暗/过亮，可在导入选项的 `Lighting Mode` 中调整

---

## 项目结构

```text
Campfire/
├── index.html
├── README.md
├── README.zh-CN.md
├── README.ja.md
├── docs/                # 模型审计、视觉方向、资产管线规范
├── src/assets/          # AssetManager.js、ModelRegistry.js
├── tools/blender/       # Blender 资产构建脚本（bpy）
├── assets/
│   ├── textures/
│   ├── models/          # 正式 .glb 资产（帐篷、背包、折叠椅、提灯 …）
│   │   └── procedural/  # 程序化模型导出 + models.json（覆盖开关）
│   └── source/          # 资产源文件 .blend
├── scripts/
└── .claude/
```

---

## 说明

- 本项目定位为轻量级浏览器演示。
- 无需构建步骤。
- 音频需要用户点击页面后才会启动，这是浏览器自动播放策略导致的。
- 建议使用现代桌面浏览器获得最佳体验。

---

## 许可证

当前尚未指定许可证。  
如果计划公开分享或复用该项目，建议添加 MIT 等开源许可证。
