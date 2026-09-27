# Campfire

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.ja.md">日本語</a>
</p>

A self-contained interactive night campfire scene built with Three.js.  
The project runs from a single `index.html` file, with Three.js loaded from a CDN. No build step or dependency installation is required.

---

## Overview

**Campfire** is an interactive browser-based campfire demo. It combines particle-based flames, sparks, smoke, moonlight, fog, simple weather controls, and procedural Web Audio to create a quiet nighttime camping atmosphere.

It is suitable for learning and experimenting with:

- Three.js scene construction
- Particle-based flame, spark, and smoke effects
- Procedural Web Audio synthesis
- 3D positional sound and distance attenuation
- Simple physical simulation
- Real-time parameter control
- Multilingual UI interaction

---

## Features

### Night Campfire Scene

The scene contains flames, logs, sparks, smoke, moonlight, fog, cloud cover, light rain, and a dark outdoor environment.

The natural environment is fully procedural:

- **Conifers**: spruce (drooping whorled tiers with pointed branch tips) and pine (tall trunk with a clumped crown); trunks run through the crown with root flare and a bark texture, plus an instanced mid-distance backdrop forest
- **Mountains**: a full ring of ridged-multifractal ranges that joins the ground seamlessly, colored by altitude and slope (forest belt, rock, snow); kept low toward the moon/lake so the moon stays visible
- **Terrain**: gradient-noise fBm relief; the camp and lake stay flat and the forest floor rises toward the foothills
- **Beach**: coastal hills that slope into the sea as headlands, rocky islets, and pinnate-frond palms

### Real-time Parameter Panel

The upper-right parameter panel provides real-time sliders for:

- Flame intensity
- Thermal buoyancy
- Spark emission rate
- Smoke amount
- Wind speed
- Master volume
- Crackle frequency
- Distance attenuation
- High-frequency air absorption
- Rain intensity
- Cloud amount
- Moon phase
- Moonlight intensity
- Fog density
- Exposure

All parameters take effect immediately.

### Add Wood Interaction

Clicking **Add Wood** throws a log into the campfire. The interaction includes:

- Parabolic motion
- Rolling animation
- Spark burst
- Smoke puff
- 3D positional impact sound
- Fuel increase
- Stronger flame
- Temporarily increased crackling sounds

Fuel gradually burns down over time, and the fire slowly returns to its original state.

### Campfire Interactions

Four campfire interactions can run independently:

- **Roast Marshmallow**: a marshmallow is held over the fire and gradually caramelizes.
- **Boil Water**: a kettle is suspended above the flame and produces steam when heated.
- **Light Torch**: a torch is lit by the fire and can be extinguished by clicking again.
- **Throw Pinecone**: a pinecone lands in the fire, producing sparks and adding a small amount of fuel.

### Trilingual UI

The interface supports instant switching between:

- Chinese
- English
- Japanese

Buttons, status messages, and progress feedback update with the selected language.

### Procedural Audio

All sounds are generated in real time using the Web Audio API. No external audio files are required.

Generated sounds include:

- Low-frequency fire rumble
- Wood crackling
- Occasional loud pops
- Log impact sound
- Distance-based attenuation
- Air absorption that makes distant fire sounds softer and darker

---

## How to Run

Because this project uses ES Modules, open it through a local HTTP server.

```bash
python -m http.server 8341
```

Then visit:

```text
http://localhost:8341
```

After entering the page, click anywhere to enable audio. Most browsers require a user gesture before Web Audio can start.

---

## Controls

| Action | Description |
|---|---|
| Drag mouse | Rotate camera |
| Mouse wheel | Zoom in or out |
| Click page | Start audio |
| Click “Add Wood” | Add a log to the campfire |
| Click interaction buttons | Roast marshmallow, boil water, light torch, or throw pinecone |
| Adjust parameter panel | Change fire, audio, weather, and environment effects in real time |

---

## Physical and Visual Simulation

| Effect | Implementation |
|---|---|
| Distance-based sound attenuation | `PositionalAudio` with an inverse distance model |
| Binaural positioning | HRTF spatial audio |
| Air absorption | High frequencies decrease with distance |
| Light falloff | Point light with inverse-square decay |
| Flame motion | Thermal buoyancy, drag, turbulence, and inward force |
| Flame layers | Blue base, bright yellow-white core, and orange-red outer flame |
| Spark movement | Gravity, drag, and thermal plume lift |
| Smoke diffusion | Upward movement, expansion, wind drift, and fade-out |
| Crackling sound | Randomly scheduled short burst sounds |
| Fire rumble | Low-frequency noise linked to flame intensity |

---

## 3D Asset Pipeline (2.0)

Real-world camp props are being upgraded from "procedurally assembled Three.js primitives" to **Blender-authored `.glb` production assets**:

- Audit: [`docs/model-audit.md`](docs/model-audit.md) — generator, geometry, materials, animation/interaction dependencies and required anchors for every prop
- Art direction: [`docs/art-direction.md`](docs/art-direction.md) — a quiet, warm, lived-in, slightly weathered realistic night camp; cold moonlight + warm fire
- Pipeline spec: [`docs/asset-pipeline.md`](docs/asset-pipeline.md) — coordinate standard, model contracts, PBR, performance budget, staged plan
- Runtime: `src/assets/AssetManager.js` (GLTFLoader loading/caching/instancing) + `src/assets/ModelRegistry.js` (node contracts)
- Sources: `tools/blender/*.py` (reproducible Blender build scripts) → `assets/source/*/*.blend` → `assets/models/*.glb`

| Stage | Models | Status |
|---|---|---|
| Stage 1 | Tent | ✔ `assets/models/tent.glb` (canvas weave, seams, tension folds, door roll, guy lines, lived-in interior; ~26k triangles, 1.3 MB) |
| Stage 2 | Backpack, chair | planned |
| Stage 3 | Lantern | planned |
| Stage 4 | Kettle + stand | planned |
| Stage 5 | Torch, pinecone, logs, axe, stump… | planned |

Rebuild the tent (Blender 4.x, or `pip install bpy`):

```bash
blender --background --python tools/blender/build_tent.py      # writes assets/models/tent.glb and assets/source/tent/tent.blend
```

You can also open `assets/source/tent/tent.blend`, edit it and export over `assets/models/tent.glb` with the settings in `docs/asset-pipeline.md` §6.
If a production asset fails to load (e.g. missing file), the page falls back to the original procedural model.

---

## Blender Interop (procedural models)

Models can be exported as **glTF 2.0 (.glb)**, opened and tweaked in Blender, and then loaded back into the page in place of the procedural models.

### 1. Export

At the bottom of the parameter panel, **"Blender models"**: pick a target → click **Export .glb** to download `<name>.glb`.

| Target | Contents | Can be loaded back |
|---|---|---|
| Whole scene (current) | Current forest/beach environment + camp + fire + lights + camera | — |
| Terrain | Ground mesh of the current scene | — |
| Mountains (forest) / Coast hills & islets | Distant ranges + treeline silhouettes | ✓ |
| Spruce / Pine / Palm | One tree template (root at origin, ~7–9 m tall) | ✓ replaces every tree of that species |
| Tent | The in-scene tent (already a production GLB) | — (edit `assets/source/tent/tent.blend`) |
| Chair / Backpack / Lantern / Woodpile / Stump & axe / Mug | A single prop (exported around its own origin) | ✓ |
| Fire pit | Stones, logs, embers | — (the logs have a collapse animation) |

`assets/models/procedural/` already contains `.glb` files for the 11 overridable models, ready to open in Blender.

### 2. Open in Blender

`File ▸ Import ▸ glTF 2.0 (.glb/.gltf)`. Units are meters, Y-up is converted to Blender's Z-up, and materials become Principled BSDF. The export is prepared for Blender:

- Runtime effects (flame particles, stars, moon, glints) are skipped
- Instanced objects (backdrop forest, pebbles…) become **linked duplicates** — edit one, all update
- Bump maps are converted to normal maps; normal-map green channels follow the glTF convention
- Trees and mountains use **vertex colors** for shading depth (a Color Attribute node in the material)
- Objects and materials have readable names (e.g. `Tree_spruce_03 › Spruce › Foliage`, `TentFabric`)

### 3. Load your edits back

1. In Blender, `File ▸ Export ▸ glTF 2.0`, format **glTF Binary (.glb)**, saved under the **same name** in `assets/models/procedural/` (e.g. `chair.glb`)
2. Edit `assets/models/procedural/models.json` and set that entry to `true` (or a file name, e.g. `"chair": "chair_v2.glb"`)
3. Reload the page (served over HTTP). The browser console prints `[models] chair ← assets/models/procedural/chair.glb`

Notes:

- **Keep the root at the origin**: placement and orientation are decided by the page; the file only describes the model
- Lantern: the light anchor is an empty named `lanternLightSocket`, and the flame material is `LanternGlow` (used by the flicker)
- Stump: the axe object is named `Axe` (used by the chopping animation); if removed, the procedural axe is kept
- Enable `Include ▸ Custom Properties` when exporting to keep shadow flags such as `noCastShadow`
- Light units differ from Blender's; if an imported full scene looks too dark or bright, adjust `Lighting Mode` in the import options

---

## Project Structure

```text
Campfire/
├── index.html
├── README.md
├── README.zh-CN.md
├── README.ja.md
├── docs/                # model audit, art direction, asset pipeline spec
├── src/assets/          # AssetManager.js, ModelRegistry.js
├── tools/blender/       # Blender asset build scripts (bpy)
├── assets/
│   ├── textures/
│   ├── models/          # production .glb assets (tent.glb …)
│   │   └── procedural/  # procedural-model exports + models.json (override switches)
│   └── source/          # asset source files (.blend)
├── scripts/
└── .claude/
```

---

## Notes

- This project is designed as a lightweight browser-based demo.
- No build step is required.
- Audio starts only after a user gesture because of browser autoplay policies.
- For the best experience, use a modern desktop browser.

---

## License

No license has been specified yet. If you plan to share or reuse this project publicly, consider adding a license such as MIT.
