/**
 * Campfire · ModelRegistry
 * ------------------------------------------------------------------
 * 每个 Blender 资产的"模型契约"：文件位置、根节点名、锚点（anchors）、部件（parts）、
 * 需要代码驱动的材质（materials）与加载后处理（prepare）。
 *
 * 场景代码只通过 AssetManager.create(key) 拿到 { root, anchors, parts, materials }，
 * 不直接写节点名——节点名查找只发生在本文件的 resolveContract() 里。
 *
 * 名称后缀 '?' 表示可选；缺少必需节点时 AssetManager 抛错，调用方回退到程序化模型。
 * 坐标/尺寸/材质标准见 docs/asset-pipeline.md，逐模型的锚点来源见 docs/model-audit.md。
 */

export const MODEL_REGISTRY = {
  // Stage 1 —— 帐篷（tools/blender/build_tent.py → assets/models/tent.glb）
  tent: {
    ready: true,
    stage: 1,
    url: 'assets/models/tent.glb',
    root: 'TentRoot',
    anchors: {
      interiorLight: 'InteriorLightAnchor'      // 帐内暖光 PointLight 的位置（v1: 局部 (0, 0.5, 0.675)）
    },
    parts: {
      door: 'Door',                             // 卷起的门帘 + 系带（将来可做开合）
      fly: 'Fly?',
      inner: 'InnerTent?',
      guyLines: 'GuyLines?'
    },
    materials: {
      canvas: 'TentCanvas?',
      lampGlow: 'LampGlow?'
    }
  },

  // Stage 2 —— 登山包 / 折叠椅（tools/blender/build_backpack.py、build_chair.py）
  // 业务逻辑不依赖内部网格，锚点均为可选（为将来"开盖 / 提起 / 坐下"预留）
  backpack: {
    ready: true, stage: 2, url: 'assets/models/backpack.glb',
    root: 'BackpackRoot',
    anchors: { handleL: 'HandleSocketL?', handleR: 'HandleSocketR?' },
    parts: { lid: 'LidPivot?' }
  },
  chair: {
    ready: true, stage: 2, url: 'assets/models/chair.glb',
    root: 'ChairRoot',
    anchors: { seat: 'SeatAnchor?' }
  },

  // Stage 3 —— 煤油提灯（tools/blender/build_lantern.py）
  lantern: {
    ready: true, stage: 3, url: 'assets/models/lantern.glb',
    root: 'LanternRoot',
    anchors: { light: 'LightAnchor' },          // campLight + 飞蛾环绕中心（火苗中心）
    parts: { glass: 'Glass', flame: 'Flame', bail: 'BailPivot?' },
    materials: { flame: 'LanternGlow' },        // 闪烁 / 生日换色
    prepare(model, THREE) {
      // 灯体近场：campLight 就在火苗中心，油壶肩部 / 侧管内侧 / 护丝离它只有 3~10 cm，按点光源 1/d² 会被打成白色。
      // 真实火苗是几厘米的面光源，且大部分被燃烧器挡住——这里只对提灯自身材质把衰减距离下限设为 50 cm（three 默认 10 cm），
      // 否则灯体（蓝漆×橙光≈中性灰）被推到饱和白。其他物体与地面光斑完全不受影响
      const nearField = new Set();
      model.root.traverse(o => {
        if (o.isMesh && o !== model.parts.flame) nearField.add(o.material);
      });
      for (const m of nearField) softNearField(m, THREE, 0.25);
      // 玻璃：加载后替换为 MeshPhysicalMaterial（只渲染外表面，避免被罩内灯光打爆）
      model.parts.glass.traverse(o => {
        if (!o.isMesh) return;
        o.material = new THREE.MeshPhysicalMaterial({
          name: 'LanternGlass', color: 0xffe2ae, transparent: true, opacity: 0.2,
          roughness: 0.06, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.05,
          depthWrite: false, side: THREE.FrontSide
        });
        o.userData.noCastShadow = true;
        o.renderOrder = 2;
      });
    }
  },

  // Stage 4 —— 铸铁水壶 + 锻铁支架（tools/blender/build_kettle.py，同一个 GLB 的两个根节点）
  kettle: {
    ready: true, stage: 4, url: 'assets/models/kettle.glb',
    root: 'KettleRoot',                         // 原点 = 壶底圈足中心，壶嘴朝 +X
    anchors: { steam: 'SteamAnchor' },          // 替代硬编码的蒸汽口 (0.38, 0.31, 0)
    parts: { body: 'Body', handle: 'Handle', lid: 'Lid?', spout: 'Spout?' },
    materials: { body: 'KettleIron' },
    perInstanceMaterials: ['body'],             // 受热自发光逐实例驱动
    prepare(model) {
      // 受热发光色（暗橙红）；强度由「煮水」进度驱动，初始为 0
      model.materials.body.emissive.setHex(0x4a1804);
      model.materials.body.emissiveIntensity = 0;
    }
  },
  'kettle-stand': {
    ready: true, stage: 4, url: 'assets/models/kettle.glb',
    root: 'KettleStandRoot', anchors: { rest: 'RestAnchor' }   // RestAnchor = 顶圈上沿（壶底落点）
  },

  // —— 以下为后续阶段的契约（ready: false：尚无正式资产，场景继续使用程序化模型）——
  // Stage 5 —— 火把 / 松果 / 木柴（tools/blender/build_torch.py、build_pinecone.py、build_firewood.py）
  torch: {
    ready: true, stage: 5, url: 'assets/models/torch.glb',
    root: 'TorchRoot',                                        // 原点 = 柄底，轴向 +Y
    anchors: { flame: 'FlameAnchor', grip: 'GripAnchor?' },   // 替代硬编码的火把头 y=1.292
    parts: { handle: 'Handle', wrap: 'Wrap' },
    materials: { ember: 'TorchEmber' },                       // 余烬贴图的强度由引燃进度驱动
    prepare(model) {
      model.materials.ember.emissiveIntensity = 0;            // 未点燃
    }
  },
  pinecone: {
    ready: true, stage: 5, url: 'assets/models/pinecone.glb',
    root: 'PineconeRoot',                                     // 原点 = 几何中心（飞行中绕它翻滚）
    parts: { cone: 'Cone' },
    materials: { body: 'Pinecone' },
    perInstanceMaterials: ['*'],                              // 逐个燃烧变色
    prepare(model) {
      model.materials.body.emissive.setHex(0xff4a0a);         // 燃烧余光色；强度由燃烧进度驱动
      model.materials.body.emissiveIntensity = 0;
    }
  },
  // 三段不同长短粗细的木柴（同一 GLB 的三个根节点）：原点 = 外端截面中心，轴向 +Y；
  // Bark 材质（颜色随燃尽变黑）与 Charcoal 材质（龟裂余烬发光）由火堆逻辑全局驱动，三段共享
  ...Object.fromEntries([[1, 0.66], [2, 0.70], [3, 0.74]].map(([i, length]) => [`log-${i}`, {
    ready: true, stage: 5, url: 'assets/models/firewood.glb', length,
    root: `Log${i}Root`,
    parts: { bark: 'Bark', charEnd: 'CharEnd' },
    materials: { bark: 'Bark', char: 'Charcoal' }
  }])),
  axe: {
    ready: false, stage: 5, url: 'assets/models/props/axe.glb',
    root: 'AxeRoot', anchors: { blade: 'BladeEdge', grip: 'GripAnchor?' }
  },
  stump: {
    ready: false, stage: 5, url: 'assets/models/props/stump.glb',
    root: 'StumpRoot', anchors: { top: 'TopAnchor', axeSocket: 'AxeSocket' }
  }
};

/**
 * 点光源近场软化：把 three 的距离衰减 1 / max(d², 0.01) 的下限改为 minSq（d² 下限）。
 * 只用于"光源装在自己体内"的道具（提灯）；不改 ShaderChunk 全局，只改该材质的程序。
 */
function softNearField(material, THREE, minSq) {
  if (!material || material.userData.nearField) return;
  const chunk = THREE.ShaderChunk.lights_pars_begin;
  const needle = 'max( pow( lightDistance, decayExponent ), 0.01 )';
  if (!chunk.includes(needle)) return;                     // three 版本改动时静默退回默认衰减
  const patched = chunk.replace(needle, `max( pow( lightDistance, decayExponent ), ${minSq.toFixed(4)} )`);
  material.userData.nearField = minSq;
  material.onBeforeCompile = shader => {
    shader.fragmentShader = shader.fragmentShader.replace('#include <lights_pars_begin>', patched);
  };
  material.customProgramCacheKey = () => `nearField:${minSq}`;
}

// GLTFLoader 会清洗节点名：空格→'_'，去掉 '.:/[]'（Blender 的 "Door.001" 变成 "Door001"）
const sanitize = name => name.replace(/\s/g, '_').replace(/[[\].:/]/g, '');

function parseSpec(spec) {
  const optional = spec.endsWith('?');
  return { name: optional ? spec.slice(0, -1) : spec, optional };
}

/** 在子树中按契约名查找节点：精确匹配 → 允许 Blender 重复名的数字后缀 */
export function findNode(root, name) {
  const clean = sanitize(name);
  const exact = root.getObjectByName(clean);
  if (exact) return exact;
  const re = new RegExp(`^${clean}_?\\d+$`);
  let hit = null;
  root.traverse(o => { if (!hit && re.test(o.name)) hit = o; });
  return hit;
}

/** 在子树中按材质名查找材质（同名材质在 GLB 中已合并为同一对象） */
export function findMaterial(root, name) {
  let hit = null;
  root.traverse(o => {
    if (hit || !o.isMesh) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (m && m.name === name) { hit = m; break; }
    }
  });
  return hit;
}

/**
 * 按契约解析一个模型根节点 → { anchors, parts, materials, missing }
 * missing：缺失的必需项（非空时调用方应视为加载失败）
 */
export function resolveContract(root, def) {
  const out = { anchors: {}, parts: {}, materials: {}, missing: [], optionalMissing: [] };
  for (const group of ['anchors', 'parts']) {
    for (const [key, spec] of Object.entries(def[group] || {})) {
      const { name, optional } = parseSpec(spec);
      const node = findNode(root, name);
      if (node) out[group][key] = node;
      else (optional ? out.optionalMissing : out.missing).push(name);
    }
  }
  for (const [key, spec] of Object.entries(def.materials || {})) {
    const { name, optional } = parseSpec(spec);
    const mat = findMaterial(root, name);
    if (mat) out.materials[key] = mat;
    else (optional ? out.optionalMissing : out.missing).push(`material:${name}`);
  }
  return out;
}
