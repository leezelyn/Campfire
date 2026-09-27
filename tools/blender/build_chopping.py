"""
Campfire · Chopping block + hatchet (Blender 4.x, bpy) — Stage 5b

    blender --background --python tools/blender/build_chopping.py [-- --preview]
    python tools/blender/build_chopping.py [--preview]              # pip "bpy" module

Outputs  assets/models/chopping.glb (four roots) · assets/source/chopping/chopping.blend (+ preview.png)
Contract ChopStumpRoot (origin = ground centre) · TopAnchor (centre of the top face, y 0.342: where the
         log to split stands) · AxeSocket (the resting pose of the axe, bit sunk in the top) ·
         AxeRoot (origin = centre of the eye, handle +Z / glTF +Y, bit toward −Y / glTF +Z — the pivot the
         chop keyframes rotate about) · optional BladeEdge, GripAnchor ·
         ChopLogRoot (the round stood on the block) · ChopHalfRoot (one half after the split)
         (see src/assets/ModelRegistry.js)

A well-used chopping block: a short round with a flared, lobed base and thick plated bark, a sawn top of
growth rings scarred by axe cuts and radial checks, a few chips on the ground. The hatchet has a forged
bearded head (black oxide, polished bevel) on a curved oval hickory handle with a swelled knob.
One baked atlas (UV1): colour / ORM (metal on the head) / relief normal.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402  (imports bpy first)
import bpy                       # noqa: E402
from mathutils import Matrix, Vector, noise as mnoise     # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'chopping.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'chopping')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv

TOP = 0.342                      # top face (v1 value: the chop log / split keyframes are built on it)
R = 0.172
SIDES = 28
BARK = '#4a3d31'
WOOD = '#a88b64'
# resting axe pose (AxeSocket), in the scene's (three.js) stump space: bit ~2 cm into the top, off the centre
# (the log to split stands at the centre), handle rising outward at ~30°. v1 buried the whole head sideways.
REST_EDGE = Vector((0.085, TOP - 0.02, 0.055))
REST_RISE = math.radians(30)

random.seed(5)
C.reset()
sroot = C.empty('ChopStumpRoot', size=0.2)
aroot = C.empty('AxeRoot', size=0.08)
lroot = C.empty('ChopLogRoot', size=0.05)
hroot = C.empty('ChopHalfRoot', size=0.05)


def tag(ob, hexcol, rough, pattern=0, metal=0.0):
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    ob['cf_pattern'] = float(pattern)
    ob['cf_metal'] = metal
    return ob


# ------------------------------------------------------------------ chopping block
def radius(z, a):
    flare = 0.075 * max(0.0, 1 - z / 0.09) ** 2                       # root flare at the base
    lobe = 0.045 * mnoise.noise(Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, 0.3 + z * 1.5)))
    return R * (1 + flare + lobe + 0.015 * math.sin(5 * a))


stump = []
rings_z = [-0.02, 0.0, 0.03, 0.07, 0.12, 0.2, 0.28, TOP]
verts, faces = [], []
for z in rings_z:
    for k in range(SIDES):
        a = 2 * math.pi * k / SIDES
        r = radius(z, a)
        verts.append((r * math.cos(a), r * math.sin(a), z))
for i in range(len(rings_z) - 1):
    for k in range(SIDES):
        a, b = i * SIDES + k, i * SIDES + (k + 1) % SIDES
        faces.append((a, b, b + SIDES, a + SIDES))
stump.append(tag(C.mesh_object('Trunk', verts, faces), BARK, 0.92, 1))
# sawn top: bark rim + end-grain disc
rim_v, rim_f = [], []
for k in range(SIDES):
    a = 2 * math.pi * k / SIDES
    rim_v.append((radius(TOP, a) * math.cos(a), radius(TOP, a) * math.sin(a), TOP))
for k in range(SIDES):
    a = 2 * math.pi * k / SIDES
    rim_v.append((radius(TOP, a) * 0.9 * math.cos(a), radius(TOP, a) * 0.9 * math.sin(a), TOP + 0.001))
for k in range(SIDES):
    k2 = (k + 1) % SIDES
    rim_f.append((k, k2, SIDES + k2, SIDES + k))
stump.append(tag(C.mesh_object('TopRim', rim_v, rim_f, smooth=False), '#2e241a', 0.95))
disc_v = [rim_v[SIDES + k] for k in range(SIDES)] + [(0, 0, TOP + 0.001)]
disc_f = [(k, (k + 1) % SIDES, SIDES) for k in range(SIDES)]
stump.append(tag(C.mesh_object('TopGrain', disc_v, disc_f, smooth=False), WOOD, 0.85, 2))
# axe cuts (dark slits) and radial checks on the top
for i in range(11):
    a = random.uniform(0, math.pi)
    d = Vector((math.cos(a), math.sin(a), 0))
    c = Vector((random.uniform(-0.07, 0.07), random.uniform(-0.07, 0.07), TOP + 0.0016))
    stump.append(tag(C.rounded_box(f'Cut{i}', (random.uniform(0.04, 0.085), 0.0028, 0.0012), c,
                                   normal=(0, 0, 1), tangent=tuple(d.cross(Vector((0, 0, 1)))), p=2.4, res=2),
                     '#2a1a0e', 0.95))
for i in range(4):
    a = i * 1.7 + 0.4
    d = Vector((math.cos(a), math.sin(a), 0))
    ln = random.uniform(0.06, 0.11)
    c = d * (R * 0.92 - ln / 2) + Vector((0, 0, TOP + 0.0014))
    stump.append(tag(C.rounded_box(f'Check{i}', (ln, 0.004, 0.0012), c, normal=(0, 0, 1),
                                   tangent=tuple(d.cross(Vector((0, 0, 1)))), p=2.0, res=2), '#1f140b', 0.95))
# chips on the ground
for i in range(9):
    a = random.uniform(0, 2 * math.pi)
    rr = random.uniform(R * 1.3, R * 2.3)
    d = Vector((math.cos(a + 1.2), math.sin(a + 1.2), 0))
    stump.append(tag(C.rounded_box(f'Chip{i}', (random.uniform(0.02, 0.04), random.uniform(0.012, 0.02), 0.004),
                                   (rr * math.cos(a), rr * math.sin(a), 0.002), normal=(0, 0, 1), tangent=tuple(d),
                                   p=3.0, res=2), '#b49a70', 0.85, 3))

# ------------------------------------------------------------------ hatchet (Blender: handle +Z, bit toward −Y)
STATIONS = [  # y, half thickness, z_top (away from the handle), z_bottom (toward the handle: beard)
    (0.036, 0.016, -0.024, 0.024), (0.022, 0.0172, -0.025, 0.025), (0.0, 0.0172, -0.025, 0.025),
    (-0.020, 0.0155, -0.024, 0.024), (-0.042, 0.010, -0.027, 0.030), (-0.070, 0.0062, -0.032, 0.041),
    (-0.098, 0.0030, -0.036, 0.050), (-0.110, 0.0012, -0.037, 0.053), (-0.1155, 0.0004, -0.036, 0.052)]
hv, hf, tipv = [], [], []
for y, t, z0, z1 in STATIONS:
    c = min(0.006, (z1 - z0) * 0.2)
    for x, z in ((t, z0 + c), (t * 0.7, z0), (-t * 0.7, z0), (-t, z0 + c),
                 (-t, z1 - c), (-t * 0.7, z1), (t * 0.7, z1), (t, z1 - c)):
        hv.append((x, y, z))
        tipv.append(min(1.0, max(0.0, (-y - 0.075) / 0.03)))           # polished bevel near the edge
for i in range(len(STATIONS) - 1):
    for k in range(8):
        a, b = i * 8 + k, i * 8 + (k + 1) % 8
        hf.append((a + 8, b + 8, b, a))                                # outward (stations run toward −Y)
hf.append(tuple(range(8)))
hf.append(tuple((len(STATIONS) - 1) * 8 + k for k in range(7, -1, -1)))
head = C.mesh_object('Head', hv, hf, smooth=True)
at = head.data.attributes.new('cf_tip', 'FLOAT', 'POINT')
for i, v in enumerate(tipv):
    at.data[i].value = v
C.bevel(head, 0.0015, 1)
C.apply_modifiers(head)
tag(head, '#2c2d2f', 0.55, 0, 1.0)
# curved oval handle with a swelled knob
hp = C.catmull([(0, 0.0, -0.027), (0, 0.0, 0.05), (0, -0.006, 0.16), (0, 0.002, 0.28), (0, -0.004, 0.37),
                (0, -0.010, 0.405)], 4)
hr = []
for p in hp:
    z = p[2]
    r = 0.0125 if z < 0.03 else 0.0155 - 0.0015 * min(1, (z - 0.03) / 0.3)
    if z > 0.36:
        r += 0.005 * min(1, (z - 0.36) / 0.03)                         # fawn's-foot swell
    hr.append(r)
handle = C.sweep('Handle', hp, hr, sides=10, cap_start=True, cap_end=True)
handle.data.transform(Matrix.Diagonal((0.82, 1.2, 1.0, 1.0)))         # oval: deeper toward the bit
tag(handle, '#8b6a44', 0.7, 3)
axe = [head, handle]

# ------------------------------------------------------------------ the log to split, and one of its halves
# conventions of the v1 procedural pieces (the chop animation / debris physics are built on them):
#   ChopLog  — origin at the bottom centre, axis +Z (glTF +Y), 0.30 m tall, r 0.056
#   ChopHalf — origin at the centre of the axis, axis +Z, bark shell on the +X side, split face at x = 0 (facing −X)
CL_H, CL_R, CL_SIDES = 0.30, 0.056, 14


def round_section(rr, a0, a1, n):
    return [(rr * (1 + 0.035 * math.sin(3 * a + 1.3)) * math.cos(a), rr * (1 + 0.035 * math.sin(3 * a + 1.3)) * math.sin(a))
            for a in [a0 + (a1 - a0) * i / n for i in range(n + 1)]]


def prism(name, ring, z0, z1, closed):
    """Extrude an XY polyline between z0 and z1 (side faces only); closed = wrap around."""
    n = len(ring)
    v = [(x, y, z0) for x, y in ring] + [(x, y, z1) for x, y in ring]
    f = [(k, (k + 1) % n, (k + 1) % n + n, k + n) for k in range(n if closed else n - 1)]
    return C.mesh_object(name, v, f)


def cap(name, ring, z, up):
    v = [(x, y, z) for x, y in ring]
    f = [tuple(range(len(ring))) if up else tuple(reversed(range(len(ring))))]
    return C.mesh_object(name, v, f, smooth=False)


log_ring = round_section(CL_R, 0, 2 * math.pi, CL_SIDES)[:-1]
chop_log = [tag(prism('ChopBark', log_ring, 0.0, CL_H, True), BARK, 0.92, 1),
            tag(cap('ChopTop', log_ring, CL_H, True), WOOD, 0.85, 2),
            tag(cap('ChopBottom', log_ring, 0.0, False), WOOD, 0.85, 2)]
half_arc = round_section(CL_R, -math.pi / 2, math.pi / 2, 8)
chord = [half_arc[-1], half_arc[0]]
chop_half = [tag(prism('HalfBark', half_arc, -CL_H / 2, CL_H / 2, False), BARK, 0.92, 1),
             tag(prism('HalfSplit', chord, -CL_H / 2, CL_H / 2, False), '#b8976a', 0.85, 3),
             tag(cap('HalfTop', half_arc, CL_H / 2, True), WOOD, 0.85, 2),
             tag(cap('HalfBottom', half_arc, -CL_H / 2, False), WOOD, 0.85, 2)]

# ------------------------------------------------------------------ anchors, pose, bake
C.empty('TopAnchor', (0, 0, TOP), sroot, size=0.05)
C.empty('BladeEdge', (0, -0.1155, 0.008), aroot, size=0.02)
C.empty('GripAnchor', (0, -0.004, 0.33), aroot, size=0.02)
# three.js stump space → Blender: (x, y, z)_three = (x, z, −y)_blender; three Euler 'XYZ' = Rx·Ry·Rz
T2B = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
# axe local frame (three): handle +Y, bit +Z, X = Y × Z
u = Vector((REST_EDGE.x, 0, REST_EDGE.z)).normalized()           # outward, horizontal
h = u * math.cos(REST_RISE) + Vector((0, 1, 0)) * math.sin(REST_RISE)
b = u * math.sin(REST_RISE) - Vector((0, 1, 0)) * math.cos(REST_RISE)   # ⟂ handle, into the wood
rot = Matrix((h.cross(b), h, b)).transposed()
edge_local = Vector((0, 0.008, 0.1155))                            # BladeEdge in three axe space
M3 = Matrix.Translation(REST_EDGE - rot @ edge_local) @ rot.to_4x4()
e = M3.to_euler('ZYX')                                             # = three.js Euler order 'XYZ'
print(f'[chopping] AxeSocket (three): p={tuple(round(v, 3) for v in M3.translation)} '
      f'r={tuple(round(v, 3) for v in (e.x, e.y, e.z))}')
# the axe object frame in Blender is itself T2B·(three local): handle +Z (three +Y), bit −Y (three +Z)
socket_m = T2B @ M3 @ T2B.inverted()
sock = C.empty('AxeSocket', (0, 0, 0), sroot, size=0.05)
sock.matrix_world = socket_m
for o in stump:
    o.parent = sroot
for o in axe:
    o.parent = aroot
for o in chop_log:
    o.parent = lroot
for o in chop_half:
    o.parent = hroot
aroot.matrix_world = socket_m          # in the .blend the axe rests in the block; the scene re-poses it
lroot.location = (0.42, 0.1, 0)        # display only: the scene places / animates these pieces
hroot.location = (0.40, -0.18, CL_R)
hroot.rotation_euler = (0, math.pi / 2, 0)
bpy.context.view_layer.update()

parts = stump + axe + chop_log + chop_half
C.unwrap_uv1(parts, uv0_tile=0.1)
base_p, orm_p, nrm_p, emi_p = C.bake_weathering(
    parts, 'chopping', TEX, size=512, dirt_height=0.07, fade=0.25, edge_wear=0.2, ao_distance=0.04,
    seed=53.0, patterns=True, normal_depth=0.003, metal=True, tip_color='#a3a6aa')
M_WOOD = C.baked_material('ChopWood', base_p, orm_p, nrm_p, 0.9, normal_uv='UV1')
M_STEEL = C.baked_material('AxeSteel', base_p, orm_p, None)
for o in stump:
    C.set_material(o, M_WOOD)
C.join(stump, 'Stump')
C.set_material(head, M_STEEL)
C.set_material(handle, M_WOOD)
C.join([head, handle], 'Axe')
for o in chop_log + chop_half:
    C.set_material(o, M_WOOD)
C.join(chop_log, 'ChopLog')
C.join(chop_half, 'ChopHalf')

print(f'[chopping] triangles: {C.triangle_count()}')
print(f'[chopping] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[chopping] saved .blend ({C.save_blend(os.path.join(SRC, "chopping.blend")) / 1024:.0f} KB)')
if PREVIEW:
    C.preview(os.path.join(SRC, 'preview.png'), (0.62, -0.95, 0.75), (0, 0, 0.3), key_loc=(0.5, -0.9, 1.1))
    print('[chopping] preview rendered')
