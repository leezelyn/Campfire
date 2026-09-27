"""
Campfire · Cloth-wrapped camp torch (Blender 4.x, bpy) — Stage 5

    blender --background --python tools/blender/build_torch.py [-- --preview]
    python tools/blender/build_torch.py [--preview]              # pip "bpy" module

Outputs  assets/models/torch.glb · assets/source/torch/torch.blend (+ preview.png)
Contract TorchRoot (origin = foot of the staff, axis +Z / glTF +Y) · FlameAnchor (top of the head, y 1.292:
         flame particles + point light) · optional GripAnchor · parts Handle, Wrap ·
         material TorchEmber (emissive map = ember gradient, intensity driven by the ignite progress)
         (see src/assets/ModelRegistry.js)

A 1.3 m staff cut from a slightly crooked branch, debarked and hand-worn, with a couple of knots; the head
is a bundle of pitch-soaked burlap bound round the top with spiral strips and jute twine, already charred
at the top from earlier use. The ember map glows over the top ~12 cm with a ragged burn line.
One baked atlas (UV1): staff colour / ORM / relief normal; head colour / ORM + tiling weave normal (UV0)
+ emissive (UV1).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402  (imports bpy first)
import bpy                       # noqa: E402
from mathutils import Vector     # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'torch.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'torch')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv

HEAD_TOP = 1.292                 # FlameAnchor (kept from v1: the ignite animation dips this point into the fire)
WOOD = '#62492f'
CLOTH = '#3b2d21'

C.reset()
root = C.empty('TorchRoot', size=0.1)


def tag(ob, hexcol, rough, pattern):
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    ob['cf_pattern'] = float(pattern)
    return ob


# ------------------------------------------------------------------ staff
axis = C.catmull([(0.0, 0.0, 0.0), (0.004, 0.002, 0.25), (-0.003, 0.004, 0.52), (0.005, -0.002, 0.78),
                  (0.0, 0.0, 1.02)], 6)
n = len(axis)
radii = []
for i, p in enumerate(axis):
    z = p[2]
    r = 0.027 + 0.006 * (z / 1.02)                  # thicker toward the head
    if z < 0.03:
        r *= 0.72 + 0.28 * (z / 0.03)               # rounded, slightly pointed foot
    radii.append(r)
staff = tag(C.sweep('Staff', axis, radii, sides=12, cap_start=True, cap_end=True), WOOD, 0.72, 3)
knots = []
for z, a in ((0.34, 0.6), (0.71, 3.4)):
    d = Vector((math.cos(a), math.sin(a), 0))
    knots.append(tag(C.rounded_box(f'Knot{z:g}', (0.018, 0.022, 0.009), d * 0.029 + Vector((0, 0, z)),
                                   normal=tuple(d), tangent=(0, 0, 1), p=2.2, res=3), '#5a3f27', 0.8, 3))

# ------------------------------------------------------------------ head
head = []
head.append(tag(C.lathe('WrapCore', [
    (0.030, 0.935), (0.046, 0.950), (0.060, 0.968), (0.068, 0.995), (0.071, 1.05), (0.072, 1.14),
    (0.071, 1.21), (0.067, 1.255), (0.058, 1.280), (0.040, 1.2915), (0.018, 1.2945), (0.0, 1.295)
], 20), CLOTH, 0.95, 5))
# spiral burlap strips over the bundle
for j, (turns, ph, z0, z1) in enumerate(((2.3, 0.0, 0.975, 1.265), (-1.6, 2.2, 1.0, 1.24))):
    pts, nrm = [], []
    for i in range(49):
        u = i / 48
        z = z0 + (z1 - z0) * u
        a = ph + turns * 2 * math.pi * u
        rr = 0.0735 - 0.004 * abs(u - 0.5) * 2
        pts.append((rr * math.cos(a), rr * math.sin(a), z))
        nrm.append((math.cos(a), math.sin(a), 0))
    head.append(tag(C.strip(f'Strip{j}', pts, nrm, 0.030, 0.003), CLOTH, 0.95, 5))
# jute twine lashing at the base of the head
twine = [(0.0585 * math.cos(2 * math.pi * 5 * i / 90), 0.0585 * math.sin(2 * math.pi * 5 * i / 90),
          0.957 + 0.024 * i / 90) for i in range(91)]
head.append(tag(C.curve_tube('Twine', twine, 0.0026, sides=6), '#8c7a57', 0.9, 0))

# ------------------------------------------------------------------ anchors, bake, materials
C.empty('FlameAnchor', (0, 0, HEAD_TOP), root, size=0.04)
C.empty('GripAnchor', (0.002, 0.003, 0.58), root, size=0.04)

parts = [staff] + knots + head
C.unwrap_uv1(parts, uv0_tile=0.08)
base_p, orm_p, nrm_p, emi_p = C.bake_weathering(
    parts, 'torch', TEX, size=512, dirt_height=0.06, fade=0.15, edge_wear=0.25, ao_distance=0.03,
    seed=31.0, patterns=True, glow_z=(1.17, 1.29), normal_depth=0.0015)
weave = C.weave_normal('torch_weave_normal', TEX, size=256, period=5, strength=2.0)
M_WOOD = C.baked_material('TorchWood', base_p, orm_p, nrm_p, 0.8, normal_uv='UV1')
M_EMBER = C.baked_material('TorchEmber', base_p, orm_p, weave, 0.9, emissive_path=emi_p, emissive_strength=1.0)

for o in [staff] + knots:
    C.set_material(o, M_WOOD)
C.join([staff] + knots, 'Handle').parent = root
for o in head:
    C.set_material(o, M_EMBER)
C.join(head, 'Wrap').parent = root

print(f'[torch] triangles: {C.triangle_count()}')
print(f'[torch] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[torch] saved .blend ({C.save_blend(os.path.join(SRC, "torch.blend")) / 1024:.0f} KB)')
if PREVIEW:
    C.preview(os.path.join(SRC, 'preview.png'), (0.55, -0.75, 1.35), (0, 0, 1.0), key_loc=(0.5, -0.8, 1.6))
    print('[torch] preview rendered')
