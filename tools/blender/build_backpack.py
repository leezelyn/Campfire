"""
Campfire · Backpack asset build (Blender 4.x, bpy) — Stage 2

    blender --background --python tools/blender/build_backpack.py [-- --preview]
    python tools/blender/build_backpack.py [--preview]          # pip "bpy" module

Outputs  assets/models/backpack.glb · assets/source/backpack/backpack.blend (+ preview.png)
Contract BackpackRoot (root) · optional HandleSocketL/R, LidPivot (see src/assets/ModelRegistry.js)

A used ~50 L trekking pack standing on its base, front (pocket side) toward Blender −Y (glTF +Z, the fire).
Soft fabric panels are superellipsoids deformed with load bulge, compression folds and strap pinches;
straps are surface-conforming webbing; one baked weathered atlas (UV1) + tiling weave normal (UV0).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402  (imports bpy first)
import bpy                       # noqa: E402
from mathutils import Vector     # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'backpack.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'backpack')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv
ss = lambda e0, e1, x: (lambda t: t * t * (3 - 2 * t))(min(1.0, max(0.0, (x - e0) / (e1 - e0))))

C.reset()
root = C.empty('BackpackRoot', size=0.2)


def tag(ob, hexcol, rough):
    """Per-object look for the shared weathering bake (read by an Attribute node)."""
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    return ob


# ------------------------------------------------------------------ main bag
def body_deform(v):
    x, y, z = v.x, v.y, v.z
    t = min(1.0, max(0.0, (z - 0.02) / 0.74))
    if z < 0.03:                                     # flat base resting on the ground
        z = 0.03 - (0.03 - z) * 0.12
    y *= 1 - 0.22 * t                                # tapers toward the top (back to front)
    x *= 1 - 0.08 * t
    if y < 0:                                        # the load settles low at the front
        y -= 0.03 * math.sin(math.pi * min(1.0, t * 1.2)) * max(0.0, 1 - abs(x) / 0.2)
    else:
        y = min(y, 0.112 + (y - 0.112) * 0.3) if y > 0.112 else y   # flatter against the back panel
    k = ss(0.70, 0.79, z)                            # drawcord collar gathered under the lid
    x *= 1 - 0.16 * k
    y *= 1 - 0.2 * k
    r = Vector((x / 0.17, y / 0.125, 0))
    r = r.normalized() if r.length > 1e-6 else Vector((1, 0, 0))
    folds = (0.0055 * math.sin(2 * math.pi * z / 0.078 + 2.2 * math.sin(x * 12))
             + 0.004 * math.sin(z * 23 + y * 17 + x * 9)) * ss(0.05, 0.12, z)
    pinch = -0.01 * (math.exp(-((z - 0.32) / 0.022) ** 2) + math.exp(-((z - 0.56) / 0.022) ** 2)) * (abs(x) / 0.17) ** 2
    d = folds + pinch
    return Vector((x + r.x * d, y + r.y * d, z))


body = tag(C.superellipsoid('Body', (0.17, 0.125, 0.375), p=3.2, res=13, center=(0, 0, 0.395), deform=body_deform),
           '#4b5034', 0.82)

lid_pivot = C.empty('LidPivot', (0, 0.12, 0.78), root)        # hinge along the back top edge (for a future "open lid")


def lid_deform(v):
    x, y, z = v.x, v.y, v.z
    if y < 0:
        z -= 0.065 * ss(0.0, -0.17, y) ** 1.4                  # front edge drapes over the collar
    if z > 0.80:
        z += 0.014 * (1 - min(1.0, (x / 0.18) ** 2)) * (1 - min(1.0, (y / 0.15) ** 2))
    z += 0.003 * math.sin(x * 41 + y * 23) + 0.002 * math.sin(y * 57 - x * 13)
    return Vector((x, y, z))


lid = tag(C.superellipsoid('Lid', (0.182, 0.152, 0.052), p=3.0, res=10, center=(0, -0.012, 0.80), deform=lid_deform),
          '#474c34', 0.84)

pocket = tag(C.superellipsoid('FrontPocket', (0.125, 0.04, 0.15), p=3.5, res=9, center=(0, -0.157, 0.36),
                              deform=lambda v: Vector((v.x, v.y + 0.036 * (v.x / 0.125) ** 2
                                                       + 0.003 * math.sin(v.z * 60 + v.x * 20), v.z))),
             '#50553a', 0.82)
side_pockets = []
for s in (-1, 1):
    side_pockets.append(tag(C.superellipsoid(f'SidePocket{"R" if s > 0 else "L"}', (0.034, 0.088, 0.11), p=3.0, res=7,
                                             center=(s * 0.182, -0.005, 0.165),
                                             deform=lambda v, s=s: Vector((v.x + s * 0.012 * ss(0.17, 0.27, v.z), v.y, v.z))),
                            '#3f4230', 0.86))
back = tag(C.superellipsoid('BackPanel', (0.15, 0.022, 0.29), p=4.5, res=10, center=(0, 0.137, 0.41),
                            deform=lambda v: Vector((v.x, v.y - (0.008 * math.exp(-(v.x / 0.025) ** 2) if v.y > 0.137 else 0)
                                                     + 0.018 * ((v.z - 0.41) / 0.29) ** 2, v.z))),
           '#2c2e2a', 0.9)

# harness: padded shoulder straps and hip-belt wings (padded strips)
pads = []
for s in (-1, 1):
    pts = C.resample([(s * 0.06, 0.15, 0.70), (s * 0.095, 0.197, 0.62), (s * 0.12, 0.217, 0.48),
                      (s * 0.13, 0.207, 0.33), (s * 0.125, 0.182, 0.2)], 18)
    pads.append(tag(C.strip(f'ShoulderStrap{"R" if s > 0 else "L"}', pts, [(0, 1, 0)] * len(pts), 0.064, 0.015,
                            taper=lambda u: 1.0 - 0.35 * u), '#2a2c28', 0.88))
    wing = C.resample([(s * 0.13, 0.15, 0.17), (s * 0.192, 0.1, 0.15), (s * 0.212, 0.0, 0.12),
                       (s * 0.205, -0.08, 0.07), (s * 0.19, -0.13, 0.03)], 16)
    nrm = [Vector((p.x, p.y * 0.6, 0.15)).normalized() for p in wing]
    pads.append(tag(C.strip(f'HipWing{"R" if s > 0 else "L"}', wing, nrm, 0.085, 0.017,
                            taper=lambda u: 1.0 - 0.4 * u), '#2a2c28', 0.88))

# rolled closed-cell foam mat strapped across the front base
surf_front = C.Surface([body, pocket])
front_y = surf_front.hit((0, -1.0, 0.1), (0, 1, 0))[0].y
MAT_R, MAT_L = 0.072, 0.5
mat_c = Vector((0, front_y - MAT_R + 0.01, MAT_R + 0.002))
mv, mf = [], []
RS, RL = 18, 14
for j in range(RL + 1):
    xx = (j / RL - 0.5) * MAT_L
    for i in range(RS):
        a = 2 * math.pi * i / RS
        r = MAT_R * (1 + 0.025 * math.sin(a * 3 + xx * 20)) * (0.97 if j in (0, RL) else 1)
        mv.append((xx, mat_c.y + math.cos(a) * r, mat_c.z + math.sin(a) * r * 0.95))
for j in range(RL):
    for i in range(RS):
        a0, a1 = j * RS + i, j * RS + (i + 1) % RS
        mf.append((a0, a1, a1 + RS, a0 + RS))
mf.append(tuple(reversed(range(RS))))
mf.append(tuple(range(RL * RS, RL * RS + RS)))
foam = tag(C.mesh_object('FoamMat', mv, mf), '#43626a', 0.93)

fabric = [body, lid, pocket, *side_pockets, back, *pads, foam]

# ------------------------------------------------------------------ webbing, hardware, cord, stitching
surf = C.Surface([body, pocket, lid])
straps, plastic, metal, cords, stitches = [], [], [], [], []


def front_hit(x, z):
    return surf.hit((x, -1.0, z), (0, 1, 0))


for sx in (-0.138, 0.138):                                 # front compression / lid straps (along the pocket edges)
    lower = [front_hit(sx, z)[0] for z in [0.08 + i * 0.04 for i in range(15)]]
    lower = [p for p in lower if p is not None]
    over = [surf.hit((sx, y, 1.2), (0, 0, -1))[0] for y in [-0.17 + i * 0.03 for i in range(8)]]
    over = [p for p in over if p is not None]
    straps.append(C.surface_strip(f'LidStrap{"R" if sx > 0 else "L"}', surf, lower + over, 0.022, 0.003, n=44,
                                  uv_tile=0.04))
    loc, nrm = front_hit(sx, 0.63)
    plastic.append(C.rounded_box('LidBuckle', (0.034, 0.05, 0.009), loc + nrm * 0.006, nrm, (0, 0, 1)))
    loc, nrm = front_hit(sx, 0.14)
    plastic.append(C.rounded_box('LadderLock', (0.03, 0.02, 0.006), loc + nrm * 0.005, nrm, (0, 0, 1)))
    # loose strap tail hanging below the ladder lock
    tail = [loc + nrm * 0.006 + Vector((0, -0.004 * k, -0.02 * k)) for k in range(4)]
    straps.append(C.strip('StrapTail', tail, [nrm] * 4, 0.02, 0.0025, uv_tile=0.04))

for s in (-1, 1):                                          # side compression straps
    for z in (0.32, 0.56):
        pts = [surf.hit((s * 0.6, y, z), (-s, 0, 0))[0] for y in [-0.13 + i * 0.032 for i in range(8)]]
        pts = [p for p in pts if p is not None]
        straps.append(C.surface_strip('SideStrap', surf, pts, 0.02, 0.003, n=24, uv_tile=0.04))
        loc, nrm = surf.hit((s * 0.6, -0.09, z), (-s, 0, 0))
        plastic.append(C.rounded_box('SideLadderLock', (0.028, 0.02, 0.006), loc + nrm * 0.005, nrm, (0, 1, 0)))
    # elastic band around the side pocket mouth
    rim = [(s * 0.182 + s * 0.012 + math.cos(a) * 0.036, -0.005 + math.sin(a) * 0.087, 0.268)
           for a in [2 * math.pi * k / 24 for k in range(25)]]
    straps.append(C.curve_tube('PocketElastic', rim, 0.0055, sides=6))

# sternum strap + buckle, shoulder-strap lower webbing + ladder locks, hip buckles lying on the ground
straps.append(C.strip('Sternum', C.resample([(-0.125, 0.226, 0.5), (0, 0.232, 0.5), (0.125, 0.226, 0.5)], 10),
                      [(0, 1, 0)] * 10, 0.018, 0.003, uv_tile=0.04))
plastic.append(C.rounded_box('SternumBuckle', (0.05, 0.03, 0.009), (0, 0.236, 0.5), (0, 1, 0), (1, 0, 0)))
for s in (-1, 1):
    a, b = Vector((s * 0.125, 0.183, 0.2)), Vector((s * 0.16, 0.118, 0.075))
    straps.append(C.strip('ShoulderWebbing', C.resample([a, (a + b) / 2 + Vector((0, 0.01, 0)), b], 8),
                          [Vector((s * 0.4, 1, 0)).normalized()] * 8, 0.022, 0.003, uv_tile=0.04))
    plastic.append(C.rounded_box('ShoulderLadder', (0.03, 0.022, 0.006), a + Vector((0, 0.006, -0.012)),
                                 (s * 0.3, 1, 0), (0, 0, 1)))
    end = Vector((s * 0.19, -0.13, 0.03))
    web = [end, end + Vector((-s * 0.01, -0.05, -0.02)), end + Vector((-s * 0.02, -0.09, -0.026))]
    straps.append(C.strip('HipWebbing', C.resample(web, 6), [(0, 0, 1)] * 6, 0.024, 0.003, uv_tile=0.04))
    plastic.append(C.rounded_box('HipBuckle', (0.04, 0.056, 0.011), end + Vector((-s * 0.02, -0.11, -0.022)),
                                 (0, 0, 1), (0, -1, 0)))
# haul loop on top of the back panel
straps.append(C.strip('HaulLoop', C.resample([(-0.045, 0.142, 0.72), (-0.03, 0.16, 0.765), (0.03, 0.16, 0.765),
                                              (0.045, 0.142, 0.72)], 12), [(0, 1, 0)] * 12, 0.022, 0.004, uv_tile=0.04))
C.empty('HandleSocketL', (-0.045, 0.142, 0.72), root)
C.empty('HandleSocketR', (0.045, 0.142, 0.72), root)

# foam-mat straps: two loops around the roll
for sx in (-0.15, 0.15):
    loop = [(sx, mat_c.y + math.cos(a) * (MAT_R + 0.003), mat_c.z + math.sin(a) * (MAT_R + 0.003) * 0.95)
            for a in [2 * math.pi * k / 20 for k in range(21)]]
    straps.append(C.strip('MatStrap', loop, [(0, math.cos(2 * math.pi * k / 20), math.sin(2 * math.pi * k / 20))
                                              for k in range(21)], 0.02, 0.0025, uv_tile=0.04))

# front pocket: zipper along the top, bungee X, stitched perimeter
zp = [front_hit(x, 0.47)[0] for x in [-0.105 + i * 0.015 for i in range(15)]]
straps.append(C.surface_strip('PocketZip', surf, zp, 0.011, 0.0025, n=30, uv_tile=0.04))
loc, nrm = front_hit(0.055, 0.47)
plastic.append(C.rounded_box('ZipSlider', (0.016, 0.022, 0.007), loc + nrm * 0.005, nrm, (1, 0, 0)))
metal.append(C.rounded_box('ZipPull', (0.008, 0.028, 0.003), loc + nrm * 0.008 + Vector((0, 0, -0.022)), nrm, (0, 0, 1)))
hooks = {}
for hx in (-0.095, 0.095):
    for hz in (0.44, 0.27):
        l, n = front_hit(hx, hz)
        hooks[(hx, hz)] = (l, n)
        plastic.append(C.rounded_box('CordHook', (0.016, 0.014, 0.008), l + n * 0.004, n, (0, 0, 1)))


def cord(a, b):
    la, na = hooks[a]
    lb, nb = hooks[b]
    mid = (la + lb) / 2
    lm, nm = surf.nearest(mid)
    return C.curve_tube('Bungee', [la + na * 0.008, lm + nm * 0.011, lb + nb * 0.008], 0.0028, sides=6)


cords += [cord((-0.095, 0.44), (0.095, 0.27)), cord((0.095, 0.44), (-0.095, 0.27)), cord((-0.095, 0.44), (0.095, 0.44))]

outline = []
for k in range(41):                                        # rounded-rectangle outline inset on the pocket face
    a = 2 * math.pi * k / 40
    cx, cz = math.cos(a), math.sin(a)
    px = 0.108 * math.copysign(abs(cx) ** 0.4, cx)
    pz = 0.36 + 0.132 * math.copysign(abs(cz) ** 0.4, cz)
    h = front_hit(px, pz)[0]
    if h is not None:
        outline.append(h)
stitches.append(C.dashes('PocketStitch', surf, outline))
lid_edge = [front_hit(x, 0.745)[0] for x in [-0.16 + i * 0.02 for i in range(17)]]
stitches.append(C.dashes('LidStitch', surf, [p for p in lid_edge if p is not None]))
for pad in pads[::2]:                                      # edge stitching on the shoulder straps
    ps = C.Surface([pad])
    me = pad.data
    n = len(me.vertices) // 4
    for e0, e1 in ((3, 2), (2, 3)):
        line = [(me.vertices[4 * k + e0].co * 0.8 + me.vertices[4 * k + e1].co * 0.2) for k in range(1, n - 1)]
        stitches.append(C.dashes('StrapStitch', ps, line, lift=0.0012))

# ------------------------------------------------------------------ materials, bake, assemble
weave = C.weave_normal('pack_weave_normal', TEX, period=6, strength=1.4)
twill = C.weave_normal('pack_webbing_normal', TEX, size=256, period=4, strength=1.8, kind='twill', seed=3)
C.unwrap_uv1(fabric, uv0_tile=0.08)
base_p, orm_p = C.bake_weathering(fabric, 'pack_fabric', TEX, size=1024, dirt_height=0.14, fade=0.25,
                                  edge_wear=0.3, soot_front=0.08, ao_distance=0.12, seed=2.0)
M_FABRIC = C.baked_material('PackFabric', base_p, orm_p, weave, 0.45)
M_WEB = C.pbr('Webbing', C.srgb('#26271f'), 0.86, normal_img=twill, normal_strength=0.6)
M_PLASTIC = C.pbr('HardwarePlastic', C.srgb('#161616'), 0.5)
M_METAL = C.pbr('HardwareMetal', C.srgb('#7d7b74'), 0.4, metal=1.0)
M_THREAD = C.pbr('Thread', C.srgb('#857f69'), 0.9)
M_CORD = C.pbr('Cord', C.srgb('#1d2320'), 0.75)

for o in fabric:
    C.set_material(o, M_FABRIC)
lid_obj = lid
pack = C.join([body, pocket, *side_pockets, back, *pads, foam], 'PackBody')
pack.parent = root
bpy.context.view_layer.update()
lid_obj.parent = lid_pivot
lid_obj.matrix_parent_inverse = lid_pivot.matrix_world.inverted()
for o in straps:
    C.set_material(o, M_WEB)
C.join(straps, 'Straps').parent = root
for o in plastic:
    C.set_material(o, M_PLASTIC)
for o in metal:
    C.set_material(o, M_METAL)
hw = C.join(plastic + metal, 'Hardware')
hw.parent = root
for o in cords:
    C.set_material(o, M_CORD)
bungee = C.join(cords, 'Bungee')
bungee.parent = root
bungee['noCastShadow'] = True
for o in stitches:
    C.set_material(o, M_THREAD)
st = C.join(stitches, 'Stitching')
st.parent = root
st['noCastShadow'] = True
for o in bpy.context.scene.objects:           # anything left unparented goes under the root
    if o is not root and o.parent is None:
        o.parent = root

print(f'[backpack] triangles: {C.triangle_count()}')
print(f'[backpack] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[backpack] saved .blend ({C.save_blend(os.path.join(SRC, "backpack.blend")) / 1024:.0f} KB)')
if PREVIEW:
    C.preview(os.path.join(SRC, 'preview.png'), (0.95, -1.35, 0.85), (0, 0.0, 0.4), key_loc=(0.5, -1.6, 0.6))
    print('[backpack] preview rendered')
