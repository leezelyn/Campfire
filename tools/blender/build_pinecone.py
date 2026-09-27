"""
Campfire · Open pine cone (Blender 4.x, bpy) — Stage 5

    blender --background --python tools/blender/build_pinecone.py [-- --preview]
    python tools/blender/build_pinecone.py [--preview]              # pip "bpy" module

Outputs  assets/models/pinecone.glb · assets/source/pinecone/pinecone.blend (+ preview.png)
Contract PineconeRoot (origin = geometric centre: the cone tumbles round it in flight) · part Cone ·
         material Pinecone (cloned per instance: each cone chars and glows on its own)
         (see src/assets/ModelRegistry.js)

A large, dry, fully opened cone (0.16 m): woody scales on a Fibonacci spiral (golden angle), small and
closed at the base and tip, biggest just below the middle, drooping at the bottom and turning upward
toward the top. Each scale is a 26-triangle wedge that narrows to its stalk and thickens into a keeled,
weathered apophysis at the tip (lighter grey-tan, via the per-vertex `cf_tip` attribute) — ~1.7 k
triangles for the whole cone (up to 9 burn at once). Baked colour / ORM, 512 px.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402  (imports bpy first)
import bpy                       # noqa: E402
from mathutils import Matrix, Vector     # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'pinecone.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'pinecone')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv

N_SCALES = 60
H = 0.15                  # height of the scale-bearing axis
GA = math.pi * (3 - math.sqrt(5))

C.reset()
root = C.empty('PineconeRoot', size=0.05)


def tag(ob, hexcol, rough):
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    return ob


parts = []
# axis (mostly hidden between the scales) with a short stalk at the base
parts.append(tag(C.lathe('Axis', [
    (0.0, -0.092), (0.006, -0.090), (0.007, -0.080), (0.012, -0.070), (0.017, -0.040), (0.017, 0.020),
    (0.013, 0.055), (0.007, 0.075), (0.0, 0.080)
], 8), '#3b2416', 0.9))

STATIONS = (0.0, 0.35, 0.75, 1.0)


def scale_mesh(name, l, w, th):
    """Low-poly woody scale (26 tris): a wedge lofted through 4 diamond sections — narrow stalk, broad
    apophysis with a raised transverse keel on top — closed with a rounded tip."""
    verts, faces, tip = [], [], []
    for u in STATIONS:
        ww = w * (0.35 + 0.75 * u) * (0.75 if u == 1.0 else 1.0)
        top = th * (0.5 + 2.2 * u ** 3) * (0.55 if u == 1.0 else 1.0)
        bot = -th * 0.45
        x = l * u
        for y, z in ((-ww / 2, 0.0), (0.0, top), (ww / 2, 0.0), (0.0, bot)):
            verts.append((x, y, z + 0.18 * l * u * u))     # curl the scale slightly outward
            tip.append(min(1.0, max(0.0, (u - 0.55) / 0.35)))
    for s_ in range(len(STATIONS) - 1):
        for k in range(4):
            a, b = s_ * 4 + k, s_ * 4 + (k + 1) % 4
            faces.append((a, b, b + 4, a + 4))
    last = (len(STATIONS) - 1) * 4
    faces.append((last, last + 1, last + 2, last + 3))
    faces.append((3, 2, 1, 0))
    ob = C.mesh_object(name, verts, faces)
    at = ob.data.attributes.new('cf_tip', 'FLOAT', 'POINT')
    for i, v in enumerate(tip):
        at.data[i].value = v
    return ob


for i in range(N_SCALES):
    t = i / (N_SCALES - 1)                               # base 0 → tip 1
    a = i * GA
    prof = math.sin(math.pi * (0.06 + 0.88 * t)) ** 0.8  # small at both ends, largest below the middle
    prof *= 1.0 - 0.25 * t
    l = 0.012 + 0.030 * prof                             # scale length
    w = 0.85 * l + 0.007
    th = 0.0042
    elev = math.radians(-25 + 85 * t ** 1.3)             # droop at the base, point up near the tip
    z = -0.072 + H * t
    ob = scale_mesh(f'Scale{i}', l, w, th)
    m = (Matrix.Translation((0, 0, z)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((0.009, 0, 0))
         @ Matrix.Rotation(-elev, 4, 'Y'))
    ob.data.transform(m)
    shade = 0.85 + 0.3 * ((i * 0.618) % 1.0)
    base = tuple(int(c * shade) for c in (0x4c, 0x2b, 0x19))
    parts.append(tag(ob, '#%02x%02x%02x' % base, 0.88))

for o in parts:
    o.parent = root
C.unwrap_uv1(parts, uv0_tile=0.05)
base_p, orm_p = C.bake_weathering(parts, 'pinecone', TEX, size=512, dirt_height=0.0, fade=0.0,
                                  edge_wear=0.35, ao_distance=0.02, seed=41.0, tip_color='#7e6a54')
M_CONE = C.baked_material('Pinecone', base_p, orm_p, None)
for o in parts:
    C.set_material(o, M_CONE)
C.join(parts, 'Cone')

print(f'[pinecone] triangles: {C.triangle_count()}')
print(f'[pinecone] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[pinecone] saved .blend ({C.save_blend(os.path.join(SRC, "pinecone.blend")) / 1024:.0f} KB)')
if PREVIEW:
    root.location = (0, 0, 0.09)
    C.preview(os.path.join(SRC, 'preview.png'), (0.22, -0.30, 0.22), (0, 0, 0.09), key_loc=(0.3, -0.5, 0.5))
    print('[pinecone] preview rendered')
