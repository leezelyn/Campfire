"""
Campfire · Tent asset build script (Blender 4.x, bpy)
======================================================

Builds the camp tent as a DCC asset and exports the runtime model:

    blender --background --python tools/blender/build_tent.py
    # or, with the pip "bpy" module:
    python tools/blender/build_tent.py

Outputs
    assets/models/tent.glb            runtime asset (loaded by src/assets/AssetManager.js)
    assets/source/tent/tent.blend     editable source (textures packed)

Standards (docs/asset-pipeline.md)
    Blender Z-up / glTF Y-up, 1 unit = 1 m, front of the tent faces Blender -Y (= glTF +Z),
    origin = ground centre, root scale 1 / rotation 0.

Contract (src/assets/ModelRegistry.js · tent)
    TentRoot               root empty
    Door                   door flap group (rolled flap + ties)
    InteriorLightAnchor    position of the in-tent warm point light (glTF (0, 0.5, 0.675))

Materials (PBR, docs/art-direction.md)
    TentCanvas   baked base colour (UV1: sun fade, mud splash, rain streaks, soot, crease grime)
                 + packed ORM (UV1: AO / roughness / metal) + tiling canvas-weave normal (UV0)
    TentTrim     seam binding / hems / zipper tape
    InnerFabric  breathable inner tent, TentFloor bathtub floor
    PoleMetal    anodised aluminium poles + steel pegs
    Cordage      guy lines, ties, toggles
    SleepingBag  lived-in interior, LampBody / LampGlow small hanging lamp
"""
import math
import os
import sys

import bpy          # must come first: with the pip "bpy" module, bmesh/mathutils become importable after it
import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT_GLB = os.path.join(REPO, 'assets', 'models', 'tent.glb')
SRC_DIR = os.path.join(REPO, 'assets', 'source', 'tent')
TEX_DIR = os.path.join(SRC_DIR, 'textures')
PREVIEW = '--preview' in sys.argv          # also render a Cycles preview PNG next to the .blend

# ---------------------------------------------------------------- dimensions (m)
W = 1.60          # width at the end walls (eave to eave)
D = 1.95          # length (back +Y → front −Y)
H = 1.08          # ridge height at the poles
FLARE = 0.13      # eaves bow outward mid-length (pegged side panels)
EAVE_Z = 0.035    # fly hem sits just above the ground (ventilation gap)
RIDGE_SAG = 0.035
PANEL_SAG = 0.075
THICK = 0.003     # canvas thickness (solidified, visible at hems and the door edge)
DOOR_BOTTOM = 0.29   # half width of the door opening at the ground
DOOR_TOP = 0.15      # half width at the top of the opening
DOOR_H = 0.70
ANCHOR = Vector((0.0, -(D / 2 - 0.30), 0.50))   # glTF (0, 0.5, 0.675): same as the v1 in-tent light
WEAVE_TILE_M = 0.15                              # UV0: one weave tile per 15 cm (~2.9 mm thread pitch)


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
os.makedirs(TEX_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)


def link(obj, parent=None):
    scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def mesh_object(name, verts, faces, uv0=None, parent=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate(clean_customdata=False)
    me.update()
    if uv0 is not None:
        layer = me.uv_layers.new(name='UV0')
        loops = np.empty(len(me.loops), dtype=np.int32)
        me.loops.foreach_get('vertex_index', loops)
        uv = np.asarray(uv0, dtype=np.float32)[loops]
        layer.data.foreach_set('uv', uv.ravel())
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    obj = bpy.data.objects.new(name, me)
    return link(obj, parent)


def empty(name, loc=(0, 0, 0), parent=None, size=0.1):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = size
    e.location = loc
    return link(e, parent)


def weld(obj, dist=1e-5):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
    bm.to_mesh(obj.data)
    bm.free()


def apply_modifiers(obj):
    """Bake the modifier stack into the mesh (no operator context needed)."""
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.clear()
    obj.data = new
    new.name = old.name
    bpy.data.meshes.remove(old)


def join(objs, name):
    """Join meshes (keeps UV layers by name)."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def curve_tube(name, pts, radius, parent=None, sides=6):
    """Polyline → bevelled curve → mesh (ropes, binding tape, poles)."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = max(0, sides // 2 - 2)
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (q[0], q[1], q[2], 1.0)
    ob = bpy.data.objects.new(name + '_curve', cu)
    link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.name = name
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    return link(bpy.data.objects.new(name, me), parent)


# ---------------------------------------------------------------- canvas surface functions
SLOPE = math.hypot(W / 2, H)


def ridge_z(v):
    return H - RIDGE_SAG * math.sin(math.pi * v)


def eave_x(v, s):
    return s * (W / 2 + FLARE * math.sin(math.pi * v))


def fold_fan(a, b, ax, ay, amp, n, decay, phase):
    """Tension folds radiating from an anchor (pole top / guy-out / peg) in panel metres."""
    dx, dy = a - ax, b - ay
    rho = math.hypot(dx, dy)
    if rho < 1e-6:
        return 0.0
    phi = math.atan2(dy, dx)
    return amp * math.sin(n * phi + phase) * math.exp(-rho / decay) * (1 - math.exp(-rho / 0.07))


def roof_point(u, v, s, folds=True, sag=PANEL_SAG):
    """Side panel s=±1, u: eave 0 → ridge 1, v: back 0 → front 1 (Blender y = D/2 − vD)."""
    y = D / 2 - v * D
    e = Vector((eave_x(v, s), y, EAVE_Z))
    r = Vector((0.0, y, ridge_z(v)))
    p = e.lerp(r, u)
    slope = (r - e).normalized()
    outward = slope.cross(Vector((0, -1 if s > 0 else 1, 0))).normalized()
    if outward.z < 0:
        outward = -outward
    disp = -sag * math.sin(math.pi * u) * (0.35 + 0.65 * math.sin(math.pi * v))
    if folds:
        a, b = u * SLOPE, v * D
        f = (fold_fan(a, b, SLOPE, 0.0, 0.024, 12, 0.8, 0.6 * s)           # back pole top
             + fold_fan(a, b, SLOPE, D, 0.024, 12, 0.8, 1.9 * s)           # front pole top
             + fold_fan(a, b, 0.55 * SLOPE, D / 2, 0.013, 9, 0.4, 0.4)     # side guy-out point
             + fold_fan(a, b, 0.0, 0.0, 0.008, 10, 0.3, 2.2)               # corner pegs
             + fold_fan(a, b, 0.0, D, 0.008, 10, 0.3, 0.9)
             + fold_fan(a, b, 0.0, D / 2, 0.009, 10, 0.3, 1.3)             # mid eave peg
             + 0.005 * math.sin(a * 7.3 + b * 3.1 + s) * math.sin(b * 5.7 - a * 2.3))
        env = (smoothstep(0, 0.06, u) * smoothstep(0, 0.05, 1 - u)
               * smoothstep(0, 0.035, v) * smoothstep(0, 0.035, 1 - v))
        disp += f * env
    return p + outward * disp


def build_roof(name, s, nu, nv, folds=True, sag=PANEL_SAG, scale=1.0, parent=None):
    verts, uv0, faces = [], [], []
    for j in range(nv + 1):
        v = j / nv
        for i in range(nu + 1):
            u = i / nu
            verts.append(roof_point(u, v, s, folds, sag) * scale)
            uv0.append(((u * SLOPE) / WEAVE_TILE_M, (v * D) / WEAVE_TILE_M))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            b, c, d = a + 1, a + nu + 1, a + nu + 2
            faces.append((a, b, d, c) if s > 0 else (a, c, d, b))
    return mesh_object(name, verts, faces, uv0, parent)


def build_end_wall(name, front, nt, nw, folds=True, roof_sag=PANEL_SAG, sag=0.03, scale=1.0, parent=None):
    """Triangle wall whose sloped edges coincide with the roof panel end edges."""
    v = 1.0 if front else 0.0
    inward = 1.0 if front else -1.0         # front wall at −Y sags toward +Y and vice versa
    verts, uv0, faces = [], [], []
    for j in range(nt + 1):
        t = j / nt
        left = roof_point(t, v, -1, folds, roof_sag)
        right = roof_point(t, v, +1, folds, roof_sag)
        for i in range(nw + 1):
            w = i / nw
            p = left.lerp(right, w)
            bulge = sag * math.sin(math.pi * w) * math.sin(math.pi * min(1.0, t * 1.15))
            if folds:
                # folds fanning down from the apex pole tip
                ang = (w - 0.5) * math.pi
                bulge += (0.010 * math.sin(10 * ang + (0.7 if front else 2.1))
                          * math.exp(-(1 - t) * H / 0.6) * smoothstep(0.0, 0.12, 1 - t)
                          * math.sin(math.pi * w))
            p.y += inward * bulge
            verts.append(p * scale)
            uv0.append(((w - 0.5) * W / WEAVE_TILE_M, p.z / WEAVE_TILE_M))
    for j in range(nt):
        for i in range(nw):
            a = j * (nw + 1) + i
            b, c, d = a + 1, a + nw + 1, a + nw + 2
            faces.append((a, b, d, c) if front else (a, c, d, b))     # outward: front −Y, back +Y
    ob = mesh_object(name, verts, faces, uv0, parent)
    weld(ob)                                  # collapse the degenerate apex row
    return ob


def door_cutter(name, bottom, top, height, y, depth=0.6):
    """Trapezoid prism (x-z outline, extruded along y) for the door boolean."""
    outline = [(-bottom, -0.1), (bottom, -0.1), (top, height), (-top, height)]
    verts = [(x, y - depth / 2, z) for x, z in outline] + [(x, y + depth / 2, z) for x, z in outline]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return mesh_object(name, verts, faces, None, None, smooth=False)


def cut_door(wall, cutter):
    mod = wall.modifiers.new('DoorCut', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    apply_modifiers(wall)
    bpy.data.objects.remove(cutter)


def solidify(obj, thickness, offset=-1.0):
    mod = obj.modifiers.new('Canvas', 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = offset
    mod.use_even_offset = True
    mod.use_rim = True
    mod.use_quality_normals = True
    apply_modifiers(obj)


# ---------------------------------------------------------------- materials
def image_node(nt, img, uv_name, non_color=False, loc=(-600, 0)):
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    tex.location = loc
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    uvn = nt.nodes.new('ShaderNodeUVMap')
    uvn.uv_map = uv_name
    uvn.location = (loc[0] - 220, loc[1])
    nt.links.new(uvn.outputs['UV'], tex.inputs['Vector'])
    return tex


def gltf_output_group():
    """Custom node group recognised by the glTF exporter for the occlusion channel."""
    g = bpy.data.node_groups.get('glTF Material Output')
    if g:
        return g
    g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
    g.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    g.nodes.new('NodeGroupInput')
    return g


def pbr_material(name, color, rough, metal=0.0, normal_img=None, normal_uv='UV0', normal_strength=0.5,
                 cull=True, emission=None, emission_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = cull
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emission is not None:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    if normal_img is not None:
        tex = image_node(nt, normal_img, normal_uv, non_color=True, loc=(-500, -400))
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.uv_map = normal_uv
        nm.inputs['Strength'].default_value = normal_strength
        nm.location = (-200, -400)
        nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return m


def srgb(hexstr):
    c = [int(hexstr[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ---------------------------------------------------------------- tiling canvas weave normal (numpy)
def make_weave_normal(size=512, period=10, seed=7):
    """Tileable plain-weave canvas: warp/weft threads undulate over and under each other."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    cx, cy = np.floor(x / period), np.floor(y / period)
    fx, fy = (x % period) / period, (y % period) / period
    prof_w = np.clip(np.cos(np.pi * (fx - 0.5)), 0, 1) ** 0.7       # round thread cross-sections
    prof_f = np.clip(np.cos(np.pi * (fy - 0.5)), 0, 1) ** 0.7
    # each warp thread goes over/under alternate wefts (phase flips between neighbouring threads)
    h_warp = prof_w * (0.5 + 0.5 * np.sin(np.pi * y / period + np.pi * cx))
    h_weft = prof_f * (0.5 + 0.5 * np.sin(np.pi * x / period + np.pi * cy + np.pi))
    nthreads = size // period
    tw = rng.normal(1.0, 0.1, nthreads + 1)[cx.astype(int)]         # slubs: thread thickness varies
    tf = rng.normal(1.0, 0.1, nthreads + 1)[cy.astype(int)]
    h = np.maximum(h_warp * tw, h_weft * tf)
    lf = np.zeros_like(h)                                            # low-frequency cloth irregularity
    for k, a in ((2, 0.25), (5, 0.12), (13, 0.05)):
        ph = rng.uniform(0, 2 * np.pi, 3)
        lf += a * (np.sin(2 * np.pi * k * x / size + ph[0]) * np.sin(2 * np.pi * k * y / size + ph[1])
                   + 0.5 * np.sin(2 * np.pi * k * (x - y) / size + ph[2]))
    h = h * 0.6 + lf
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    k = 1.6
    n = np.stack([-dx * k, -dy * k, np.ones_like(h)], -1)   # Blender pixel rows run bottom→top (+V): OpenGL / glTF convention
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rgb = n * 0.5 + 0.5
    img = bpy.data.images.new('TentWeaveNormal', size, size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    px = np.concatenate([rgb, np.ones((size, size, 1), np.float32)], -1)
    img.pixels.foreach_set(px.astype(np.float32).ravel())
    path = os.path.join(TEX_DIR, 'tent_weave_normal.png')
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    return bpy.data.images.load(path, check_existing=False)


# ---------------------------------------------------------------- build
root = empty('TentRoot', size=0.3)
weave = make_weave_normal()

# -- fly (outer canvas)
fly_parts = [
    build_roof('FlyRoofL', -1, 28, 48),
    build_roof('FlyRoofR', +1, 28, 48),
    build_end_wall('FlyBack', False, 28, 30),
]
front = build_end_wall('FlyFront', True, 28, 30)
cut_door(front, door_cutter('FlyDoorCut', DOOR_BOTTOM, DOOR_TOP, DOOR_H, -D / 2))
fly_parts.append(front)
from mathutils.bvhtree import BVHTree
_bvh = BVHTree.FromObject(front, bpy.context.evaluated_depsgraph_get())


def front_surface_y(x, z):
    """y of the (bulging) front wall at (x, z), found by casting a ray along +Y."""
    hit = _bvh.ray_cast(Vector((x, -D / 2 - 0.5, z)), Vector((0, 1, 0)))
    return hit[0].y if hit[0] is not None else -D / 2


def door_outline_pts(inset=0.012, n=14):
    corners = [(-DOOR_BOTTOM - inset, EAVE_Z), (-DOOR_TOP - inset, DOOR_H + inset),
               (DOOR_TOP + inset, DOOR_H + inset), (DOOR_BOTTOM + inset, EAVE_Z)]
    pts = []
    for (x0, z0), (x1, z1) in zip(corners[:-1], corners[1:]):
        for k in range(n):
            x, z = x0 + (x1 - x0) * k / n, z0 + (z1 - z0) * k / n
            pts.append((x, front_surface_y(x, z) - 0.003, z))
    x, z = corners[-1]
    pts.append((x, front_surface_y(x, z) - 0.003, z))
    return pts
fly = join(fly_parts, 'Fly')
weld(fly, 2e-4)
solidify(fly, THICK)
fly.parent = root

# -- seam binding / hems / zipper tape (TentTrim)
trim = []
N = 48
trim.append(curve_tube('TrimRidge', [(0, D / 2 - v * D, ridge_z(v) + 0.006) for v in np.linspace(0, 1, N)], 0.009))
for front_end in (False, True):
    v = 1.0 if front_end else 0.0
    for s in (-1, 1):
        pts = [roof_point(t, v, s) for t in np.linspace(0, 1, 26)]
        trim.append(curve_tube(f'TrimEdge{"F" if front_end else "B"}{"R" if s > 0 else "L"}', pts, 0.0075))
for s in (-1, 1):   # bottom hems
    trim.append(curve_tube(f'TrimHem{"R" if s > 0 else "L"}',
                           [roof_point(0.004, v, s) for v in np.linspace(0, 1, 40)], 0.006))
trim.append(curve_tube('TrimDoorZip', door_outline_pts(), 0.007))
fly_trim = join(trim, 'FlyTrim')
fly_trim.parent = root

# -- door: rolled flap tied above the opening + two ties with wooden toggles
DOOR_Y = front_surface_y(0.0, DOOR_H + 0.03) - 0.034      # roll rests against the wall above the opening
door = empty('Door', (0, DOOR_Y, DOOR_H + 0.03), root)
roll_len = DOOR_TOP * 2 + 0.16
# rolled canvas flap: flattened roll that sags between the two ties, with rippled layers along its length
RR, RL = 16, 28
rverts, rfaces = [], []
for j in range(RL + 1):
    x = (j / RL - 0.5) * roll_len
    bow = 0.014 * (1 - (2 * x / roll_len) ** 2)                  # hangs lower between the ties
    taper = 0.8 + 0.2 * math.sin(math.pi * j / RL) ** 0.4          # ends slightly thinner (loose layers)
    for i in range(RR):
        a = 2 * math.pi * i / RR
        ripple = 1 + 0.1 * math.sin(x * 55 + a * 2) + 0.05 * math.sin(x * 130 + a * 3)
        r = 0.03 * taper * ripple
        rverts.append((x, math.cos(a) * r * 0.72, math.sin(a) * r - bow))
for j in range(RL):
    for i in range(RR):
        a0, a1 = j * RR + i, j * RR + (i + 1) % RR
        rfaces.append((a0, a0 + RR, a1 + RR, a1))
rfaces.append(tuple(range(RR)))                                     # end caps
rfaces.append(tuple(reversed(range(RL * RR, RL * RR + RR))))
roll = mesh_object('DoorRoll', rverts, rfaces, [(v[0] / WEAVE_TILE_M, math.atan2(v[2], v[1]) * 0.03 / WEAVE_TILE_M) for v in rverts])
roll.parent = door
roll.location = (0, 0, 0)
ties = []
for sx in (-1, 1):
    x = sx * (roll_len / 2 - 0.05)
    wy = front_surface_y(x, DOOR_H + 0.12) - 0.002
    z0 = DOOR_H + 0.03
    pts = [(x, wy, z0 + 0.09), (x, DOOR_Y - 0.02, z0 + 0.045), (x, DOOR_Y - 0.04, z0),
           (x, DOOR_Y - 0.02, z0 - 0.045), (x, DOOR_Y - 0.005, z0 - 0.15)]
    ties.append(curve_tube(f'DoorTie{"R" if sx > 0 else "L"}', pts, 0.004))
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.007, depth=0.045,
                                        location=(x, DOOR_Y - 0.005, z0 - 0.155), rotation=(0, math.pi / 2, 0))
    tog = bpy.context.active_object
    tog.name = f'DoorToggle{"R" if sx > 0 else "L"}'
    ties.append(tog)
door_ties = join(ties, 'DoorTies')
bpy.context.view_layer.update()
door_ties.parent = door
door_ties.matrix_parent_inverse = door.matrix_world.inverted()

# -- inner tent + bathtub floor (seen through the door, lit by the interior lamp)
inner_scale = 0.9
inner_parts = [
    build_roof('InnerL', -1, 12, 20, folds=False, sag=0.03, scale=inner_scale),
    build_roof('InnerR', +1, 12, 20, folds=False, sag=0.03, scale=inner_scale),
    build_end_wall('InnerBack', False, 12, 14, folds=False, roof_sag=0.03, sag=0.02, scale=inner_scale),
]
inner_front = build_end_wall('InnerFront', True, 12, 14, folds=False, roof_sag=0.03, sag=0.02, scale=inner_scale)
# inner door slightly wider than the fly door's projection: looking in, the view goes straight to the interior
cut_door(inner_front, door_cutter('InnerDoorCut', DOOR_BOTTOM * 1.08, DOOR_TOP * 1.12, DOOR_H * 0.97, -D / 2 * inner_scale))
inner_parts.append(inner_front)
inner = join(inner_parts, 'InnerTent')
weld(inner, 2e-4)
inner.parent = root
fw, fd = W * inner_scale / 2 - 0.02, D * inner_scale / 2 - 0.02
floor = mesh_object('TentFloor', [
    (-fw, -fd, 0.004), (fw, -fd, 0.004), (fw, fd, 0.004), (-fw, fd, 0.004),
    (-fw, -fd, 0.07), (fw, -fd, 0.07), (fw, fd, 0.07), (-fw, fd, 0.07)],
    [(0, 1, 2, 3), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
    [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (1, 0), (1, 1), (0, 1)], root, smooth=False)

# -- poles: A-frames at both ends (inside the fly), rubber-capped pins through the apex
poles = []
for end in (-1, 1):
    y = end * (D / 2 - 0.035)
    for s in (-1, 1):
        poles.append(curve_tube(f'Pole{end}{s}', [(s * (W / 2 - 0.13), y, 0.0), (0, y, H - 0.03)], 0.0095, sides=8))
    poles.append(curve_tube(f'PolePin{end}', [(0, end * D / 2, H - 0.05), (0, end * D / 2, H + 0.045)], 0.004))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.013, location=(0, end * D / 2, H + 0.045))
    cap = bpy.context.active_object
    cap.name = f'PoleCap{end}'
    poles.append(cap)

# -- guy lines with tensioners, pegs (front/back from the apex, sides from the guy-out points)
ropes, pegs = [], []


def peg_at(p, lean_dir):
    x, y = p[0], p[1]
    lx, ly = lean_dir
    shaft = curve_tube('PegShaft', [(x - lx * 0.06, y - ly * 0.06, -0.14), (x, y, 0.035), (x + lx * 0.03, y + ly * 0.03, 0.04)],
                       0.0032, sides=6)
    pegs.append(shaft)


def guy(a, b):
    a, b = Vector(a), Vector(b)
    mid = a.lerp(b, 0.5) - Vector((0, 0, 0.012 * (a - b).length))   # slight catenary
    ropes.append(curve_tube('Guy', [a, a.lerp(mid, 0.5), mid, mid.lerp(b, 0.5), b], 0.0026, sides=6))
    t = b + (a - b).normalized() * 0.16                                 # plastic tensioner near the peg
    bpy.ops.mesh.primitive_cube_add(size=1, location=t)
    ten = bpy.context.active_object
    ten.scale = (0.012, 0.012, 0.03)
    ten.rotation_mode = 'QUATERNION'
    ten.rotation_quaternion = Vector((0, 0, 1)).rotation_difference((a - b).normalized())
    ropes.append(ten)
    peg_at(b, tuple((b - a).normalized()[:2]))


for end in (-1, 1):
    guy((0, end * (D / 2 + 0.005), H + 0.035), (0, end * (D / 2 + 0.66), 0.0))
for s in (-1, 1):
    p = roof_point(0.56, 0.5, s)
    guy(tuple(p), (s * (W / 2 + FLARE + 0.52), 0.0, 0.0))
for s in (-1, 1):          # hem pegs: corners + mid eave, short webbing loop to the peg
    for v in (0.0, 0.5, 1.0):
        e = roof_point(0.0, v, s)
        pg = (e.x + s * 0.07, e.y + (0.05 if v == 0 else -0.05 if v == 1 else 0), 0.0)
        ropes.append(curve_tube('HemLoop', [(e.x, e.y, e.z + 0.01), (pg[0], pg[1], 0.035)], 0.004))
        peg_at(pg, (s, 0.0))

pole_obj = join(poles, 'Poles')
pole_obj.parent = root
guy_obj = join(ropes, 'GuyLines')
guy_obj.parent = root
guy_obj['noCastShadow'] = True          # thin lines: avoid hard streak shadows from the fire point light
peg_obj = join(pegs, 'Pegs')
peg_obj.parent = root

# -- lived-in interior: sleeping bag + pillow, small hanging lamp at the light anchor
bag_verts, bag_faces = [], []
NL, NR = 36, 16
for j in range(NL + 1):
    t = j / NL
    y = (D * inner_scale / 2 - 0.08) - t * 1.75
    half_w = 0.33 - 0.1 * t ** 1.5
    hgt = 0.11 + 0.03 * math.sin(math.pi * min(1, t * 1.3)) + 0.012 * math.cos(2 * math.pi * t * 9)   # quilted baffles
    for i in range(NR):
        a = 2 * math.pi * i / NR
        x = math.cos(a) * half_w
        z = max(0.0, math.sin(a)) * hgt + 0.008 + (0.012 if math.sin(a) < 0 else 0) * 0
        bag_verts.append((x + 0.12 + 0.05 * t, y, z + 0.004))
for j in range(NL):
    for i in range(NR):
        a = j * NR + i
        b = j * NR + (i + 1) % NR
        bag_faces.append((a, b, b + NR, a + NR))
bag_faces.append(tuple(reversed(range(NR))))                     # closed head / foot ends
bag_faces.append(tuple(range(NL * NR, NL * NR + NR)))
bag = mesh_object('SleepingBag', bag_verts, bag_faces, None, root)
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.2, location=(-0.12, D * inner_scale / 2 - 0.22, 0.06))
pillow = bpy.context.active_object
pillow.name = 'Pillow'
pillow.scale = (1.0, 0.55, 0.28)
pillow.rotation_euler = (0, 0, 0.18)
bpy.ops.object.shade_smooth()
pillow.parent = root

anchor = empty('InteriorLightAnchor', tuple(ANCHOR), root, size=0.05)
lamp_parts = [curve_tube('LampCord', [(0, ANCHOR.y, ridge_z(0.85) * inner_scale - 0.02), (0, ANCHOR.y, ANCHOR.z + 0.05)], 0.0015)]
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.028, depth=0.02, location=(0, ANCHOR.y, ANCHOR.z + 0.045))
lamp_parts.append(bpy.context.active_object)
lamp_body = join(lamp_parts, 'InteriorLampBody')
lamp_body.parent = root
lamp_body['noCastShadow'] = True
bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=8, radius=0.03, location=tuple(ANCHOR))
glow = bpy.context.active_object
glow.name = 'InteriorLampGlow'
glow.scale = (1, 1, 1.25)
bpy.ops.object.shade_smooth()
glow.parent = root
glow['noCastShadow'] = True

# ---------------------------------------------------------------- materials & baking
M_TRIM = pbr_material('TentTrim', srgb('#2f372c'), 0.82)
M_INNER = pbr_material('InnerFabric', srgb('#9c8a6c'), 0.9, normal_img=weave, normal_strength=0.25, cull=False)
M_FLOOR = pbr_material('TentFloor', srgb('#2b2d29'), 0.62, cull=False)
M_METAL = pbr_material('PoleMetal', srgb('#4a4d50'), 0.4, metal=1.0)
M_CORD = pbr_material('Cordage', srgb('#9c8b66'), 0.93)
M_BAG = pbr_material('SleepingBag', srgb('#5b3a2c'), 0.66)
M_LAMP = pbr_material('LampBody', srgb('#26282a'), 0.5)
M_GLOW = pbr_material('LampGlow', srgb('#ffd79a'), 0.4, emission=srgb('#ffb866'), emission_strength=2.5)

for ob, m in ((fly_trim, M_TRIM), (inner, M_INNER), (floor, M_FLOOR), (pole_obj, M_METAL), (peg_obj, M_METAL),
              (guy_obj, M_CORD), (door_ties, M_CORD), (bag, M_BAG), (pillow, M_BAG), (lamp_body, M_LAMP),
              (glow, M_GLOW), (roll, None)):
    if m is None:
        continue
    ob.data.materials.clear()
    ob.data.materials.append(m)

# UV1: unique unwrap of the canvas (fly + door roll share the baked canvas material)
for ob in (fly, roll):
    me = ob.data
    if 'UV0' not in me.uv_layers:
        if len(me.uv_layers):
            me.uv_layers[0].name = 'UV0'
        else:
            me.uv_layers.new(name='UV0')
    uv1 = me.uv_layers.new(name='UV1')
    me.uv_layers.active = uv1
bpy.ops.object.select_all(action='DESELECT')
for ob in (fly, roll):
    ob.select_set(True)
bpy.context.view_layer.objects.active = fly
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.006, scale_to_bounds=True)
bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
for ob in (fly, roll):
    ob.data.uv_layers['UV0'].active_render = True

BAKE = 1024
img_base = bpy.data.images.new('TentCanvas_BaseColor', BAKE, BAKE, alpha=False)
img_rough = bpy.data.images.new('TentCanvas_Rough', BAKE, BAKE, alpha=False)
img_rough.colorspace_settings.name = 'Non-Color'
img_ao = bpy.data.images.new('TentCanvas_AO', BAKE, BAKE, alpha=False)
img_ao.colorspace_settings.name = 'Non-Color'

# bake material: procedural weathering evaluated in object space (origin = ground centre, front = −Y)
bake_mat = bpy.data.materials.new('TentCanvasBake')
bake_mat.use_nodes = True
nt = bake_mat.node_tree
nt.nodes.clear()
N_ = nt.nodes.new
L_ = nt.links.new
out = N_('ShaderNodeOutputMaterial')
emis = N_('ShaderNodeEmission')
L_(emis.outputs['Emission'], out.inputs['Surface'])
geo = N_('ShaderNodeNewGeometry')
texco = N_('ShaderNodeTexCoord')
sep_p = N_('ShaderNodeSeparateXYZ')
L_(texco.outputs['Object'], sep_p.inputs['Vector'])
sep_n = N_('ShaderNodeSeparateXYZ')
L_(geo.outputs['Normal'], sep_n.inputs['Vector'])


def noise(scale, detail=4.0, rough=0.55, vec=None, sx=1.0, sy=1.0, sz=1.0):
    n = N_('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough
    mp = N_('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (sx, sy, sz)
    L_(texco.outputs['Object'], mp.inputs['Vector'])
    L_(mp.outputs['Vector'], n.inputs['Vector'])
    return n.outputs['Fac']


def mapr(src, a, b, c=0.0, d=1.0, smooth=True):
    m = N_('ShaderNodeMapRange')
    m.interpolation_type = 'SMOOTHSTEP' if smooth else 'LINEAR'
    m.inputs['From Min'].default_value = a
    m.inputs['From Max'].default_value = b
    m.inputs['To Min'].default_value = c
    m.inputs['To Max'].default_value = d
    L_(src, m.inputs['Value'])
    return m.outputs['Result']


def math_op(op, a, b):
    m = N_('ShaderNodeMath')
    m.operation = op
    for i, x in enumerate((a, b)):
        if isinstance(x, (int, float)):
            m.inputs[i].default_value = x
        else:
            L_(x, m.inputs[i])
    return m.outputs['Value']


def mix_col(a, b, fac):
    m = N_('ShaderNodeMix')
    m.data_type = 'RGBA'
    m.blend_type = 'MIX'
    for sock, x in ((m.inputs[6], a), (m.inputs[7], b)):
        if isinstance(x, tuple):
            sock.default_value = (*x, 1.0)
        else:
            L_(x, sock)
    if isinstance(fac, (int, float)):
        m.inputs[0].default_value = fac
    else:
        L_(fac, m.inputs[0])
    return m.outputs[2]


CANVAS = srgb('#4f5d44')      # olive/sage cotton-poly canvas
FADED = srgb('#77806a')       # sun-bleached ridge
MUD = srgb('#3a2f24')
SOOT = srgb('#1d1c1a')
# base colour variation (large blotches + weave-scale mottling)
var = math_op('ADD', mapr(noise(2.2, 3.0), 0.3, 0.7, -0.1, 0.1), mapr(noise(38.0, 2.0), 0.3, 0.7, -0.04, 0.04))
base = mix_col(CANVAS, (1.0, 1.0, 1.0), 0.0)
hsv = N_('ShaderNodeHueSaturation')
L_(base, hsv.inputs['Color'])
L_(math_op('ADD', var, 1.0), hsv.inputs['Value'])
col = hsv.outputs['Color']
# sun fade on upward-facing surfaces, broken up by noise
sun = math_op('MULTIPLY', mapr(sep_n.outputs['Z'], 0.25, 0.95), mapr(noise(4.0), 0.25, 0.75, 0.55, 1.0))
col = mix_col(col, FADED, math_op('MULTIPLY', sun, 0.5))
# mud splash near the ground (speckled)
low = mapr(sep_p.outputs['Z'], 0.34, 0.02)
speck = mapr(noise(26.0, 6.0, 0.7), 0.47, 0.62)
mud = math_op('MULTIPLY', low, math_op('ADD', math_op('MULTIPLY', speck, 0.8), math_op('MULTIPLY', low, 0.45)))
col = mix_col(col, MUD, math_op('MINIMUM', mud, 0.85))
# vertical rain streaks
streak = mapr(noise(6.0, 3.0, 0.5, sx=4.0, sy=4.0, sz=0.35), 0.52, 0.7)
col = mix_col(col, SOOT, math_op('MULTIPLY', streak, 0.2))
# soot toward the fire (front, −Y) and up high
front = mapr(sep_p.outputs['Y'], 0.0, -D / 2)
soot = math_op('MULTIPLY', math_op('MULTIPLY', front, mapr(sep_p.outputs['Z'], 0.35, 1.05)), mapr(noise(3.0), 0.3, 0.8, 0.4, 1.0))
col = mix_col(col, SOOT, math_op('MULTIPLY', soot, 0.32))
# crease grime from ambient occlusion
aon = N_('ShaderNodeAmbientOcclusion')
aon.inputs['Distance'].default_value = 0.25
aon.samples = 12
grime = mapr(aon.outputs['AO'], 0.35, 1.0, 0.72, 1.0)
col_final = N_('ShaderNodeMix')
col_final.data_type = 'RGBA'
col_final.blend_type = 'MULTIPLY'
col_final.inputs[0].default_value = 1.0
L_(col, col_final.inputs[6])
comb = N_('ShaderNodeCombineColor')
for ch in ('Red', 'Green', 'Blue'):
    L_(grime, comb.inputs[ch])
L_(comb.outputs['Color'], col_final.inputs[7])
base_out = col_final.outputs[2]
# roughness: canvas 0.84, mud rougher, streaks slightly smoother, faded ridge chalky
rough = math_op('ADD', 0.84, mapr(noise(9.0), 0.3, 0.7, -0.05, 0.05))
rough = math_op('ADD', rough, math_op('MULTIPLY', mud, 0.08))
rough = math_op('ADD', rough, math_op('MULTIPLY', sun, 0.04))
rough = math_op('SUBTRACT', rough, math_op('MULTIPLY', streak, 0.06))
rough_rgb = N_('ShaderNodeCombineColor')
for ch in ('Red', 'Green', 'Blue'):
    L_(rough, rough_rgb.inputs[ch])
bake_target = N_('ShaderNodeTexImage')

for ob in (fly, roll):
    ob.data.materials.clear()
    ob.data.materials.append(bake_mat)

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
bake_world = bpy.data.worlds.new('BakeWorld')
bake_world.light_settings.distance = 0.35          # AO reach: creases, seams, under the door roll
scene.world = bake_world
scene.render.bake.margin = 6
bpy.ops.object.select_all(action='DESELECT')
for ob in (fly, roll):
    ob.select_set(True)
bpy.context.view_layer.objects.active = fly
nt.nodes.active = bake_target


def bake(img, kind, src=None):
    bake_target.image = img
    if src is not None:
        L_(src, emis.inputs['Color'])
    bpy.ops.object.bake(type=kind, uv_layer='UV1', use_clear=True, margin=6)


bake(img_base, 'EMIT', base_out)
bake(img_rough, 'EMIT', rough_rgb.outputs['Color'])
scene.cycles.samples = 48
bake(img_ao, 'AO')


def save(img, name, fmt='JPEG', quality=90):
    path = os.path.join(TEX_DIR, name)
    img.filepath_raw = path
    img.file_format = fmt
    if fmt == 'JPEG':
        scene.render.image_settings.quality = quality
        img.save(filepath=path, quality=quality)
    else:
        img.save(filepath=path)
    return path


# pack AO (R) / roughness (G) / metal (B) into one ORM map (glTF occlusion + metallicRoughness)
ao = np.array(img_ao.pixels[:], dtype=np.float32).reshape(BAKE, BAKE, 4)
ro = np.array(img_rough.pixels[:], dtype=np.float32).reshape(BAKE, BAKE, 4)
orm = np.zeros_like(ao)
orm[..., 0] = 0.35 + 0.65 * ao[..., 0]          # keep AO gentle: canvas is thin, light bleeds
orm[..., 1] = np.clip(ro[..., 0], 0.0, 1.0)
orm[..., 3] = 1.0
img_orm = bpy.data.images.new('TentCanvas_ORM', BAKE, BAKE, alpha=False)
img_orm.colorspace_settings.name = 'Non-Color'
img_orm.pixels.foreach_set(orm.ravel())
img_orm.scale(512, 512)                          # ORM is low-frequency: 512 is plenty (texture budget §5)
p_base = save(img_base, 'tent_canvas_basecolor.jpg', 'JPEG', 90)
p_orm = save(img_orm, 'tent_canvas_orm.jpg', 'JPEG', 92)
for im in (img_ao, img_rough):
    bpy.data.images.remove(im)

# final canvas material: baked colour + ORM on UV1, tiling weave normal on UV0
M_CANVAS = bpy.data.materials.new('TentCanvas')
M_CANVAS.use_nodes = True
M_CANVAS.use_backface_culling = True
nt2 = M_CANVAS.node_tree
bsdf = nt2.nodes['Principled BSDF']
base_img = bpy.data.images.load(p_base, check_existing=False)
orm_img = bpy.data.images.load(p_orm, check_existing=False)
t_base = image_node(nt2, base_img, 'UV1', loc=(-600, 300))
nt2.links.new(t_base.outputs['Color'], bsdf.inputs['Base Color'])
t_orm = image_node(nt2, orm_img, 'UV1', non_color=True, loc=(-600, 0))
sep = nt2.nodes.new('ShaderNodeSeparateColor')
sep.location = (-300, 0)
nt2.links.new(t_orm.outputs['Color'], sep.inputs['Color'])
nt2.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
nt2.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
occ = nt2.nodes.new('ShaderNodeGroup')
occ.node_tree = gltf_output_group()
occ.location = (0, -250)
nt2.links.new(sep.outputs['Red'], occ.inputs['Occlusion'])
t_n = image_node(nt2, weave, 'UV0', non_color=True, loc=(-600, -350))
nmap = nt2.nodes.new('ShaderNodeNormalMap')
nmap.uv_map = 'UV0'
nmap.inputs['Strength'].default_value = 0.4
nt2.links.new(t_n.outputs['Color'], nmap.inputs['Color'])
nt2.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
for ob in (fly, roll):
    ob.data.materials.clear()
    ob.data.materials.append(M_CANVAS)
bpy.data.materials.remove(bake_mat)

# roll belongs to the door group; keep objects that don't need UV1 lean
for ob in scene.objects:
    if ob.type == 'MESH':
        for layer in list(ob.data.uv_layers):
            if ob not in (fly, roll) and layer.name != 'UV0':
                ob.data.uv_layers.remove(layer)

# parent everything to the root without moving it (root sits at the origin, identity)
for ob in scene.objects:
    if ob is not root and ob.parent is None:
        ob.parent = root

# stats
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in scene.objects:
    if ob.type == 'MESH':
        me = ob.evaluated_get(dg).data
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
print(f'[tent] triangles: {tris}')

# ---------------------------------------------------------------- export
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB, export_format='GLB', use_selection=False,
    export_apply=True, export_extras=True, export_yup=True,
    export_lights=False, export_cameras=False, export_animations=False,
    export_texcoords=True, export_normals=True, export_tangents=False,
    export_image_format='AUTO', export_materials='EXPORT')
print(f'[tent] exported {OUT_GLB} ({os.path.getsize(OUT_GLB) / 1024:.0f} KB)')

bpy.ops.file.pack_all()
blend = os.path.join(SRC_DIR, 'tent.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
print(f'[tent] saved {blend} ({os.path.getsize(blend) / 1024:.0f} KB)')

if PREVIEW:
    cam = bpy.data.objects.new('PreviewCam', bpy.data.cameras.new('PreviewCam'))
    link(cam)
    cam.location = (1.9, -3.2, 1.35)
    cam.rotation_euler = (Vector((0, 0, 0.45)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    sun = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'POINT'))
    sun.data.energy = 120
    sun.data.color = (1.0, 0.55, 0.25)
    sun.location = (0.6, -3.4, 0.6)
    link(sun)
    world = bpy.data.worlds.new('W')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.2, 0.26, 0.4, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = 0.6
    bpy.ops.mesh.primitive_plane_add(size=8)
    scene.cycles.samples = 48
    scene.render.resolution_x, scene.render.resolution_y = 960, 640
    scene.render.filepath = os.path.join(SRC_DIR, 'preview.png')
    bpy.ops.render.render(write_still=True)
    print('[tent] preview rendered')
