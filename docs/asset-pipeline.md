# Campfire 3D Asset Pipeline

本文件定义 Campfire 2.0 的"现实物品"资产流程：
**DCC（Blender）制作 → 导出 `.glb` → `AssetManager` 加载 → `ModelRegistry` 契约适配 → 场景逻辑只通过 `root / anchors / parts` 使用模型**。

- 模型审计与替换依据：[`model-audit.md`](model-audit.md)
- 视觉方向：[`art-direction.md`](art-direction.md)

---

## 1. 目录结构

```
Campfire/
├── index.html                    # 场景与业务逻辑（仍为单文件入口）
├── src/assets/
│   ├── AssetManager.js           # GLTFLoader 封装：加载、缓存、契约解析、实例化
│   └── ModelRegistry.js          # 每个模型的契约（节点名 → anchors / parts）与加载后处理
├── assets/models/                # ★ 正式资产：Blender 制作的 .glb（运行时加载）
│   ├── tent.glb                  # Stage 1 ✔
│   ├── backpack.glb              # Stage 2 ✔
│   ├── chair.glb                 # Stage 2 ✔
│   ├── lantern.glb               # Stage 3 ✔
│   ├── kettle.glb                # Stage 4 ✔（两个根节点：KettleRoot + KettleStandRoot）
│   ├── torch.glb                 # Stage 5
│   ├── pinecone.glb              # Stage 5
│   ├── props/                    # Stage 5：logs、axe、stump、woodpile、mug …
│   └── procedural/               # v1 的"程序模型导出"（供 Blender 参考/覆盖，不是正式资产）
│       ├── models.json           # 覆盖开关
│       └── *.glb
├── assets/source/                # 资产源文件（.blend），供继续在 Blender 中修改
│   ├── tent/tent.blend
│   ├── backpack/backpack.blend
│   ├── chair/chair.blend
│   ├── lantern/lantern.blend
│   └── kettle/kettle.blend       # 每个目录另有 preview.png（Cycles 预览）；textures/ 为构建中间产物，已 gitignore
└── tools/blender/                # 可复现的 Blender 构建脚本（bpy）
    ├── cf_common.py              # Stage 2 起的公共工具：软体造型、表面投影织带、UV0/UV1、烘焙旧化、glTF 导出
    ├── build_tent.py
    ├── build_backpack.py
    ├── build_chair.py
    ├── build_lantern.py
    └── build_kettle.py
```

规则：
- **禁止**把 GLB/贴图 base64 嵌进 HTML；一律作为独立文件由 HTTP 加载。
- `assets/models/*.glb` 是**构建产物**，源头是 `assets/source/*.blend`（或 `tools/blender/*.py` 生成 .blend）。
- 贴图随 GLB 内嵌（`.glb` 二进制块），不单独散落在 `assets/models/`。

---

## 2. 坐标与尺寸标准

| 项 | 标准 |
|---|---|
| 上方向 | glTF **+Y 向上**（Blender 中 +Z 向上，由导出器自动转换） |
| 正面方向 | glTF **+Z 为正面**（= Blender 中 **−Y**，即 Blender "Front" 视图看到的一面）。道具摆放时 +Z 朝向火堆 |
| 单位 | **1 Blender unit = 1 m**，按真实尺寸建模 |
| 原点 | 合理的接地点：地面道具 = 底面中心；手持物 = 握持/旋转枢轴（见各模型契约） |
| 变换 | 根对象 **Scale = 1、Rotation = 0**，导出前 Apply All Transforms |
| 禁止 | 在 Three.js 里用 `scale.set(0.013…)`、`rotation.set(…)` 补救导出错误 |

v1 遗留的违例（替换时一并消除）：~~提灯组 `scale 0.58`~~（Stage 3 已消除，仅程序化回退仍用）、~~水壶 `scale 0.14 + rotation.y π`~~（Stage 4 已消除）。

---

## 3. Model Contract（模型契约）

每个模型在 `ModelRegistry.js` 注册一份契约。场景代码**只**通过 `AssetManager.create(key)` 返回的实例访问模型：

```js
const tent = await assets.create('tent');   // 或 createTentInstance(assets)
tent.root                    // THREE.Object3D，直接 add 到场景 / 道具组
tent.anchors.interiorLight   // THREE.Object3D，帐内暖光位置
tent.parts.door              // THREE.Object3D，门帘
tent.materials.canvas        // （可选）需要代码驱动的材质
```

- 节点名查找（`getObjectByName`）**只**发生在 `ModelRegistry` 的解析函数里；主场景代码不写节点名。
- 必需节点缺失 → 加载失败（抛错），调用方回退到程序化模型；可选节点缺失 → 控制台警告。
- GLTFLoader 会清洗节点名（空格→`_`，去掉 `.:/[]`）；Blender 的 `Door.001` 会变成 `Door001`，解析函数按"精确匹配 → 去掉数字后缀匹配"查找。
- 灯光**不放进 GLB**：点光由代码在锚点处创建并常驻场景根部（光源数量变化会触发全场景着色器重编译）。

### 各模型契约

| key | 根节点 | 必需锚点 / 部件 | 可选 | 加载后处理 |
|---|---|---|---|---|
| `tent` | `TentRoot` | `InteriorLightAnchor`（anchor）、`Door`（part） | `Fly`、`InnerTent`、`GuyLines` | 阴影：细绳/地钉不投影 |
| `backpack` | `BackpackRoot` | — | `HandleSocketL/R`、`LidPivot` | 业务逻辑不依赖内部网格 |
| `chair` | `ChairRoot` | — | `SeatAnchor` | — |
| `lantern` | `LanternRoot` | `LightAnchor`、`Glass`、`Flame`（材质 `LanternGlow`） | `BailPivot` | 玻璃替换为 `MeshPhysicalMaterial`（FrontSide，透明）；火苗材质交给闪烁/生日换色逻辑 |
| `kettle` | `KettleRoot`（原点=壶底中心） | `SteamAnchor`、`Body`、`Handle` | `Lid`、`Spout` | `Body` 材质克隆（受热自发光按实例驱动） |
| `kettle-stand` | `KettleStandRoot` | `RestAnchor`（壶底落点） | — | — |
| `torch` | `TorchRoot`（原点=柄底，轴 +Y） | `FlameAnchor`、`Handle`、`Wrap`（材质 `TorchEmber`） | `GripAnchor` | `Wrap` 材质设 emissive 余烬贴图 |
| `pinecone` | `PineconeRoot`（原点=中心） | — | — | 每个实例克隆材质（燃烧变色） |
| `log` | `LogRoot`（原点=中心，长轴 +Y） | — | `CharEnd` | 共享材质 |
| `axe` | `AxeRoot`（原点=斧头与柄交接处，柄 +Y，刃 +Z） | `BladeEdge` | `GripAnchor` | 若枢轴变化需重调 `CHOP_POSE` |
| `stump` | `StumpRoot` | `TopAnchor`、`AxeSocket` | — | — |

---

## 4. PBR 材质标准

- glTF 2.0 metallic-roughness：`baseColor`（sRGB）、`normal`（切线空间，OpenGL/+Y 约定）、`metallicRoughness`（G=roughness, B=metallic）、`occlusion`（R）。
- AO / Roughness / Metallic **打包成一张 ORM**（R=AO, G=Roughness, B=Metallic），与 glTF 通道一致。
- 两套 UV：
  - **UV0（TEXCOORD_0）**：按真实尺寸平铺的细节 UV（织纹、木纹法线），可超出 0..1；
  - **UV1（TEXCOORD_1）**：不重叠的唯一展开，承载烘焙的 baseColor（含旧化）与 ORM。
- 旧化（泥点、日晒褪色、烟熏、积灰）在 Blender 里用程序节点表达并**烘焙**进 UV1 贴图，运行时零成本。
- 同一模型内相同参数的材质必须合并；单件道具 ≤ 6 个材质（帐篷这类复合物 ≤ 10）。
- 允许的 glTF 扩展：`KHR_texture_transform`、`KHR_materials_emissive_strength`、`KHR_materials_clearcoat`。暂不使用 Draco/Meshopt/KTX2（体积在预算内时不引入额外解码器）。

---

## 5. 性能预算（现代桌面浏览器 + 普通笔记本）

| 模型 | 三角形上限 | 材质 | 贴图 |
|---|---|---|---|
| Tent（复合物：外帐+内帐+杆+绳+陈设） | 30 k | ≤ 10 | 1× 1024 baseColor + 1× 1024 ORM + 1× 512 平铺法线 |
| Backpack | 15 k | ≤ 5 | 1024 套 |
| Chair | 6 k | ≤ 3 | 512–1024 |
| Lantern | 10 k | ≤ 5 | 1024 套 |
| Kettle + Stand | 10 k | ≤ 4 | 1024 套 |
| Torch | 4 k | ≤ 3 | 512 套 |
| Pinecone | 2 k（最多同时 9 个） | 1 | 512 |
| Log / Axe / Stump / Mug | 各 ≤ 2–3 k | ≤ 2 | 512，共享木材贴图 |

- **全部营地道具合计 ≤ 100 k 三角形、≤ 15 MB GLB 下载、贴图显存 ≤ 64 MB**。
- 基础色 JPEG（q≈90），ORM JPEG，法线 PNG；贴图尺寸为 2 的幂。
- 导出前：Apply modifiers、删除看不见的面（如贴地底面、被遮挡内侧）、合并重复材质、法线平滑+硬边标记（Weighted Normal）、清理非流形。
- 不导入雕刻级高模；需要的细节烘焙成法线。

---

## 6. 导出设置（Blender 4.x glTF 2.0 Exporter）

| 选项 | 值 |
|---|---|
| Format | glTF Binary (`.glb`) |
| Include | Custom Properties ✔（extras 带阴影标记等）；Cameras ✘；Punctual Lights ✘ |
| Transform | +Y Up ✔ |
| Mesh | Apply Modifiers ✔；UVs ✔；Normals ✔；Tangents ✘（运行时 MikkTSpace/导数切线）；Vertex Colors 仅在材质使用时 |
| Material | Export；Images: Automatic（保留源图的 JPEG/PNG） |
| Compression | 关闭（见 §4） |
| Animation | 关闭（动画由代码驱动） |

校验：
1. `gltf-validator`：0 error；
2. Blender 重新导入：尺寸、原点、朝向正确；
3. 页面加载：控制台无 `[assets]` 警告，契约节点齐全。

---

## 7. 运行时：AssetManager

```js
import { AssetManager, createTentInstance } from './src/assets/AssetManager.js';
const assets = new AssetManager({ renderer });
const ready = assets.preload(['tent']);        // 场景构建前发起，与其余初始化并行
// …
await ready;
const tent = await createTentInstance(assets); // 失败时抛错 → 回退程序化 makeTent()
```

- `loadGLTF(url)`：单一 `GLTFLoader`，按 URL 缓存 Promise；
- `load(key)`：加载 + 契约校验 + 加载后处理，缓存"模板"；
- `create(key)`：克隆模板（几何/贴图共享，契约声明需要逐实例的材质才克隆），返回 `{ root, anchors, parts, materials }`；
- 贴图各向异性过滤按渲染器上限设置；`castShadow/receiveShadow` 按契约的阴影策略设置。

---

## 7.1 Stage 1 实测（tent.glb）

| 项 | 数值 |
|---|---|
| 三角形 | 25 654（预算 30 k） |
| 材质 | 9：TentCanvas、TentTrim、InnerFabric、TentFloor、PoleMetal、Cordage、SleepingBag、LampBody、LampGlow |
| 贴图 | baseColor 1024 JPEG（UV1，含旧化）+ ORM 1024 JPEG（UV1）+ 织纹法线 512 PNG（UV0，每 15 cm 平铺） |
| 文件 | `tent.glb` 1.26 MB；`tent.blend` 1.1 MB（贴图已打包） |
| 校验 | gltf-validator 0 error（仅"运行时生成切线"提示）；Blender 4.5 导入尺寸/原点/朝向正确 |
| 契约 | `TentRoot` / `Door` / `InteriorLightAnchor` 齐全；`GuyLines`、`InteriorLampBody/Glow` 带 `noCastShadow` |
| 构建 | `tools/blender/build_tent.py`（建模 → UV → Cycles 烘焙 → 导出），约 1.5 min（CPU） |

## 7.2 Stage 2 实测（backpack.glb / chair.glb）

| 项 | backpack | chair |
|---|---|---|
| 三角形 | 14 678（预算 15 k） | 6 244（预算 8 k） |
| 材质 | 6：PackFabric、Webbing、HardwarePlastic、HardwareMetal、Thread、Cord | 5：ChairFabric、ChairFrame、ChairPlastic、ChairRivet、Thread |
| 贴图 | 布料 baseColor + ORM 1024 JPEG（UV1，含灰尘/褪色/磨边/污渍）；平纹法线 512（UV0）；织带斜纹法线 256（UV0） | 布料 baseColor + ORM 1024 JPEG（UV1）；平纹法线 512（UV0） |
| 文件 | 1.42 MB（.blend 1.2 MB） | 0.73 MB（.blend 0.7 MB） |
| 校验 | gltf-validator 0 error（仅"运行时生成切线"提示） | 同左 |
| 契约 | `BackpackRoot`；可选 `LidPivot`（顶袋铰点）、`HandleSocketL/R`（提手） | `ChairRoot`；可选 `SeatAnchor`（坐姿参考点） |
| 构建 | `tools/blender/build_backpack.py`，约 1.5 min | `tools/blender/build_chair.py`，约 1 min |

实现要点：
- 包体/顶袋/侧袋用超椭球 + 形变做"装满东西"的软体轮廓；压缩带、顶袋带用 BVH 投影贴合包面（不再是悬空方条）。
- 椅子为 X 型交叉腿 + 扶手的露营折叠椅；座/背布为有下垂量的吊床式网格，双面渲染（`cull=False`），管套、包边、杯托独立建模。
- 颜色在篝火暖光下校准：椅布去饱和的铁锈红 `#6b3a2f`，背包橄榄绿 `#4b5034`（初版在火光中过饱和 / 发白，已调暗）。
- 场景端仅把 `makeChair()` / `makeBackpack()` 换成 `assetOrFallback('chair' | 'backpack', …)`；摆放、阴影、导出逻辑不变，GLB 缺失时自动回退到程序化模型。

## 7.3 Stage 3 实测（lantern.glb）

| 项 | 数值 |
|---|---|
| 三角形 | 10 824（预算 10 k，超 8%：主要是护丝、提梁等细管的圆周段数，已降到 6~8 边） |
| 材质 | 5：LanternPaint（烘焙）、LanternWire、LanternBrass、LanternGlass（运行时替换）、LanternGlow |
| 贴图 | 漆面 baseColor + ORM 1024 JPEG（UV1）：褪色、灯脚污垢、烟罩烟熏、**掉漆露钢（ORM 蓝通道 = 金属度）+ 锈边** |
| 文件 | 0.70 MB（.blend 0.64 MB） |
| 校验 | gltf-validator 0 error / 0 warning |
| 尺寸 | 实物比例：油壶 Ø 0.21 m，灯帽顶 0.32 m，提梁立起 0.38 m；场景里不再缩放（旧程序模型需 `scale 0.58`） |
| 契约 | `LanternRoot` / `LightAnchor`（火苗中心，y = 0.155）/ `Glass` / `Flame`（`LanternGlow`）/ `BailPivot`（提梁向后倾 26° 靠放） |
| 阴影 | 只有油壶、燃烧器、烟罩投影；侧管、护丝、提梁、玻璃、火苗 `noCastShadow`（灯光就在它们内侧几厘米，否则地面出现放射状硬条纹） |
| 构建 | `tools/blender/build_lantern.py`，约 2 min |

灯光复查（Stage 3）：
- **灯体近场过曝**：点光在火苗中心，油壶肩、侧管内侧距光源 3~10 cm，按 1/d²（three 默认下限 10 cm）被推到饱和白（蓝漆 × 橙光 ≈ 中性灰 → 白）。`ModelRegistry.lantern.prepare` 只对提灯自身材质把衰减距离下限改为 50 cm（`softNearField`，通过 `onBeforeCompile` 局部修改，不动全局 ShaderChunk）；地面光斑与其他物体不变。依据：真实火苗是几厘米的面光源、且大部分被燃烧器挡住。
- **地面光斑**：火苗高度从 ≈0.22 m 降到 0.155 m，相同距离地面照度约 ×1.2，`LANTERN_INT` 3.2 → 2.8。
- 漆面粗糙度 0.62、钢丝 0.6、黄铜 0.45：避免火苗在侧管上形成白色高光条。

## 7.4 Stage 4 实测（kettle.glb：水壶 + 支架）

| 项 | 数值 |
|---|---|
| 三角形 | 8 524（预算 10 k）：壶 4 632（Body 2 016、Spout 1 172、Handle 724、Lid 720）、支架 3 892 |
| 材质 | 3：KettleIron（壶，逐实例克隆 → 受热自发光）、StandIron（支架，与壶共用同一张烘焙图集）、KettleGrip（木握把） |
| 贴图 | baseColor + ORM 1024 JPEG（UV1，两者共用）：养护过的黑铸铁、边缘与提梁磨亮露金属、锈斑、**壶底烟熏**（新增 `soot_bottom`）、支架顶圈烟熏 |
| 文件 | 0.68 MB（.blend 0.64 MB） |
| 校验 | gltf-validator 0 error / 0 warning |
| 尺寸 | 壶 Ø 0.36 m（12 L 吊壶），盖钮顶 0.29 m，提梁 0.42 m；支架顶圈 r 0.127 m、上沿 0.588 m，脚落在 r 0.80 m |
| 契约 | `KettleRoot`（原点 = 圈足中心，壶嘴 +X）/ `SteamAnchor` / `Body` / `Handle` / `Lid` / `Spout` / 材质 `KettleIron`；`KettleStandRoot` / `RestAnchor`（顶圈上沿） |
| 构建 | `tools/blender/build_kettle.py`，约 1 min；.blend 里壶直接坐在支架上，便于整体微调 |

接入与复查：
- 去掉旧模型的 `scale 0.14 + rotation.y π`；`kettle` 组仍是动画目标（放置 / 取回路径不变），GLB 挂在其下。
- 蒸汽发射点由 `SteamAnchor` 提供（原硬编码 `(0.38, 0.31, 0)`），壶底落点 `KETTLE_REST` 由支架 `RestAnchor` 提供（原硬编码 0.59）。
- 受热发光：`prepare` 设置暗橙红自发光色，强度仍由「煮水」进度驱动；材质按实例克隆，不影响支架。
- 支架四腿从 45° 改到 22.5° + k·90°：旧支架腿与 8 根 teepee 木柴（k·45°）重合、穿模。
- 尺寸：真实 2~3 L 小壶（Ø 0.26 m）在这堆篝火（木柴展开约 1.3 m）里会被火焰完全吞没，所以做成 12 L 吊壶（Ø 0.36 m）；旧壶 Ø 0.56 m。
- 程序化回退仍保留，且旧壶的 4 张 1024 铸铁 PNG 只在回退时才加载。
- 蒸汽粒子球 8×6 段 → 16×12 段（近景可见棱面），蒸汽逻辑不变。

## 8. 分阶段计划

每个阶段：Blender 制作 → 导出校验 → 接入（保留程序化回退）→ **与上一版本截图对比** → 再进入下一阶段。

| Stage | 内容 | 验证重点 |
|---|---|---|
| **1** ✔ | **Tent** + AssetManager / ModelRegistry 基础设施 | 帆布质感、接缝、褶皱、门帘厚度、拉绳；帐内暖光位置不变；冷暖关系 |
| **2** ✔ | **Backpack + Chair** | 布料/织带/扣具的粗糙度差异；营地生活感 |
| **3** ✔ | **Lantern** | 喷漆金属、黄铜、玻璃、局部光与火光叠加 |
| **4** ✔ | **Kettle + Stand** | 与放置动画、受热自发光、蒸汽锚点结合 |
| 5 | Torch / Pinecone / Logs / Axe / Stump / WoodPile / Mug | 互动锚点、实例化与材质克隆 |

每阶段结束同步复查光照：月光、篝火点光、提灯局部光、阴影柔和度、色调映射与曝光、自发光强度、粗糙度响应、接触阴影。

---

## 9. 第一轮代码修改范围（Stage 1）

1. 新增 `src/assets/AssetManager.js`、`src/assets/ModelRegistry.js`（`tent` 契约）。
2. `index.html`：
   - 导入 AssetManager，场景构建开始时预加载 `tent`；
   - 帐篷摆放处改为 `createTentInstance()`，失败回退 `makeTent()`；
   - 帐内暖光 `TentGlow` 由 `anchors.interiorLight` 定位（仍常驻场景根部）；
   - v1 的"程序模型覆盖"移到 `assets/models/procedural/`，`tent` 从覆盖列表移除；覆盖加载复用 AssetManager 的 GLTFLoader。
3. 新增 `tools/blender/build_tent.py`（可复现构建）、`assets/source/tent/tent.blend`、`assets/models/tent.glb`。
4. 不改动：火焰/火星/烟/燃料/天气/音频/国际化/生日彩蛋/森林海边切换，以及其余道具。
