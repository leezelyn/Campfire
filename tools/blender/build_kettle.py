"""
Campfire · Cast-iron camp kettle + forged pot stand (Blender 4.x, bpy) — Stage 4

    blender --background --python tools/blender/build_kettle.py [-- --preview]
    python tools/blender/build_kettle.py [--preview]              # pip "bpy" module

Outputs  assets/models/kettle.glb (two roots) · assets/source/kettle/kettle.blend (+ preview.png)
Contract KettleRoot (origin = centre of the foot ring) · SteamAnchor (spout mouth) · Body · Handle ·
         optional Lid / Spout · material KettleIron (heat glow, cloned per instance)
         KettleStandRoot (origin = ground centre) · RestAnchor (top of the ring = where the kettle foot sits)
         (see src/assets/ModelRegistry.js)

A well-used 12 L cast-iron camp ("gypsy") kettle, Ø 0.36 m, spout toward Blender +X (glTF +X, the direction the steam leaves),
seen side-on from the front (−Y): foot ring, belly with a casting flange, domed shoulder, rolled neck,
lid with a turned knob, tapered spout with a thick lip, two cast lugs carrying a forged bail with a
charred wooden grip. The stand is a forged four-leg pot stand: a ring on bent arms and splayed legs with
a brace hoop and flattened feet. Its legs sit at 22.5° + k·90° (in the scene's X/Z), i.e. between the
eight teepee logs, which lie at k·45°.

Both share one baked atlas (UV1): seasoned black iron with bare-metal wear on edges and the bail,
oxide patches, heavy soot on the kettle bottom and on the stand's ring (it sits in the flames).
In the .blend the kettle sits on the stand; at runtime every root is placed by the scene.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402  (imports bpy first)
import bpy                       # noqa: E402
from mathutils import Matrix, Vector     # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'kettle.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'kettle')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv

IRON = '#2b2926'
K = 1.3                                 # kettle profiles below are drawn for a Ø 0.27 m pot; built at Ø 0.36 m
                                        # (a 12 L "gypsy" kettle — anything smaller vanishes in this fire's flames)
RING_R, RING_BAR = 0.098 * K, 0.0075    # stand ring (under the kettle's foot bead)
REST_Z = 0.5805 + RING_BAR              # top of the ring: kettle foot contact
LEG_BAR = 0.0065
FOOT_R = 0.80                           # feet inside the stone ring
LEG_ANGLES = [22.5, 112.5, 202.5, 292.5]    # scene angles (X/Z plane), between the teepee logs

C.reset()
kroot = C.empty('KettleRoot', size=0.1)
sroot = C.empty('KettleStandRoot', size=0.2)


def tag(ob, hexcol, rough, metal):
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    ob['cf_metal'] = metal
    return ob


def place(ob, m):
    ob.data.transform(m)
    return ob


# ------------------------------------------------------------------ kettle (built around its own origin)
body = [tag(C.lathe('Shell', [
    (0.0, 0.004), (0.090, 0.004), (0.097, 0.0), (0.103, 0.002), (0.1065, 0.008), (0.104, 0.013),   # foot bead
    (0.109, 0.016), (0.120, 0.029), (0.1275, 0.047), (0.1305, 0.064),
    (0.1365, 0.066), (0.1375, 0.0705), (0.1305, 0.073),                                          # casting flange
    (0.1295, 0.092), (0.125, 0.113), (0.116, 0.132), (0.101, 0.148), (0.085, 0.158), (0.074, 0.163),
    (0.0725, 0.169), (0.0765, 0.1725), (0.0745, 0.1765), (0.067, 0.175), (0.065, 0.166)          # rolled neck
], 40), IRON, 0.62, 0.35)]
# cast lugs on the shoulder (±X, in the bail plane) with the bail holes
for s in (-1, 1):
    lug = C.rounded_box(f'Lug{"LR"[s > 0]}', (0.026, 0.010, 0.030), (s * 0.103, 0, 0.147),
                        normal=(0, -1, 0), tangent=(0, 0, 1), p=3.0, res=3)
    place(lug, Matrix.Translation((s * 0.103, 0, 0.147)) @ Matrix.Rotation(s * math.radians(-38), 4, 'Y')
          @ Matrix.Translation((-s * 0.103, 0, -0.147)))
    body.append(tag(lug, IRON, 0.62, 0.35))

spout = C.sweep('Spout', C.catmull([
    (0.095, 0, 0.050), (0.132, 0, 0.058), (0.166, 0, 0.083), (0.190, 0, 0.118), (0.203, 0, 0.152), (0.209, 0, 0.170)
], 4), [0.027, 0.026, 0.024, 0.022, 0.021, 0.019, 0.018, 0.0165, 0.015, 0.0142, 0.0135, 0.013,
        0.0125, 0.012, 0.0118, 0.0115, 0.0112, 0.011, 0.0108, 0.0106, 0.0105], sides=14, cap_start=True)
C.solidify(spout, 0.0028, offset=-1.0)
C.apply_modifiers(spout)
tag(spout, IRON, 0.62, 0.35)

lid = [tag(C.lathe('LidDome', [
    (0.066, 0.168), (0.070, 0.1745), (0.0755, 0.1778), (0.0735, 0.1815), (0.060, 0.188), (0.042, 0.1935),
    (0.022, 0.1962), (0.0, 0.1968)
], 40), IRON, 0.62, 0.35),
    tag(C.lathe('LidKnob', [
        (0.0, 0.195), (0.009, 0.1955), (0.0125, 0.201), (0.0155, 0.210), (0.0135, 0.217), (0.0075, 0.2205), (0.0, 0.221)
    ], 20), IRON, 0.62, 0.35)]

# forged bail: through both lugs, flattened arch over the top (in the X/Z plane, like the spout)
PIV_Z, BAIL_TOP = 0.150, 0.325
arch = []
for i in range(33):
    t = math.pi * i / 32
    c, sn = math.cos(t), math.sin(t)
    arch.append((math.copysign(abs(c) ** (2 / 3.2), c) * 0.116, 0, PIV_Z + abs(sn) ** (2 / 3.2) * (BAIL_TOP - PIV_Z)))
arch = [(-0.100, 0, PIV_Z - 0.004)] + arch[::-1] + [(0.100, 0, PIV_Z - 0.004)]
bail = tag(C.curve_tube('BailWire', arch, 0.0042, sides=8), IRON, 0.55, 0.6)
grip = C.lathe('Grip', [(0.0, -0.047), (0.0085, -0.046), (0.0115, -0.040), (0.0125, -0.020), (0.0128, 0.0),
                        (0.0125, 0.020), (0.0115, 0.040), (0.0085, 0.046), (0.0, 0.047)], 12)
place(grip, Matrix.Translation((0, 0, BAIL_TOP)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))

for o in body + [spout] + lid + [bail, grip]:
    o.data.transform(Matrix.Scale(K, 4))   # bake the size into the mesh: roots stay at scale 1

# ------------------------------------------------------------------ stand (world = its own origin)
stand = []
ring = [(RING_R * math.cos(2 * math.pi * i / 48), RING_R * math.sin(2 * math.pi * i / 48), 0.5805) for i in range(49)]
stand.append(tag(C.curve_tube('StandRing', ring, RING_BAR, sides=8), '#1f1e1c', 0.7, 0.4))
LEG = [(RING_R, 0.5805), (0.165, 0.583), (0.235, 0.570), (0.300, 0.532), (0.540, 0.282), (FOOT_R - 0.02, 0.028), (FOOT_R, 0.012)]
brace_r = None
for deg in LEG_ANGLES:
    a = -math.radians(deg)                          # scene (x, z) angle → Blender (x, −y)
    d = Vector((math.cos(a), math.sin(a), 0))
    pts = [tuple(d * r + Vector((0, 0, z))) for r, z in LEG]
    stand.append(tag(C.curve_tube(f'Leg{deg:g}', C.catmull(pts, 5), LEG_BAR, sides=6), '#1f1e1c', 0.7, 0.4))
    stand.append(tag(C.rounded_box(f'Foot{deg:g}', (0.030, 0.050, 0.007), d * FOOT_R + Vector((0, 0, 0.0035)),
                                   normal=(0, 0, 1), tangent=tuple(d), p=3.0, res=3), '#1f1e1c', 0.7, 0.4))
    stand.append(tag(C.rounded_box(f'Weld{deg:g}', (0.020, 0.024, 0.016), d * (RING_R + 0.004) + Vector((0, 0, 0.580)),
                                   normal=(0, 0, 1), tangent=tuple(d), p=2.4, res=3), '#1f1e1c', 0.7, 0.4))
brace_z = 0.30
# radius of the legs at brace_z on the straight run between (0.30, 0.532) and (0.54, 0.282)
brace_r = 0.30 + (0.532 - brace_z) / (0.532 - 0.282) * (0.54 - 0.30)
brace = [(brace_r * math.cos(2 * math.pi * i / 64), brace_r * math.sin(2 * math.pi * i / 64), brace_z) for i in range(65)]
stand.append(tag(C.curve_tube('BraceHoop', brace, 0.0050, sides=6), '#1f1e1c', 0.7, 0.4))

# ------------------------------------------------------------------ assemble, then bake in place
for o in body + [spout] + lid + [bail, grip]:
    o.parent = kroot
for o in stand:
    o.parent = sroot
C.empty('SteamAnchor', (0.212 * K, 0, 0.176 * K), kroot, size=0.02)
C.empty('RestAnchor', (0, 0, REST_Z), sroot, size=0.03)
kroot.location = (0, 0, REST_Z)             # kettle sits on the stand in the .blend (runtime resets it)
bpy.context.view_layer.update()

iron_parts = body + [spout] + lid + [bail] + stand
C.unwrap_uv1(iron_parts, uv0_tile=0.1)
base_p, orm_p = C.bake_weathering(iron_parts, 'kettle_iron', TEX, size=1024, dirt_height=0.0, fade=0.1,
                                  edge_wear=0.3, ao_distance=0.05, seed=17.0, metal=True,
                                  chips=0.5, chip_color='#5f5b55', rust=0.3,
                                  soot_top=(0.50, 0.58, 0.8), soot_bottom=(0.005, 0.07, 0.9))
M_IRON = C.baked_material('KettleIron', base_p, orm_p, None)
# same atlas, separate material: the kettle's copy gets the heat glow per instance (colour set at load time,
# ModelRegistry.kettle.prepare), the stand's never does
M_STAND = C.baked_material('StandIron', base_p, orm_p, None)
M_GRIP = C.pbr('KettleGrip', C.srgb('#2a1b12'), 0.78)

for o in body:
    C.set_material(o, M_IRON)
C.join(body, 'Body')
C.set_material(spout, M_IRON)
for o in lid:
    C.set_material(o, M_IRON)
C.join(lid, 'Lid')
C.set_material(bail, M_IRON)
C.set_material(grip, M_GRIP)
C.join([bail, grip], 'Handle')
for o in stand:
    C.set_material(o, M_STAND)
C.join(stand, 'Stand')

print(f'[kettle] triangles: {C.triangle_count()}')
print(f'[kettle] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[kettle] saved .blend ({C.save_blend(os.path.join(SRC, "kettle.blend")) / 1024:.0f} KB)')
if PREVIEW:
    C.preview(os.path.join(SRC, 'preview.png'), (0.9, -1.5, 0.95), (0, 0.0, 0.45), key_loc=(0.6, -1.2, 1.2))
    print('[kettle] preview rendered')
