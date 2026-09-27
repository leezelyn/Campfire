"""
Campfire · Enamel camp mug (Blender 4.x, bpy) — Stage 5b

    blender --background --python tools/blender/build_mug.py [-- --preview]
    python tools/blender/build_mug.py [--preview]              # pip "bpy" module

Outputs  assets/models/mug.glb · assets/source/mug/mug.blend (+ preview.png)
Contract MugRoot (origin = centre of the base, handle toward +X) · part Mug
         (see src/assets/ModelRegistry.js)

A well-used enamel mug (Ø 8 cm × 8.8 cm): white enamel with a navy rolled rim and foot, real wall
thickness (outer wall → rolled rim → inner wall → floor), a welded tube handle with flared feet,
chipped enamel showing black steel at the rim / foot / handle, and three-quarters of a cup of coffee.
One baked atlas (UV1): colour / ORM (steel where chipped).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402  (imports bpy first)
import bpy                       # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'mug.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'mug')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv

WHITE = '#e6e3da'
NAVY = '#1f3148'
SEG = 36

C.reset()
root = C.empty('MugRoot', size=0.05)


def tag(ob, hexcol, rough):
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    ob['cf_metal'] = 0.0
    return ob


parts = [
    tag(C.lathe('Foot', [(0.0, 0.0025), (0.033, 0.0025), (0.0365, 0.0), (0.0392, 0.0022), (0.0402, 0.0075)], SEG), NAVY, 0.3),
    tag(C.lathe('Wall', [(0.0402, 0.0075), (0.0408, 0.03), (0.0417, 0.06), (0.0424, 0.080)], SEG), WHITE, 0.28),
    tag(C.lathe('Rim', [(0.0424, 0.080), (0.0433, 0.0845), (0.0448, 0.0868), (0.0444, 0.0888),
                        (0.0428, 0.0891), (0.0413, 0.0870), (0.0409, 0.0835)], SEG), NAVY, 0.3),
    tag(C.lathe('Inner', [(0.0409, 0.0835), (0.0402, 0.06), (0.0392, 0.02), (0.0375, 0.0065), (0.034, 0.0048),
                          (0.0, 0.0048)], SEG), WHITE, 0.3),
]
# welded tube handle (+X), flattened feet where it meets the wall
hp = C.catmull([(0.041, 0, 0.071), (0.056, 0, 0.074), (0.068, 0, 0.066), (0.071, 0, 0.047),
                (0.066, 0, 0.028), (0.054, 0, 0.020), (0.0405, 0, 0.022)], 5)
parts.append(tag(C.curve_tube('Handle', hp, 0.0042, sides=8), WHITE, 0.3))
for z in (0.0715, 0.0215):
    parts.append(tag(C.rounded_box(f'Weld{z:g}', (0.012, 0.014, 0.003), (0.0425, 0, z), normal=(1, 0, 0),
                                   tangent=(0, 0, 1), p=2.6, res=2), WHITE, 0.3))

for o in parts:
    o.parent = root
C.unwrap_uv1(parts, uv0_tile=0.05)
base_p, orm_p = C.bake_weathering(parts, 'mug', TEX, size=512, dirt_height=0.012, fade=0.0, edge_wear=0.1,
                                  ao_distance=0.015, seed=71.0, metal=True, chips=0.9, chip_color='#1b1b1c',
                                  stains=0.25)
M_ENAMEL = C.baked_material('Enamel', base_p, orm_p, None)
M_COFFEE = C.pbr('Coffee', C.srgb('#1b0f08'), 0.08)
for o in parts:
    C.set_material(o, M_ENAMEL)
mug = C.join(parts, 'Mug')
coffee = C.lathe('Coffee', [(0.0, 0.064), (0.0401, 0.064)], SEG, parent=root)
for p_ in coffee.data.polygons:                      # pole-first profile faces down: flip to face up
    p_.flip()
C.set_material(coffee, M_COFFEE)
coffee['noCastShadow'] = True

print(f'[mug] triangles: {C.triangle_count()}')
print(f'[mug] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[mug] saved .blend ({C.save_blend(os.path.join(SRC, "mug.blend")) / 1024:.0f} KB)')
if PREVIEW:
    C.preview(os.path.join(SRC, 'preview.png'), (0.16, -0.2, 0.17), (0, 0, 0.045), key_loc=(0.3, -0.4, 0.5))
    print('[mug] preview rendered')
