# Campfire 模型审计（Model Audit）

> 审计对象：`index.html`（v1.x，单文件 Three.js r165）。
> 目的：找出所有**用 Three.js 程序几何拼装的现实物品**，记录它们与业务逻辑的耦合点，
> 判断能否直接替换为 Blender 制作的 `.glb`，以及替换时必须保留的锚点（anchor / pivot / interaction point）。
>
> 坐标约定（下文所有数值）：Three.js 世界 / 道具局部坐标，Y 向上，单位米。
> 道具经 `placeProp(group, az, r)` 摆放：组原点落在 `(cos az·r, 0, sin az·r)`，局部 **+Z 正面朝向火堆**。
> 三角形数来自运行时统计（`renderer` 场景遍历，含全部子网格）。

---

## 0. 总览

| # | 物品 | 生成函数 / 位置 | 三角形 | 动画 | 互动 | 位置计算依赖 | 可直接换 GLB | 必须保留的锚点 |
|---|---|---|---|---|---|---|---|---|
| 1 | 帐篷 Tent | `makeTent()` | 828 | 否 | 收拾/摆放（显隐） | 帐内点光位置 | **是（Stage 1）** | `InteriorLightAnchor`、`Door` |
| 2 | 登山包 Backpack | `makeBackpack()` | 5 396 | 否 | 收拾/摆放 | 无 | **是（Stage 2）** | `BackpackRoot`（其余可选） |
| 3 | 折叠椅 Chair | `makeChair()` | 508 | 否 | 收拾/摆放 | 无 | **是（Stage 2）** | `ChairRoot` |
| 4 | 煤油提灯 Lantern | `makeLantern()` | 6 048 | 火苗材质闪烁 | 收拾/摆放、生日换色 | **提灯点光 + 飞蛾环绕点** | **是（Stage 3）** | `LightAnchor`、`Glass`、火苗发光材质 |
| 5 | 水壶 Kettle | 顶层块 `kettle` | 8 044 | 放置/取回路径、受热自发光、蒸汽 | 「煮水」 | 支架顶圈高度、蒸汽口位置 | **是（Stage 4）** | `SteamAnchor`、`Body`、`Handle`、底面原点 |
| 6 | 水壶支架 KettleStand | 顶层块 `kettleRig` | 576 | 随水壶显隐 | 「煮水」 | 顶圈 y=0.575 决定 `KETTLE_REST` | 是（Stage 4，与水壶同批） | `RestAnchor`（顶圈中心） |
| 7 | 火把 Torch | `makeTorchModel()` | 1 486 | 移入火中/取回、倾斜、缠布余烬 | 「点燃火把」 | 火焰发射点、点光 | **是（Stage 5）** | `FlameAnchor`、`Wrap`、`Handle` |
| 8 | 松果 Pinecone | `pineconeGeo` + `throwPinecone()` | ≈ 2 100 / 个 | 抛物线、翻滚、燃烧变色缩小 | 「投掷松果」 | 落点高度 y=0.19 | **是（Stage 5）** | 原点=几何中心；材质可逐个克隆 |
| 9 | 篝火木柴 TeepeeLogs | 篝火块（8 根） | ≈ 1 200 | **坍塌**（四元数插值）、炭化变色 | 燃料系统 | 外端 r≈0.65、内端 y≈0.45 | 部分（Stage 5，需保留炭化段） | 每根：底端原点 + 轴向 +Y、`CharEnd` 子网格 |
| 10 | 加柴木柴 AddedLog | `tossLog()` | ≈ 140 / 根 | 抛物线、翻滚 | 「加柴」 | 落点高度 0.30~0.42 | 是（Stage 5） | 原点=几何中心，长轴 +Y |
| 11 | 柴垛 WoodPile | `makeWoodPile()` | 1 120 | 否 | 收拾/摆放 | 无 | 是（Stage 5） | `WoodPileRoot` |
| 12 | 劈柴桩 ChopStump | `makeStump()` | 206（含斧头） | 否（斧头见下） | 「劈柴」 | 桩顶 y=0.342 | 是（Stage 5） | `TopAnchor`、`AxeSocket` |
| 13 | 斧头 Axe | `makeStump()` 内 `axe` | ≈ 100 | **三关键帧抡斧**（位置+欧拉角） | 「劈柴」 | `CHOP_POSE` 以斧头组原点为枢轴 | 是（Stage 5，需重设枢轴） | `AxeRoot` 原点 = 斧头与柄交接处 |
| 14 | 待劈原木 / 半柴 / 木屑 | `chopLog`、`makeChopHalf()`、`chopChipGeo` | ≈ 300 | 下落、劈开飞散、弹跳 | 「劈柴」 | 半柴静止高度 0.058 | 是（Stage 5） | 半柴：劈面朝 +Z 的原点 |
| 15 | 搪瓷杯 Mug | `makeMug()` | 360 | 否 | 收拾/摆放 | 无 | 是（Stage 5 顺带） | `MugRoot` |
| 16 | 棉花糖 + 竹签 | 顶层块 `skewer` / `marshmallow` | 460 | **竹签按两点瞄准缩放**、棉花糖自转、焦糖化变色 | 「烤棉花糖」、生日彩虹色 | 手/签尖轨迹 | 部分（竹签长度靠缩放，暂保留程序化） | 棉花糖材质需可逐帧改色 |
| 17 | 篝火石圈 FireStones | 篝火块（14 块） | ≈ 4 500 | 否 | 否 | 石圈半径 0.98（限定火焰/支架范围） | 可以但**不建议**（见 §3） | — |
| 18 | 炭床 Embers | 篝火块（46 块） | ≈ 900 | 自发光脉动 | 否 | 否 | 不建议（程序化脉动更便宜） | — |

非营地物品（树、山、地形、散布物、海边元素）按项目规则**保留程序化**，见 §3。

---

## 1. 营地道具（placeProp 体系）

所有这些道具都通过 `placeProp(group, az, r, faceIn, key)` 放置：
- 组原点贴地（y = 0，营地 r < 4.5 m 为平地），`faceIn` 时旋转使 **+Z 朝向火堆**；
- `applyPropShadows()` 统一设置投影（`userData.noCastShadow` / `noCastShadowTree` 可排除）；
- 组被收入 `campProps`，「收拾物品」只切换 `group.visible`，不销毁；
- `PROP_GROUPS[key]` 供 Blender 导出/覆盖查找。

### 1.1 帐篷 Tent — `makeTent()`

| 项 | 内容 |
|---|---|
| 摆放 | `placeProp(tent, 2.30, 3.1, true, 'tent')`，左后方，门朝火 |
| 尺寸 | 宽 1.6 × 长 1.95 × 脊高 1.06 m；拉绳地钉到 z = ±1.53 |
| Geometry | 手写 `BufferGeometry` 两侧帆布（5×10 网格 + 垂坠公式）；`ShapeGeometry` 后墙、带门洞前墙、梯形内壁；`CapsuleGeometry` 门帘卷；`CylinderGeometry` ×6（系带、拉绳、地钉） |
| Material | 5 个 `MeshStandardMaterial`：帆布 `TentFabric`（纯色 0x3a6651，DoubleSide）、门帘、拉绳、地钉、内壁 `TentInnerGlow`（emissive 0xff9a46 × 0.55 伪装帐内灯光） |
| Texture | **无**——帆布没有纹理、接缝、褶皱，只有低频垂坠 |
| 动画 | 无 |
| Interaction | 收拾/摆放（显隐）；帐内点光 `TentGlow` 在收拾时强度归零 |
| Position / collision | 帐内点光 `PointLight(0xffb26a, 0.9, 2.6, 2)` 位于局部 `(0, 0.5, D/2−0.3)`；摆放后 `scene.attach()` 到根部（**光源数量必须恒定**，否则全场景着色器重编译卡顿） |
| 直接换 GLB | **是**。业务逻辑只依赖：组原点、+Z 正面、帐内光位置 |
| 必须保留 | `TentRoot`（原点=地面中心）、`InteriorLightAnchor`（帐内暖光位置，保持与现有 (0, 0.5, 0.675) 一致）、`Door`（门帘/门洞部件，后续可做开合） |
| 问题 | 最大、最靠前的物体却是最粗糙的：平涂颜色、塑料感、无厚度、无接缝/褶皱/张力、拉绳是 5 边棱柱 |

### 1.2 登山包 Backpack — `makeBackpack()`

| 项 | 内容 |
|---|---|
| 摆放 | `placeProp(makeBackpack(), 0.62, 2.15, true, 'backpack')` |
| Geometry | `ExtrudeGeometry` ×10（包身、翻盖、加固底、前袋、侧袋、扣具框）、`BoxGeometry` ×19（织带、扣舌、锚点、缝线实例）、`TubeGeometry` ×9（弹力绳、肩带、提手、滚边）、`CapsuleGeometry`（背垫）、`SphereGeometry` ×2（腰带翼） |
| Material | 6 个 `MeshStandardMaterial`：canvas / reinforced / webbing（64 px 画布程序贴图 map+roughness+bump+ao）、cord、hardware、seam |
| Texture | 运行时画布生成 64×64 平铺贴图（分辨率低、平铺感明显） |
| 动画 | 无（`userData.actionProfile` 描述了开盖/提手，但当前未使用） |
| Interaction | 收拾/摆放 |
| Position | 无依赖 |
| 直接换 GLB | **是** |
| 必须保留 | `BackpackRoot`；可选 `HandleSocketL/R`、`LidPivot`（为将来"开盖"预留，不强制） |
| 问题 | 挤出体圆角生硬、织带是方盒、缝线是小方块实例；布料无褶皱 |

### 1.3 折叠椅 Chair — `makeChair()`

| 项 | 内容 |
|---|---|
| 摆放 | `placeProp(makeChair(), 0.15, 1.95, true, 'chair')` |
| Geometry | `CylinderGeometry` ×13（X 腿、侧轨、横撑、靠背柱、扶手，经 `makeBeamBetween` 两点定向）、`PlaneGeometry` ×2（下垂座面/靠背布） |
| Material | `ChairFrame`（金属度 0.3）、`ChairFabric`（纯色 0x7a2d2d，DoubleSide） |
| Texture | 无 |
| 动画 / 互动 | 无 / 收拾摆放 |
| 直接换 GLB | **是** |
| 必须保留 | `ChairRoot`；可选 `SeatAnchor`（将来人物/道具放置点） |
| 问题 | 管材无接头、布面无厚度无缝边，扶手是细圆柱 |

### 1.4 煤油提灯 Lantern — `makeLantern()`

| 项 | 内容 |
|---|---|
| 摆放 | `placeProp(lant.group, 1.25, 2.5, true, 'lantern')`，组缩放 0.58（**Three.js 侧补救尺寸**，违反新坐标标准） |
| Geometry | `LatheGeometry` ×5（油壶、接缝、燃烧器、玻璃罩、灯帽）、`TorusGeometry` ×7、`TubeGeometry` ×7（框架、提梁、护笼）、`CylinderGeometry` ×4、`SphereGeometry` ×3（火苗、通风孔实例） |
| Material | `steel`、`steelDark`、`brass`（纯色 PBR 参数）、`LanternGlass`（MeshPhysical，透明 0.2，FrontSide）、`LanternGlow`（emissive 2.4） |
| Texture | 无——没有漆面、旧化、烟熏 |
| 动画 | 火苗 `LanternGlow.emissiveIntensity` 每帧闪烁（`lanternFlick`） |
| Interaction | 收拾/摆放（强度归零）；生日彩蛋改 `lanternGlowMat.color/emissive` 与 `campLight.color` |
| Position | **`campLight`（PointLight 3.2 cd，投影）位置 = 灯芯挂点 `lanternLightSocket` 世界坐标**；前 3 只飞蛾环绕 `campLight.position` |
| 直接换 GLB | **是**，但必须提供锚点与可识别的发光材质 |
| 必须保留 | `LanternRoot`、`LightAnchor`（点光+飞蛾中心）、`Glass`（加载后换成 MeshPhysicalMaterial）、火苗网格 `Flame`（材质名 `LanternGlow`，代码驱动闪烁和换色）；可选 `BailPivot` |
| 注意 | 细铁丝框架设为不投影（`noCastShadowTree`），否则在地面投出放射状硬条纹 |

### 1.5 水壶 Kettle + 支架 KettleStand — 顶层块

| 项 | 内容 |
|---|---|
| 生成 | 顶层 `kettle` 组；`inner` 以原始雕刻单位建模后 `scale 0.14`、`rotation.y = π`（**又一处 Three.js 侧补救尺寸/朝向**） |
| Geometry | `LatheGeometry` ×4（壶身、壶肩、壶盖、盖钮）、`TorusGeometry` ×3（圈足、领口、烟熏带）、`TubeGeometry` ×2（壶嘴、提梁）、`CapsuleGeometry`（握把）、`CylinderGeometry` ×3、`BoxGeometry`；蒸汽 `SphereGeometry` ×7 |
| Material | `kettleMat`：铸铁 PBR（`assets/textures/iron/*` 1024 px albedo/roughness/normal/AO），emissive 受热发光；握把/嘴口纯色；烟熏带半透明 |
| 动画 | 放置/取回：`kettle.position` 在 `start ↔ KETTLE_REST(0.04, 0.59, 0.02)` 间插值 + 抛物线抬升；`kettleMat.emissiveIntensity` 随受热进度；蒸汽球逐帧重设位置/缩放/透明度 |
| Interaction | 「煮水」按钮；收拾时强制复位 |
| Position | **蒸汽发射点硬编码 `(0.38, 0.31, 0)`（壶嘴口，组局部）**；壶底 = 组原点；`KETTLE_REST.y` 与支架顶圈高度 0.575 配套 |
| 支架 | `kettleRig`：`TorusGeometry` 顶圈 + 4 条 `makeBeamBetween` 细腿，腿脚落在石圈内侧 r=0.8 |
| 直接换 GLB | **是**（Stage 4），同时替换支架 |
| 必须保留 | `KettleRoot`（原点=壶底中心）、`SteamAnchor`（替代硬编码蒸汽点）、`Body`（受热自发光材质所在网格）、`Handle`；支架 `KettleStandRoot` + `RestAnchor` |
| 注意 | 受热发光是对材质 `emissiveIntensity` 的修改——GLB 加载后需克隆壶身材质，避免影响其他实例 |

### 1.6 火把 Torch — `makeTorchModel()`

| 项 | 内容 |
|---|---|
| 生成 | `makeTorchModel()` 返回 `{ torch, torchFlame, torchGlow, torchLight, torchWrapMat }` |
| Geometry | `LatheGeometry` 木柄、`SphereGeometry` 柄尾、`CylinderGeometry` 缠布芯、自定义 `BufferGeometry` ×5 螺旋布条、`ShapeGeometry` ×2 结尾、`TorusGeometry` 焦黑口沿 |
| Material | 木柄（64 px 画布 map/roughness/bump/ao）、缠布芯（emissiveMap 余烬渐变，`emissiveIntensity` 代码驱动）、布条、护边、焦黑 |
| 动画 | 引燃：`torch.position` 在 `stand(1.58, 0.02, −0.82) ↔ ignite(0.96, 0.36, −0.22)` 插值，`rotation.z` 倾斜 1.16 rad |
| Interaction | 「点燃火把 / 熄灭」 |
| Position | **火焰粒子发射点与点光 = 局部 `(0, 1.292, 0)` 变换到世界**（硬编码）；辉光 Sprite 挂在 `torchFlameRig` |
| 直接换 GLB | 是（Stage 5） |
| 必须保留 | `TorchRoot`（原点=柄底，轴向 +Y）、`FlameAnchor`（替代 1.292 硬编码）、`Wrap`（余烬发光材质，名称 `TorchEmber`）、`Handle` |
| 注意 | 点光 `torchLight` 常驻场景根部（光源数量恒定），不要放进 GLB |

### 1.7 松果 Pinecone — `pineconeGeo` / `throwPinecone()`

| 项 | 内容 |
|---|---|
| Geometry | 1 个拉伸球核 + 46 个压扁 `SphereGeometry` 鳞片（黄金角排列）合并为共享几何（`userData.shared`） |
| Material | 每个松果独立 `MeshStandardMaterial`（燃烧时颜色渐黑、emissive 衰减） |
| 动画 | 抛物线 + 翻滚 → 落点 y=0.19 → 燃烧 7.5 s 并缩小 |
| Interaction | 「投掷松果」，最多 9 个 |
| 直接换 GLB | 是：只需一个网格，加载后共享几何、**逐个克隆材质** |
| 必须保留 | `PineconeRoot` 原点 = 几何中心（翻滚绕中心），高度 ≈ 0.24 m |

### 1.8 木柴 Logs

| 子项 | 生成 | 动画 / 逻辑 | 换 GLB |
|---|---|---|---|
| 篝火 teepee 8 根 | 篝火块：`makeLogGeometry()`（变形 Cylinder）树皮段 + 炭化段（`charMat` 龟裂 emissiveMap）+ 年轮端面 `CircleGeometry` | **坍塌**：每根组的四元数在 `baseQuat → flatQuat` 间 slerp、下沉；树皮颜色 `BARK_FRESH→BARK_CHAR` 随燃尽插值；炭化段 emissive 闪烁 | 可以，但每根须保持"原点在外端、轴向 +Y、长度 ≈0.65 m"，炭化段为独立子网格 `CharEnd`（共享 `Charcoal` 发光材质） |
| 加柴飞入 | `tossLog()`：`makeLogGeometry` + 新材质 | 抛物线、翻滚、落地姿态随机；最多 5 根，旧的被 dispose | 可以：原点=中心、长轴 +Y；材质共享即可 |
| 柴垛 | `makeWoodPile()`：7 根短柴 + 14 个年轮面 | 无 | 可以（`WoodPileRoot`） |
| 待劈原木 / 半柴 / 木屑 | `chopLog`（Cylinder+Circle）、`makeChopHalf()`（半圆柱壳+劈面）、`chopChipGeo`（Box） | 下落、劈开、弹跳、静置（最多 8 块半柴） | 可以：需要 `ChopLog`、`ChopHalf`（劈面朝 +Z）两个模型 |

### 1.9 劈柴桩 + 斧头 — `makeStump()`

| 项 | 内容 |
|---|---|
| 摆放 | `placeProp(chopRig, −0.95, 2.45, true, 'stump')` |
| Geometry | 桩：`makeLogGeometry` + 顶面年轮 `CircleGeometry`；斧：`CylinderGeometry` 柄 + `BoxGeometry` 斧头 + `BoxGeometry` 刃 |
| 动画 | 斧头组 `chopRig.userData.axe` 在 `CHOP_POSE.idle / raised / impact` 三个关键帧之间插值位置和欧拉角 |
| Position | **桩顶 y = 0.342**（原木落点、劈开高度）；斧头关键帧以斧头组原点（斧头中心）为枢轴，坐标在桩的局部空间 |
| 必须保留 | `ChopStumpRoot`、`TopAnchor`（桩顶中心）、`Axe`（独立子节点；原点 = 斧头与柄交接处，柄沿 +Y，刃口朝 +Z）；替换斧头若改变枢轴，需要重调 `CHOP_POSE` |

### 1.10 搪瓷杯 Mug — `makeMug()`

`CylinderGeometry` 杯身 + `TorusGeometry` 杯沿/把手；`Enamel` + `EnamelRim` 两个纯色材质。无动画、无依赖，**可直接换 GLB**（`MugRoot`）。

### 1.11 棉花糖 + 竹签 — 顶层块 `skewer`

竹签是单位高度 `CylinderGeometry`，由 `aimRod()` 按"手→签尖"两点**定向并沿 Y 缩放**；棉花糖是 `LatheGeometry`，绕 Y 自转，材质颜色随烤制进度 `0xfff2d8 → 0xa94d18`，生日模式改彩虹色。
竹签的"按长度缩放"不适合 GLB（会拉伸纹理），**建议保留程序化竹签**，棉花糖可在 Stage 5 之后换 GLB（需暴露材质 `Marshmallow`）。

---

## 2. 与互动/渲染耦合的全局约束（替换时不能破坏）

1. **光源数量恒定**：`TentGlow`、`LanternLight`、`torchLight` 都常驻场景根部，只改强度/位置。GLB 里**不要**放灯光（KHR_lights_punctual），由代码按锚点创建。
2. **材质逐帧驱动**：`LanternGlow`（闪烁、生日换色）、`kettleMat.emissiveIntensity`（受热）、`torchWrapMat.emissiveIntensity`（余烬）、`charMat`（炭化段）、`barkMat.color`（炭化）、松果/棉花糖材质颜色。适配层需按名称拿到这些材质，必要时克隆。
3. **硬编码坐标**：蒸汽口 `(0.38, 0.31, 0)`、火把头 `1.292`、桩顶 `0.342`、`KETTLE_REST`、`CHOP_POSE`、提灯 `lanternLightSocket`。换 GLB 时改由锚点提供。
4. **Three.js 侧尺寸补救**：提灯 `scale 0.58`、水壶 `scale 0.14 + rotation π`。新标准要求在 Blender 内做对尺寸和朝向。
5. **阴影**：`applyPropShadows()` 统一开关；细杆、玻璃、缝线不投影，避免低分辨率点光阴影出现硬条纹。
6. **收拾物品**：只改 `visible`，GLB 实例必须挂在原来的道具组（或替换为同一引用）下。
7. **导出/覆盖（v1 功能）**：`PROP_GROUPS[key]`、`EXPORT_TARGETS`、`assets/models/procedural/models.json` 依赖道具组存在。

---

## 3. 保留程序化的对象（不替换）

| 对象 | 理由 |
|---|---|
| 火焰 / 火星 / 烟 / 雨 / 萤火虫 / 飞蛾 / 流星 | 粒子系统，本质是模拟 |
| 星空、月亮、月晕、云、天穹 | 着色器效果，随月相/云量实时变化 |
| 地形、湖面、海面、泡沫、碎光 | 大尺度程序地形，树木/散布物的落地依赖 `groundHeight()` / `beachHeight()` |
| 远山、海岸丘陵、礁岛、林带剪影 | 远景，按项目规则用程序几何 |
| 针叶树、背景林、棕榈 | 植被（v1 已重建，含实例化背景林）；可选的 Blender 覆盖仍保留 |
| 石圈石块、碎石、枯枝、贝壳、礁石、漂流木 | 石头/小树枝属于"程序几何适用"类别；石圈已用实拍 PBR 贴图 |
| 炭床 46 块炭 | 每块独立脉动发光，程序化最便宜 |
| 棉花糖竹签 | 靠两点瞄准+缩放实现，GLB 反而更复杂 |

---

## 4. 替换优先级结论

| 阶段 | 模型 | 原因 | 进度 |
|---|---|---|---|
| Stage 1 | **Tent** | 最大、最靠前、最粗糙（828 三角形、纯色、无纹理） | ✔ `tent.glb`（25.7 k 三角形） |
| Stage 2 | Backpack + Chair | 营地生活感；无逻辑依赖，风险最低 | ✔ `backpack.glb`（14.7 k）、`chair.glb`（6.2 k） |
| Stage 3 | Lantern | 验证金属/玻璃/局部光；需要 `LightAnchor` 和发光材质契约 | ✔ `lantern.glb`（10.8 k），去掉 `scale 0.58` |
| Stage 4 | Kettle + KettleStand | 验证 GLB 与放置动画、受热发光、蒸汽锚点结合 | ✔ `kettle.glb`（8.5 k），去掉 `scale 0.14 + rotation.y π` |
| Stage 5 | Torch / Pinecone / Logs / Axe / Stump / WoodPile / Mug | 互动小物件，锚点多但单个简单 | 5a ✔ `torch.glb`（3.1 k）、`pinecone.glb`（1.8 k）、`firewood.glb`（3 段）；5b 斧头 / 劈柴桩 / 柴垛 / 杯子待做 |

已替换的模型仍保留 `makeTent()` / `makeBackpack()` / `makeChair()` / `makeLantern()` / 程序化水壶与支架 / `makeTorchModel()` / 程序化松果与木柴 作为 GLB 缺失时的回退，实测数据见 `asset-pipeline.md` §7。
