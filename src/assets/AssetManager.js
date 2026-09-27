/**
 * Campfire · AssetManager
 * ------------------------------------------------------------------
 * 统一的 GLB 资产加载层（three/addons GLTFLoader）：
 *   loadGLTF(url)  按 URL 缓存的原始加载（也供 v1 的"程序模型覆盖"复用）
 *   load(key)      加载 + 契约校验 + 加载后处理，缓存模板
 *   create(key)    克隆模板（几何/贴图共享），返回 { key, root, anchors, parts, materials }
 *   preload(keys)  场景构建前发起下载，与其余初始化并行
 *
 * 模型契约见 ModelRegistry.js；资产标准见 docs/asset-pipeline.md。
 * 加载失败（文件缺失、契约节点缺失）一律抛错，由调用方回退到程序化模型。
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MODEL_REGISTRY, findNode, resolveContract } from './ModelRegistry.js';

export class AssetManager {
  constructor({ renderer = null, registry = MODEL_REGISTRY, baseUrl = '' } = {}) {
    this.renderer = renderer;
    this.registry = registry;
    this.baseUrl = baseUrl;
    this.loader = new GLTFLoader();
    this._gltf = new Map();       // url → Promise<gltf>
    this._templates = new Map();  // key → Promise<template>
    this._maxAniso = renderer ? Math.min(8, renderer.capabilities.getMaxAnisotropy()) : 1;
  }

  /** 该模型是否已有正式资产（registry.ready） */
  has(key) {
    return !!this.registry[key]?.ready;
  }

  loadGLTF(url) {
    const full = this.baseUrl + url;
    if (!this._gltf.has(full)) this._gltf.set(full, this.loader.loadAsync(full));
    return this._gltf.get(full);
  }

  load(key) {
    if (!this._templates.has(key)) this._templates.set(key, this._loadTemplate(key));
    return this._templates.get(key);
  }

  async _loadTemplate(key) {
    const def = this.registry[key];
    if (!def) throw new Error(`[assets] unknown model "${key}"`);
    if (!def.ready) throw new Error(`[assets] "${key}" has no production asset yet (stage ${def.stage})`);
    const gltf = await this.loadGLTF(def.url);
    const root = def.root ? findNode(gltf.scene, def.root) : gltf.scene;
    if (!root) throw new Error(`[assets] ${def.url}: root node "${def.root}" not found`);
    const check = resolveContract(root, def);
    if (check.missing.length) throw new Error(`[assets] ${def.url}: missing ${check.missing.join(', ')}`);
    if (check.optionalMissing.length) console.warn(`[assets] ${key}: optional nodes missing: ${check.optionalMissing.join(', ')}`);
    root.removeFromParent();
    root.position.set(0, 0, 0);          // 摆放由场景决定；模型只描述自身（见坐标标准）
    root.quaternion.identity();
    this._prepareTemplate(root);
    return { key, def, root };
  }

  // 模板级处理（所有实例共享）：贴图过滤、默认阴影策略
  _prepareTemplate(root) {
    root.traverse(o => {
      if (!o.isMesh) return;
      // glTF extras → userData：Blender 中给对象加自定义属性 noCastShadow 即可关闭投影
      o.castShadow = !o.userData.noCastShadow;
      o.receiveShadow = true;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        for (const k of ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap']) {
          if (m[k]) m[k].anisotropy = this._maxAniso;
        }
      }
    });
  }

  preload(keys) {
    return Promise.all(keys.filter(k => this.has(k)).map(k => this.load(k).catch(e => {
      console.warn(e.message || e);
      return null;
    })));
  }

  /** 实例化：克隆节点树（共享几何与贴图），按契约返回锚点/部件/材质 */
  async create(key) {
    const tpl = await this.load(key);
    const root = tpl.root.clone(true);
    const def = tpl.def;
    const per = def.perInstanceMaterials || [];
    if (per.length) {
      // 需要逐实例驱动的材质（受热发光、燃烧变色）克隆一份，避免实例互相影响
      const names = per.includes('*') ? null : new Set(per.map(k => (def.materials?.[k] || '').replace('?', '')));
      const cloned = new Map();
      root.traverse(o => {
        if (!o.isMesh) return;
        const m = o.material;
        if (names && !names.has(m.name)) return;
        if (!cloned.has(m)) cloned.set(m, m.clone());
        o.material = cloned.get(m);
      });
    }
    const { anchors, parts, materials } = resolveContract(root, def);
    const model = { key, root, anchors, parts, materials, def };
    if (def.prepare) def.prepare(model, THREE);
    return model;
  }
}

// —— 模型适配入口：场景代码按物品调用，不关心节点名 ——
export const createTentInstance = assets => assets.create('tent');
export const createBackpackInstance = assets => assets.create('backpack');
export const createChairInstance = assets => assets.create('chair');
export const createLanternInstance = assets => assets.create('lantern');
export const createKettleInstance = assets => assets.create('kettle');
export const createKettleStandInstance = assets => assets.create('kettle-stand');
export const createTorchInstance = assets => assets.create('torch');
