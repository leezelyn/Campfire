"""
Campfire · Folding camp chair asset build (Blender 4.x, bpy) — Stage 2

    blender --background --python tools/blender/build_chair.py [-- --preview]
    python tools/blender/build_chair.py [--preview]              # pip "bpy" module

Outputs  assets/models/chair.glb · assets/source/chair/chair.blend (+ preview.png)
Contract ChairRoot (root) · optional SeatAnchor (see src/assets/ModelRegistry.js)

A well-used folding "quad" camp chair, front toward Blender −Y (glTF +Z, the fire):
19 mm powder-coated steel tubes with offset X legs, rivet pivots, plastic foot caps and moulded armrests;
canvas seat/back slings that sag between the rails with corner tension folds, sleeves wrapped round the
rails, piped hems, stitching and a drink holder. Fabric uses one baked weathered atlas (UV1) + weave normal (UV0).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402
import bpy                       # noqa: E402
from mathutils import Vector     # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'chair.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'chair')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv

HS = 0.42            # seat rail height
SX = 0.255           # half width between the seat rails
YF, YB = -0.235, 0.215   # seat front / back (front = −Y)
BACK_TOP = 0.87
BACK_LEAN = 0.09
ARM_Z = 0.625
TUBE = 0.0095

C.reset()
root = C.empty('ChairRoot', size=0.2)


def tag(ob, hexcol, rough):
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    return ob


def fold_fan(a, b, ax, ay, amp, n, decay, phase):
    dx, dy = a - ax, b - ay
    rho = math.hypot(dx, dy)
    if rho < 1e-6:
        return 0.0
    return amp * math.sin(n * math.atan2(dy, dx) + phase) * math.exp(-rho / decay) * (1 - math.exp(-rho / 0.04))


# ------------------------------------------------------------------ frame
tubes, plastic, bolts = [], [], []


def tube(name, a, b, r=TUBE):
    tubes.append(C.curve_tube(name, [a, b], r, sides=8))


for s in (-1, 1):
    xo, xi = s * (SX + 0.008), s * (SX - 0.008)          # the two legs of an X pass each other at the pivot
    tube('LegA', (xo, YF - 0.03, 0.0), (xo, YB, HS))
    tube('LegB', (xi, YB + 0.03, 0.0), (xi, YF, HS))
    tube('SeatRail', (s * SX, YF - 0.012, HS), (s * SX, YB + 0.012, HS))
    top = (s * (SX - 0.012), YB + BACK_LEAN, BACK_TOP)
    tube('BackUpright', (s * SX, YB, HS), top)
    # armrest: from the back upright forward, then a post down to the front of the seat rail
    k = (ARM_Z - HS) / (BACK_TOP - HS)
    back_pt = (s * (SX + 0.004), YB + BACK_LEAN * k, ARM_Z)
    front_pt = (s * (SX + 0.012), YF + 0.01, ARM_Z)
    tube('ArmRail', back_pt, front_pt, 0.0085)
    tube('ArmPost', front_pt, (s * SX, YF + 0.01, HS), 0.0085)
    # moulded armrest pad on top of the rail
    plastic.append(C.rounded_box('ArmPad', (0.058, 0.33, 0.02), ((back_pt[0] + front_pt[0]) / 2, 0.012, ARM_Z + 0.014),
                                 (0, 0, 1), (0, -1, 0), p=5.0, res=4))
    # pivot rivets and joints
    zc = HS / 2
    yc = (YF - 0.03 + YB) / 2
    bolts.append(C.rounded_box('Pivot', (0.016, 0.016, 0.008), (s * (SX + 0.02), yc, zc), (s, 0, 0), (0, 0, 1), p=2.5))
    for pt in ((s * (SX + 0.012), YB, HS), (s * (SX + 0.012), YF, HS)):
        bolts.append(C.rounded_box('Rivet', (0.012, 0.012, 0.006), pt, (s, 0, 0), (0, 0, 1), p=2.5))
    # foot caps
    for fp in ((xo, YF - 0.03), (xi, YB + 0.03)):
        plastic.append(C.rounded_box('FootCap', (0.028, 0.028, 0.022), (fp[0], fp[1], 0.011), (0, 0, 1), (0, 1, 0), p=3.0, res=4))
tube('FrontBar', (-SX, YF + 0.004, HS - 0.02), (SX, YF + 0.004, HS - 0.02))
tube('LowBarF', (-(SX + 0.008), YF - 0.022, 0.06), (SX + 0.008, YF - 0.022, 0.06))
tube('LowBarB', (-(SX - 0.008), YB + 0.022, 0.06), (SX - 0.008, YB + 0.022, 0.06))
tube('TopRail', (-(SX - 0.012), YB + BACK_LEAN, BACK_TOP), (SX - 0.012, YB + BACK_LEAN, BACK_TOP))

# ------------------------------------------------------------------ fabric
def sling(name, nu, nv, corner):
    """Grid sling: corner(u, v) → point; u across (x), v along. Faces up/outward."""
    verts, faces = [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            verts.append(corner(i / nu, j / nv))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    return C.mesh_object(name, verts, faces)


def seat_pt(u, v):
    x = (u - 0.5) * 2 * (SX - 0.012)
    y = YF + 0.006 + v * (YB - YF - 0.012)
    a, b = u * 2 * SX, v * (YB - YF)
    sag = 0.05 * math.sin(math.pi * u) ** 0.9 * math.sin(math.pi * min(1.0, v * 1.08)) ** 0.8
    f = sum(fold_fan(a, b, ax, ay, 0.006, 9, 0.16, ph) for ax, ay, ph in
            ((0, 0, 0.3), (2 * SX, 0, 1.1), (0, YB - YF, 2.0), (2 * SX, YB - YF, 0.7)))
    env = math.sin(math.pi * u) ** 0.5 * math.sin(math.pi * v) ** 0.5
    return Vector((x, y, HS + 0.004 - sag + f * env))


def back_pt(u, v):
    z = HS + 0.09 + v * (BACK_TOP - HS - 0.1)
    k = (z - HS) / (BACK_TOP - HS)
    x = (u - 0.5) * 2 * (SX - 0.014 - 0.012 * k)
    y = YB + BACK_LEAN * k + 0.004
    bulge = 0.032 * math.sin(math.pi * u) ** 0.9 * math.sin(math.pi * v) ** 0.7
    f = sum(fold_fan(u * 0.5, v * 0.4, ax, ay, 0.005, 8, 0.12, ph) for ax, ay, ph in
            ((0, 0, 0.4), (0.5, 0, 1.5), (0, 0.4, 2.2), (0.5, 0.4, 0.9)))
    return Vector((x, y + bulge + f * math.sin(math.pi * u) ** 0.5 * math.sin(math.pi * v) ** 0.5, z))


seat = tag(sling('SeatSling', 14, 12, seat_pt), '#6b3a2f', 0.84)
C.solidify(seat, 0.0025, offset=-1)
backsl = tag(sling('BackSling', 12, 14, back_pt), '#6b3a2f', 0.84)
C.solidify(backsl, 0.0025, offset=-1)
sleeves = []
for s in (-1, 1):   # fabric wrapped round the seat rails and back uprights
    sleeves.append(tag(C.curve_tube('SeatSleeve', [(s * SX, YF + 0.01, HS), (s * SX, YB - 0.01, HS)], 0.0165, sides=8),
                       '#603329', 0.86))
    k0, k1 = 0.09 / (BACK_TOP - HS), 0.97
    p0 = Vector((s * SX, YB, HS)).lerp(Vector((s * (SX - 0.012), YB + BACK_LEAN, BACK_TOP)), k0)
    p1 = Vector((s * SX, YB, HS)).lerp(Vector((s * (SX - 0.012), YB + BACK_LEAN, BACK_TOP)), k1)
    sleeves.append(tag(C.curve_tube('BackSleeve', [p0, p1], 0.0165, sides=8), '#603329', 0.86))
sleeves.append(tag(C.curve_tube('TopSleeve', [(-(SX - 0.02), YB + BACK_LEAN, BACK_TOP), (SX - 0.02, YB + BACK_LEAN, BACK_TOP)],
                                0.0175, sides=8), '#603329', 0.86))
hems = [tag(C.curve_tube('FrontHem', [seat_pt(u, 0) + Vector((0, -0.004, 0)) for u in [i / 16 for i in range(17)]], 0.006),
            '#3a1a16', 0.8),
        tag(C.curve_tube('BackHem', [back_pt(u, 0) + Vector((0, 0.002, -0.004)) for u in [i / 16 for i in range(17)]], 0.006),
            '#3a1a16', 0.8)]
# drink holder hanging from the right armrest front
hx, hy, hz = SX + 0.05, YF + 0.06, ARM_Z - 0.012
cv, cf = [], []
RS = 12
for j, (zz, rr) in enumerate(((0.0, 0.041), (-0.045, 0.043), (-0.09, 0.04), (-0.1, 0.03))):
    for i in range(RS):
        a = 2 * math.pi * i / RS
        cv.append((hx + math.cos(a) * rr, hy + math.sin(a) * rr, hz + zz + 0.003 * math.sin(a * 3 + j)))
for j in range(3):
    for i in range(RS):
        a0, a1 = j * RS + i, j * RS + (i + 1) % RS
        cf.append((a0, a0 + RS, a1 + RS, a1))
cf.append(tuple(range(3 * RS, 4 * RS)))
cup = tag(C.mesh_object('DrinkHolder', cv, cf), '#603329', 0.88)
C.solidify(cup, 0.002, offset=-1)
plastic.append(C.curve_tube('DrinkRim', [(hx + math.cos(a) * 0.042, hy + math.sin(a) * 0.042, hz + 0.002)
                                         for a in [2 * math.pi * k / 20 for k in range(21)]], 0.004, sides=6))
# fabric tab stitched to the armrest rail, holding the drink holder
tab_pts = C.resample([(SX + 0.012, hy, ARM_Z - 0.004), (hx - 0.03, hy, hz + 0.004), (hx - 0.04, hy, hz - 0.03)], 6)
tab = tag(C.strip('HolderTab', tab_pts, [(0, -1, 0)] * 6, 0.045, 0.003), '#603329', 0.88)
fabric = [seat, backsl, *sleeves, *hems, cup, tab]

# stitching along the hems and sleeves
surf = C.Surface([seat, backsl, *sleeves])
stitches = [
    C.dashes('SeatStitchF', surf, [seat_pt(u, 0.035) for u in [0.03 + i * 0.047 for i in range(21)]]),
    C.dashes('BackStitchB', surf, [back_pt(u, 0.04) for u in [0.03 + i * 0.047 for i in range(21)]]),
    C.dashes('BackStitchT', surf, [back_pt(u, 0.96) for u in [0.03 + i * 0.047 for i in range(21)]]),
]
for s in (-1, 1):
    stitches.append(C.dashes('SeatStitchS', surf, [seat_pt(0.5 + s * 0.46, v) for v in [0.04 + i * 0.046 for i in range(21)]]))

C.empty('SeatAnchor', (0, (YF + YB) / 2, HS - 0.03), root)

# ------------------------------------------------------------------ materials, bake, assemble
weave = C.weave_normal('chair_weave_normal', TEX, period=7, strength=1.5)
C.unwrap_uv1(fabric, uv0_tile=0.1)
base_p, orm_p = C.bake_weathering(fabric, 'chair_fabric', TEX, size=1024, dirt_height=0.0, fade=0.45,
                                  edge_wear=0.35, stains=0.18, ao_distance=0.1, seed=5.0)
M_FABRIC = C.baked_material('ChairFabric', base_p, orm_p, weave, 0.45, cull=False)
M_FRAME = C.pbr('ChairFrame', C.srgb('#23262a'), 0.42, metal=0.35)
M_PLASTIC = C.pbr('ChairPlastic', C.srgb('#141414'), 0.62)
M_BOLT = C.pbr('ChairRivet', C.srgb('#8f8d86'), 0.35, metal=1.0)
M_THREAD = C.pbr('Thread', C.srgb('#b09a86'), 0.9)
for o in fabric:
    C.set_material(o, M_FABRIC)
C.join(fabric, 'Fabric').parent = root
for o in tubes:
    C.set_material(o, M_FRAME)
C.join(tubes, 'Frame').parent = root
for o in plastic:
    C.set_material(o, M_PLASTIC)
for o in bolts:
    C.set_material(o, M_BOLT)
C.join(plastic + bolts, 'Fittings').parent = root
for o in stitches:
    C.set_material(o, M_THREAD)
st = C.join(stitches, 'Stitching')
st.parent = root
st['noCastShadow'] = True
for o in bpy.context.scene.objects:
    if o is not root and o.parent is None:
        o.parent = root

print(f'[chair] triangles: {C.triangle_count()}')
print(f'[chair] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[chair] saved .blend ({C.save_blend(os.path.join(SRC, "chair.blend")) / 1024:.0f} KB)')
if PREVIEW:
    C.preview(os.path.join(SRC, 'preview.png'), (1.0, -1.45, 1.0), (0, 0.0, 0.4), key_loc=(0.4, -1.6, 0.7))
    print('[chair] preview rendered')
