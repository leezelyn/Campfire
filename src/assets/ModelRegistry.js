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

  // —— 以下为后续阶段的契约（ready: false：尚无正式资产，场景继续使用程序化模型）——
  lantern: {
    ready: false, stage: 3, url: 'assets/models/lantern.glb',
    root: 'LanternRoot',
    anchors: { light: 'LightAnchor' },          // campLight + 飞蛾环绕中心
    parts: { glass: 'Glass', flame: 'Flame', bail: 'BailPivot?' },
    materials: { flame: 'LanternGlow' },        // 闪烁 / 生日换色
    prepare(model, THREE) {
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
  kettle: {
    ready: false, stage: 4, url: 'assets/models/kettle.glb',
    root: 'KettleRoot',
    anchors: { steam: 'SteamAnchor' },          // 替代硬编码的蒸汽口 (0.38, 0.31, 0)
    parts: { body: 'Body', handle: 'Handle', lid: 'Lid?' },
    materials: { body: 'KettleIron' },
    perInstanceMaterials: ['body']              // 受热自发光逐实例驱动
  },
  'kettle-stand': {
    ready: false, stage: 4, url: 'assets/models/kettle.glb',
    root: 'KettleStandRoot', anchors: { rest: 'RestAnchor' }
  },
  torch: {
    ready: false, stage: 5, url: 'assets/models/torch.glb',
    root: 'TorchRoot',
    anchors: { flame: 'FlameAnchor', grip: 'GripAnchor?' },   // 替代硬编码的火把头 y=1.292
    parts: { handle: 'Handle', wrap: 'Wrap' },
    materials: { ember: 'TorchEmber' }
  },
  pinecone: {
    ready: false, stage: 5, url: 'assets/models/pinecone.glb',
    root: 'PineconeRoot', perInstanceMaterials: ['*']          // 逐个燃烧变色
  },
  log: {
    ready: false, stage: 5, url: 'assets/models/props/log.glb',
    root: 'LogRoot', parts: { charEnd: 'CharEnd?' }
  },
  axe: {
    ready: false, stage: 5, url: 'assets/models/props/axe.glb',
    root: 'AxeRoot', anchors: { blade: 'BladeEdge', grip: 'GripAnchor?' }
  },
  stump: {
    ready: false, stage: 5, url: 'assets/models/props/stump.glb',
    root: 'StumpRoot', anchors: { top: 'TopAnchor', axeSocket: 'AxeSocket' }
  }
};

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
