"""
Campfire · Hurricane (kerosene) lantern asset build (Blender 4.x, bpy) — Stage 3

    blender --background --python tools/blender/build_lantern.py [-- --preview]
    python tools/blender/build_lantern.py [--preview]              # pip "bpy" module

Outputs  assets/models/lantern.glb · assets/source/lantern/lantern.blend (+ preview.png)
Contract LanternRoot (root) · LightAnchor · Glass · Flame (material LanternGlow) · optional BailPivot
         (see src/assets/ModelRegistry.js)

A well-used "cold blast" hurricane lantern, wick adjuster toward Blender −Y (glTF +Z):
stamped fuel fount with rolled foot and seam bead, two side air tubes that carry the frame up into the
chimney hood / air chamber, brass burner gallery with a flat-wick flame, bulbous clear globe inside a wire
guard, lift lever, bail on eye pivots (resting tilted back) and a hanging ring.
Enamel paint is baked once into UV1 with chipped edges (bare steel + rust rims), sun-faded tops, foot grime
and chimney soot; metal shows only where the paint is gone (ORM blue channel).

Shadow policy (userData.noCastShadow): the lamp's own point light sits a few cm inside the wire guard,
side tubes and bail — anything thin there would throw metre-long radial streaks across the ground, so only
the fount, burner and hood cast shadows (the fount masks the ground right below, as in reality).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402  (imports bpy first)
import bpy                       # noqa: E402
from mathutils import Matrix, Vector     # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'lantern.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'lantern')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv

PAINT = '#2b4560'        # faded cobalt enamel — a cool counterpoint to the warm flame
TUBE_X = 0.108           # side air tubes (centre line) — the lantern's defining silhouette
TUBE_R = 0.0085
FLAME_Z = 0.155          # LightAnchor: centre of the flame
BAIL_Z = 0.215           # bail eye pivots on the tubes
BAIL_TILT = -26          # degrees about X; negative leans the bail back (+Y), off the globe

C.reset()
root = C.empty('LanternRoot', size=0.1)


def tag(ob, hexcol, rough, metal=0.0):
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    ob['cf_metal'] = metal
    return ob


def place(ob, m):
    ob.data.transform(m)
    return ob


# ------------------------------------------------------------------ painted body (baked)
painted = []

# fuel fount: rolled foot, bulging wall, seam bead, stamped shoulder rising to the burner seat
painted.append(tag(C.lathe('Fount', [
    (0.0, 0.004), (0.080, 0.004), (0.088, 0.0), (0.094, 0.002), (0.097, 0.007), (0.095, 0.012),
    (0.098, 0.020), (0.102, 0.032), (0.1035, 0.043), (0.102, 0.052),
    (0.1045, 0.055), (0.1045, 0.060), (0.100, 0.063),
    (0.095, 0.070), (0.084, 0.080), (0.068, 0.089), (0.050, 0.095), (0.036, 0.097), (0.0, 0.097)
], 32), PAINT, 0.62))
# embossed ring on the shoulder (a stamping line, not a logo)
painted.append(tag(C.lathe('FountRib', [
    (0.0795, 0.0826), (0.0815, 0.0842), (0.0795, 0.0858)
], 32, smooth=True), PAINT, 0.62))

# chimney hood + air chamber + top cap
painted.append(tag(C.lathe('Hood', [
    (0.034, 0.237), (0.046, 0.240), (0.062, 0.247), (0.074, 0.257), (0.079, 0.266), (0.078, 0.272),
    (0.070, 0.276), (0.064, 0.279), (0.062, 0.290), (0.061, 0.298),
    (0.067, 0.300), (0.071, 0.304), (0.069, 0.309), (0.057, 0.315), (0.040, 0.319), (0.020, 0.321), (0.0, 0.3215)
], 32), PAINT, 0.62))
# inside of the hood (seen through the globe): soot black
painted.append(tag(C.lathe('HoodInner', [
    (0.0, 0.262), (0.030, 0.258), (0.034, 0.2375)
], 24), '#161310', 0.9))
# vent slots round the air chamber
for i in range(12):
    a = 2 * math.pi * (i + 0.5) / 12
    n = Vector((math.cos(a), math.sin(a), 0))
    painted.append(tag(C.rounded_box(f'Vent{i}', (0.009, 0.0045, 0.0016), n * 0.0615 + Vector((0, 0, 0.2885)),
                                     normal=n, tangent=(0, 0, 1), p=4.0, res=2), '#0e0d0c', 0.9))

# charred flat wick
painted.append(tag(C.rounded_box('Wick', (0.014, 0.0035, 0.008), (0, 0, 0.134), p=5.0, res=2), '#0c0a08', 0.95))

# side air tubes: from the fount wall up and into the air chamber (one mesh per side, painted, no shadow)
frame = []
for s in (-1, 1):
    path = C.catmull([
        (s * 0.097, 0, 0.022), (s * 0.106, 0, 0.040), (s * TUBE_X, 0, 0.075), (s * TUBE_X, 0, 0.150),
        (s * TUBE_X, 0, 0.222), (s * 0.103, 0, 0.250), (s * 0.090, 0, 0.270), (s * 0.072, 0, 0.283),
        (s * 0.058, 0, 0.289)
    ], 6)
    frame.append(tag(C.curve_tube(f'AirTube{"LR"[s > 0]}', path, TUBE_R, sides=8), PAINT, 0.62))
    # collar where the tube meets the fount, and the bail eye boss
    frame.append(tag(C.lathe(f'TubeCollar{"LR"[s > 0]}', [
        (0.0, 0.034), (0.012, 0.034), (0.0125, 0.040), (0.0105, 0.046), (0.0, 0.046)
    ], 12, loc=(s * 0.104, 0, 0)), PAINT, 0.62))
    frame.append(tag(C.rounded_box(f'BailBoss{"LR"[s > 0]}', (0.006, 0.014, 0.018),
                                   (s * (TUBE_X + TUBE_R), 0, BAIL_Z), normal=(s, 0, 0), tangent=(0, 0, 1),
                                   p=3.0, res=3), PAINT, 0.62))

# ------------------------------------------------------------------ bare wire (galvanised steel, no bake)
wire = []
# globe guard: four bowed bars from the gallery to the hood, plus a belt ring
for deg in (48, 132, 228, 312):
    a = math.radians(deg)
    d = Vector((math.cos(a), math.sin(a), 0))
    pts = [tuple(d * r + Vector((0, 0, z))) for r, z in
           ((0.055, 0.108), (0.070, 0.124), (0.081, 0.150), (0.084, 0.176), (0.080, 0.205), (0.072, 0.230), (0.070, 0.250))]
    wire.append(C.curve_tube(f'GuardBar{deg}', C.catmull(pts, 5), 0.0022, sides=6))
belt = [(0.0842 * math.cos(2 * math.pi * i / 48), 0.0842 * math.sin(2 * math.pi * i / 48), 0.176) for i in range(49)]
wire.append(C.curve_tube('GuardBelt', belt, 0.0019, sides=6))
# globe lift lever (right side): pivots on the tube, bent up to a thumb tab in front
lever = C.catmull([(TUBE_X - 0.004, -0.009, 0.120), (0.098, -0.030, 0.113), (0.080, -0.052, 0.110),
                   (0.062, -0.066, 0.109)], 5)
wire.append(C.curve_tube('LiftLever', lever, 0.0021, sides=6))
wire.append(C.rounded_box('LiftTab', (0.016, 0.011, 0.0025), (0.058, -0.070, 0.109), p=3.0, res=3))
# hanging ring on the top cap
ring = [(0.014 * math.sin(2 * math.pi * i / 24), 0, 0.3345 + 0.014 * math.cos(2 * math.pi * i / 24)) for i in range(25)]
wire.append(C.curve_tube('HangRing', ring, 0.0022, sides=6))
# bail eyes
for s in (-1, 1):
    eye = [(s * (TUBE_X + TUBE_R + 0.004), 0.0065 * math.cos(2 * math.pi * i / 16), BAIL_Z + 0.0065 * math.sin(2 * math.pi * i / 16))
           for i in range(17)]
    wire.append(C.curve_tube(f'BailEye{"LR"[s > 0]}', eye, 0.0017, sides=6))

# bail: flattened arch on its own pivot so it can swing (parts.bail)
bail_pivot = C.empty('BailPivot', (0, 0, BAIL_Z), root, size=0.03)
arch = []
for i in range(29):
    t = math.pi * i / 28
    c, sn = math.cos(t), math.sin(t)
    x = math.copysign(abs(c) ** (2 / 2.8), c) * (TUBE_X + TUBE_R + 0.004)
    z = abs(sn) ** (2 / 2.8) * 0.165
    arch.append((x, 0, z))
# the ends turn inward through the eyes
arch = [(-(TUBE_X + 0.004), 0, 0.0)] + arch[::-1] + [((TUBE_X + 0.004), 0, 0.0)]
bail = C.curve_tube('BailWire', arch, 0.0030, sides=6)
# wire grip crimp at the top of the arch
grip = C.lathe('BailGrip', [(0.0, -0.022), (0.0042, -0.020), (0.0048, 0.0), (0.0042, 0.020), (0.0, 0.022)], 10)
place(grip, Matrix.Translation((0, 0, 0.165)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))

# ------------------------------------------------------------------ brass (no bake)
brass = []
brass.append(C.lathe('Gallery', [
    (0.030, 0.094), (0.035, 0.097), (0.047, 0.101), (0.0535, 0.105), (0.0535, 0.1105), (0.0475, 0.1125),
    (0.041, 0.1125), (0.030, 0.1135), (0.022, 0.116), (0.0145, 0.127), (0.0115, 0.1315), (0.0, 0.1315)
], 32))
# perforated gallery: a ring of dark holes reads as air holes
for i in range(16):
    a = 2 * math.pi * (i + 0.5) / 16
    n = Vector((math.cos(a), math.sin(a), 0.35)).normalized()
    painted.append(tag(C.rounded_box(f'GalleryHole{i}', (0.0042, 0.0042, 0.0012),
                                     Vector((math.cos(a) * 0.050, math.sin(a) * 0.050, 0.1035)),
                                     normal=n, tangent=(0, 0, 1), p=2.2, res=2), '#0c0a08', 0.9))
# wick adjuster: shaft out to a knurled knob in front (−Y)
shaft = C.lathe('WickShaft', [(0.0, 0.0), (0.0025, 0.0), (0.0025, 0.050), (0.0, 0.050)], 10)
place(shaft, Matrix.Translation((0, -0.030, 0.1025)) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
brass.append(shaft)
knob = C.lathe('WickKnob', [(0.0, 0.0), (0.009, 0.0), (0.0125, 0.0015), (0.0128, 0.0055), (0.0105, 0.0072),
                            (0.004, 0.0078), (0.0, 0.0078)], 18)
place(knob, Matrix.Translation((0, -0.079, 0.1025)) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
brass.append(knob)
# filler cap on the shoulder (back right)
cap = C.lathe('FillerCap', [(0.0, 0.0), (0.0125, 0.0), (0.0125, 0.007), (0.0105, 0.0095), (0.0, 0.0105)], 20)
place(cap, Matrix.Translation((0.050, 0.046, 0.083)) @ Matrix.Rotation(math.radians(-18), 4, Vector((-1, 1, 0)).normalized()))
brass.append(cap)

# ------------------------------------------------------------------ materials, bake, assemble
C.unwrap_uv1(painted + frame, uv0_tile=0.1)
base_p, orm_p = C.bake_weathering(painted + frame, 'lantern_paint', TEX, size=1024, dirt_height=0.03, fade=0.3,
                                  edge_wear=0.25, ao_distance=0.04, seed=11.0,
                                  chips=1.25, chip_color='#6e6c66', soot_top=(0.255, 0.31, 0.75), metal=True)
M_PAINT = C.baked_material('LanternPaint', base_p, orm_p, None)
M_WIRE = C.pbr('LanternWire', C.srgb('#7d7b75'), 0.6, metal=1.0)
M_BRASS = C.pbr('LanternBrass', C.srgb('#8c6a36'), 0.45, metal=1.0)
M_GLOW = C.pbr('LanternGlow', C.srgb('#ffd9a0'), 0.4, emission=C.srgb('#ffb259'), emission_strength=2.4)

# glass (replaced at runtime by ModelRegistry.lantern.prepare; kept physically sensible for Blender)
M_GLASS = bpy.data.materials.new('LanternGlass')
M_GLASS.use_nodes = True
M_GLASS.use_backface_culling = True
M_GLASS.surface_render_method = 'BLENDED'
gb = M_GLASS.node_tree.nodes['Principled BSDF']
gb.inputs['Base Color'].default_value = (*C.srgb('#ffe2ae'), 1.0)
gb.inputs['Roughness'].default_value = 0.06
gb.inputs['Alpha'].default_value = 0.2
gb.inputs['Coat Weight'].default_value = 1.0
gb.inputs['Coat Roughness'].default_value = 0.05

for o in painted:
    C.set_material(o, M_PAINT)
body = C.join(painted, 'Body')
body.parent = root
for o in frame:
    C.set_material(o, M_PAINT)
fr = C.join(frame, 'Frame')
fr.parent = root
fr['noCastShadow'] = True
for o in wire:
    C.set_material(o, M_WIRE)
gd = C.join(wire, 'Guard')
gd.parent = root
gd['noCastShadow'] = True
for o in (bail, grip):
    C.set_material(o, M_WIRE)
bw = C.join([bail, grip], 'Bail')
bw.parent = bail_pivot
bw['noCastShadow'] = True
bail_pivot.rotation_euler = (math.radians(BAIL_TILT), 0, 0)
for o in brass:
    C.set_material(o, M_BRASS)
C.join(brass, 'Burner').parent = root

# globe: a single outward-facing shell (see ModelRegistry: an inner surface would face the flame and blow out)
glass = C.lathe('Glass', [
    (0.041, 0.1125), (0.050, 0.122), (0.061, 0.138), (0.0685, 0.158), (0.0705, 0.180), (0.0675, 0.203),
    (0.058, 0.222), (0.046, 0.233), (0.0355, 0.2385)
], 32)
C.set_material(glass, M_GLASS)
glass.parent = root
glass['noCastShadow'] = True

# flame: flat-wick fan (wide across X, thin in Y) with a brighter core, one emissive material
anchor = C.empty('LightAnchor', (0, 0, FLAME_Z), root, size=0.02)
outer = C.lathe('FlameOuter', [(0.0, 0.1375), (0.0065, 0.140), (0.0105, 0.147), (0.0115, 0.155),
                               (0.0092, 0.166), (0.005, 0.176), (0.0, 0.186)], 16)
place(outer, Matrix.Diagonal((1.0, 0.5, 1.0, 1.0)))
core = C.lathe('FlameCore', [(0.0, 0.1385), (0.0045, 0.141), (0.0065, 0.148), (0.0055, 0.156), (0.0, 0.164)], 12)
place(core, Matrix.Diagonal((1.0, 0.45, 1.0, 1.0)))
for o in (outer, core):
    C.set_material(o, M_GLOW)
flame = C.join([outer, core], 'Flame')
flame.parent = root
flame['noCastShadow'] = True

print(f'[lantern] triangles: {C.triangle_count()}')
print(f'[lantern] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[lantern] saved .blend ({C.save_blend(os.path.join(SRC, "lantern.blend")) / 1024:.0f} KB)')
if PREVIEW:
    C.preview(os.path.join(SRC, 'preview.png'), (0.42, -0.62, 0.34), (0, 0.0, 0.18), key_loc=(0.35, -0.9, 0.5))
    print('[lantern] preview rendered')
