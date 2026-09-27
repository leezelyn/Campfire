"""
Campfire · shared Blender (bpy) helpers for asset build scripts.

Used by build_backpack.py / build_chair.py / build_lantern.py / build_kettle.py (and later stages). Conventions (docs/asset-pipeline.md):
Blender Z-up, 1 unit = 1 m, the front of a prop faces Blender −Y (= glTF +Z), origin = ground contact.

Main pieces
    mesh / curve builders     mesh_object, curve_tube, lathe, sweep, catmull, superellipsoid, strip, surface_strip, dashes
    surface queries           Surface (BVH over several objects: nearest point, ray hits)
    hardware                  rounded_box placed on a surface frame (buckles, sliders, caps)
    UV + bake                 unwrap_uv1 (+ uniform-texel UV0), weave_normal, bake_weathering
    output                    baked_material, export_glb, save_blend, preview, triangle_count
"""
import math
import os

import bpy          # must be imported before bmesh/mathutils when running with the pip "bpy" module
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))


# ------------------------------------------------------------------ scene / basic objects
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    return sc


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def empty(name, loc=(0, 0, 0), parent=None, size=0.05):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = size
    e.location = loc
    return link(e, parent)


def mesh_object(name, verts, faces, uv=None, parent=None, smooth=True, uv_name='UV0'):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate(clean_customdata=False)
    me.update()
    if uv is not None:
        layer = me.uv_layers.new(name=uv_name)
        loops = np.empty(len(me.loops), dtype=np.int32)
        me.loops.foreach_get('vertex_index', loops)
        layer.data.foreach_set('uv', np.asarray(uv, dtype=np.float32)[loops].ravel())
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    return link(bpy.data.objects.new(name, me), parent)


def weld(obj, dist=1e-5):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.to_mesh(obj.data)
    bm.free()


def apply_modifiers(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.clear()
    obj.data = new
    new.name = old.name
    bpy.data.meshes.remove(old)


def solidify(obj, thickness, offset=-1.0, rim=True):
    m = obj.modifiers.new('Thickness', 'SOLIDIFY')
    m.thickness, m.offset, m.use_rim, m.use_even_offset, m.use_quality_normals = thickness, offset, rim, True, True
    apply_modifiers(obj)


def bevel(obj, width, segments=2):
    m = obj.modifiers.new('Bevel', 'BEVEL')
    m.width, m.segments, m.limit_method = width, segments, 'ANGLE'
    apply_modifiers(obj)


def join(objs, name):
    objs = [o for o in objs if o is not None]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def set_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj


def curve_tube(name, pts, radius, parent=None, sides=8, smooth=True, caps=True):
    """Polyline → round bevelled curve → mesh (tubes, cords, piping)."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = max(0, sides // 2 - 2)
    cu.use_fill_caps = caps
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (q[0], q[1], q[2], 1.0)
    ob = link(bpy.data.objects.new(name + '_c', cu))
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    me.name = name
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    return link(bpy.data.objects.new(name, me), parent)


def resample(pts, n):
    """Resample a polyline to n points evenly spaced by arc length."""
    pts = [Vector(p) for p in pts]
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seg)
    out, acc, i = [], 0.0, 0
    for k in range(n):
        s = total * k / (n - 1)
        while i < len(seg) - 1 and acc + seg[i] < s:
            acc += seg[i]
            i += 1
        t = 0.0 if seg[i] == 0 else (s - acc) / seg[i]
        out.append(pts[i].lerp(pts[i + 1], min(1.0, max(0.0, t))))
    return out


# ------------------------------------------------------------------ superellipsoid (rounded soft shapes)
def catmull(pts, per_seg=6):
    """Centripetal-ish Catmull–Rom through `pts` (tuples) → dense polyline (wire paths, tubes)."""
    P = [Vector(p) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per_seg):
            t = k / per_seg
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)))
    out.append(tuple(P[-2]))
    return out


def sweep(name, pts, radii, sides=12, parent=None, cap_start=True, cap_end=False, smooth=True):
    """Tapered tube along a polyline (spouts, horns): one ring per point with its own radius,
    parallel-transported frames (no twist). Open ends unless capped."""
    P = [Vector(p) for p in pts]
    n = len(P)
    tangents = []
    for i in range(n):
        t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        tangents.append(t)
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    u = (ref - tangents[0] * ref.dot(tangents[0])).normalized()
    verts, faces = [], []
    for i in range(n):
        if i:
            # parallel transport of u from the previous tangent to this one
            u = (u - tangents[i] * u.dot(tangents[i])).normalized()
        v = tangents[i].cross(u)
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(tuple(P[i] + (u * math.cos(a) + v * math.sin(a)) * radii[i]))
    for i in range(n - 1):
        for k in range(sides):
            a, b = i * sides + k, i * sides + (k + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    if cap_start:
        faces.append(tuple(reversed(range(sides))))
    if cap_end:
        faces.append(tuple((n - 1) * sides + k for k in range(sides)))
    return mesh_object(name, verts, faces, parent=parent, smooth=smooth)


def lathe(name, profile, segments=32, parent=None, smooth=True, loc=(0, 0, 0)):
    """Revolve a (radius, z) profile around local Z. Profile ends with radius 0 become single pole vertices."""
    verts, faces, rings = [], [], []
    for r, z in profile:
        if r < 1e-7:
            rings.append([len(verts)])
            verts.append((loc[0], loc[1], loc[2] + z))
            continue
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring.append(len(verts))
            verts.append((loc[0] + r * math.cos(a), loc[1] + r * math.sin(a), loc[2] + z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        for i in range(segments):
            j = (i + 1) % segments
            if len(a) == 1:
                faces.append((a[0], b[j], b[i]))
            elif len(b) == 1:
                faces.append((a[i], a[j], b[0]))
            else:
                faces.append((a[i], a[j], b[j], b[i]))
    return mesh_object(name, verts, faces, parent=parent, smooth=smooth)


def superellipsoid(name, half, p=4.0, res=12, center=(0, 0, 0), deform=None, parent=None):
    """Rounded box |x/a|^p + |y/b|^p + |z/c|^p = 1 built from a subdivided cube (quads, welded).
    deform(v: Vector) -> Vector is applied in world space after placement."""
    a, b, c = half
    faces_def = [  # (axis origin, u axis, v axis) for the 6 cube faces, outward winding
        (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))),
        (Vector((-1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))),
        (Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))),
        (Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))),
        (Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))),
        (Vector((0, 0, -1)), Vector((0, 1, 0)), Vector((1, 0, 0))),
    ]
    verts, faces = [], []
    for o, u, v in faces_def:
        base = len(verts)
        for j in range(res + 1):
            for i in range(res + 1):
                q = o + u * (2 * i / res - 1) + v * (2 * j / res - 1)
                # equal-angle cube mapping gives more even spacing on the rounded surface
                q = Vector((math.tan(q.x * math.pi / 4), math.tan(q.y * math.pi / 4), math.tan(q.z * math.pi / 4)))
                s = (abs(q.x) ** p + abs(q.y) ** p + abs(q.z) ** p) ** (-1 / p)
                w = Vector((q.x * s * a, q.y * s * b, q.z * s * c)) + Vector(center)
                verts.append(deform(w) if deform else w)
        for j in range(res):
            for i in range(res):
                k = base + j * (res + 1) + i
                faces.append((k, k + 1, k + res + 2, k + res + 1))
    ob = mesh_object(name, verts, faces, None, parent)
    weld(ob, 1e-6)
    return ob


# ------------------------------------------------------------------ surfaces & strips
class Surface:
    """BVH over the evaluated world-space geometry of one or more objects."""

    def __init__(self, objs):
        verts, polys = [], []
        dg = bpy.context.evaluated_depsgraph_get()
        for o in objs:
            me = o.evaluated_get(dg).to_mesh()
            mw = o.matrix_world
            off = len(verts)
            verts.extend(mw @ v.co for v in me.vertices)
            polys.extend([off + i for i in pl.vertices] for pl in me.polygons)
            o.evaluated_get(dg).to_mesh_clear()
        self.bvh = BVHTree.FromPolygons(verts, polys)

    def nearest(self, p):
        loc, nrm, _, _ = self.bvh.find_nearest(Vector(p))
        return loc, nrm

    def hit(self, origin, direction):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm


def strip(name, pts, normals, width, thickness, uv_tile=0.1, parent=None, taper=None):
    """Flat strap/webbing: rectangular cross-section swept along pts, lying in the plane ⟂ normals."""
    n = len(pts)
    verts, uv, faces = [], [], []
    s_acc = 0.0
    for k in range(n):
        p, nrm = Vector(pts[k]), Vector(normals[k]).normalized()
        t = (Vector(pts[min(k + 1, n - 1)]) - Vector(pts[max(k - 1, 0)])).normalized()
        side = t.cross(nrm).normalized()
        nrm = side.cross(t).normalized()
        w = width * (taper(k / (n - 1)) if taper else 1.0)
        if k:
            s_acc += (Vector(pts[k]) - Vector(pts[k - 1])).length
        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):          # ring: bottom-left, bottom-right, top-right, top-left
            verts.append(p + side * (a * w / 2) + nrm * (b * thickness / 2))
            uv.append((s_acc / uv_tile, (a * w / 2 + (b + 1) * thickness) / uv_tile))
    for k in range(n - 1):
        r0, r1 = 4 * k, 4 * (k + 1)
        for e in range(4):
            a, b = r0 + e, r0 + (e + 1) % 4
            faces.append((r1 + e, r1 + (e + 1) % 4, b, a))              # outward-facing
    faces.append((0, 1, 2, 3))
    faces.append(tuple(4 * (n - 1) + e for e in (3, 2, 1, 0)))
    return mesh_object(name, verts, faces, uv, parent, smooth=False)


def surface_strip(name, surf, pts, width, thickness, n=40, lift=0.0015, uv_tile=0.1, parent=None, taper=None):
    """Strap that follows a surface: resample pts, snap each to the nearest surface point, lie on it."""
    locs, nrms = [], []
    for p in resample(pts, n):
        loc, nrm = surf.nearest(p)
        locs.append(loc + nrm * (lift + thickness / 2))
        nrms.append(nrm)
    return strip(name, locs, nrms, width, thickness, uv_tile, parent, taper)


def dashes(name, surf, pts, dash=0.006, gap=0.004, width=0.0013, lift=0.0009, parent=None):
    """Stitch line: short flat quads snapped onto a surface along a path."""
    pts = [Vector(p) for p in pts]
    length = sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))
    n = max(2, int(length / 0.002))
    dense = resample(pts, n)
    verts, faces = [], []
    step = length / (n - 1)
    period = dash + gap
    for k in range(n - 1):
        s = k * step
        if (s % period) > dash:
            continue
        a, b = dense[k], dense[k + 1]
        la, na = surf.nearest(a)
        lb, _ = surf.nearest(b)
        t = (lb - la).normalized()
        side = t.cross(na).normalized() * (width / 2)
        base = len(verts)
        verts += [la + na * lift - side, la + na * lift + side, lb + na * lift + side, lb + na * lift - side]
        faces.append((base, base + 1, base + 2, base + 3))
    return mesh_object(name, verts, faces, None, parent, smooth=False)


def frame_from(normal, tangent):
    """Rotation matrix whose local Z = normal and local Y = tangent (projected)."""
    z = Vector(normal).normalized()
    y = (Vector(tangent) - z * Vector(tangent).dot(z)).normalized()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed().to_4x4()


def rounded_box(name, size, loc, normal=(0, 0, 1), tangent=(0, 1, 0), p=6.0, res=3, parent=None):
    """Small hard part (buckle, slider, cap) oriented on a surface frame; size = full extents (x, y, z)."""
    ob = superellipsoid(name, (size[0] / 2, size[1] / 2, size[2] / 2), p=p, res=res)
    ob.matrix_world = Matrix.Translation(Vector(loc)) @ frame_from(normal, tangent)
    bpy.context.view_layer.update()
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    if parent is not None:
        ob.parent = parent
    return ob


# ------------------------------------------------------------------ textures
def weave_normal(name, out_dir, size=512, period=8, strength=1.6, kind='plain', seed=7):
    """Tileable fabric normal map (plain weave / 2x2 twill for webbing). OpenGL/glTF green-up."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    cx, cy = np.floor(x / period), np.floor(y / period)
    fx, fy = (x % period) / period, (y % period) / period
    prof_w = np.clip(np.cos(np.pi * (fx - 0.5)), 0, 1) ** 0.7
    prof_f = np.clip(np.cos(np.pi * (fy - 0.5)), 0, 1) ** 0.7
    if kind == 'twill':   # diagonal ribs: over two, under two, shifted each row
        ph = np.pi * (y / period + cx) / 2
        h_warp = prof_w * (0.5 + 0.5 * np.sin(ph))
        h_weft = prof_f * (0.5 + 0.5 * np.sin(np.pi * (x / period + cy) / 2 + np.pi))
    else:
        h_warp = prof_w * (0.5 + 0.5 * np.sin(np.pi * y / period + np.pi * cx))
        h_weft = prof_f * (0.5 + 0.5 * np.sin(np.pi * x / period + np.pi * cy + np.pi))
    nt = size // period + 1
    h = np.maximum(h_warp * rng.normal(1, 0.1, nt)[cx.astype(int)], h_weft * rng.normal(1, 0.1, nt)[cy.astype(int)])
    lf = np.zeros_like(h)
    for k, a in ((2, 0.2), (5, 0.1), (13, 0.04)):
        p3 = rng.uniform(0, 2 * np.pi, 3)
        lf += a * (np.sin(2 * np.pi * k * x / size + p3[0]) * np.sin(2 * np.pi * k * y / size + p3[1])
                   + 0.5 * np.sin(2 * np.pi * k * (x - y) / size + p3[2]))
    h = h * 0.6 + lf
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.concatenate([n * 0.5 + 0.5, np.ones((size, size, 1), np.float32)], -1).astype(np.float32).ravel())
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name + '.png')
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return bpy.data.images.load(path, check_existing=False)


# ------------------------------------------------------------------ materials
def gltf_output_group():
    g = bpy.data.node_groups.get('glTF Material Output')
    if g:
        return g
    g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
    g.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    g.nodes.new('NodeGroupInput')
    return g


def _image_node(nt, img, uv_name, non_color, loc):
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


def pbr(name, color, rough, metal=0.0, normal_img=None, normal_strength=0.4, cull=True,
        emission=None, emission_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = cull
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emission is not None:
        b.inputs['Emission Color'].default_value = (*emission, 1.0)
        b.inputs['Emission Strength'].default_value = emission_strength
    if normal_img is not None:
        t = _image_node(nt, normal_img, 'UV0', True, (-500, -400))
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.uv_map = 'UV0'
        nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(t.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def baked_material(name, base_path, orm_path, normal_img, normal_strength=0.4, cull=True,
                   normal_uv='UV0', emissive_path=None, emissive_strength=1.0):
    """Final PBR material: baked colour + ORM on UV1 (occlusion via glTF Material Output), normal map on
    `normal_uv` (tiling detail on UV0, or a baked relief on UV1), optional baked emissive map on UV1."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = cull
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tb = _image_node(nt, bpy.data.images.load(base_path, check_existing=False), 'UV1', False, (-600, 300))
    nt.links.new(tb.outputs['Color'], b.inputs['Base Color'])
    to = _image_node(nt, bpy.data.images.load(orm_path, check_existing=False), 'UV1', True, (-600, 0))
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(to.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], b.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    occ = nt.nodes.new('ShaderNodeGroup')
    occ.node_tree = gltf_output_group()
    nt.links.new(sep.outputs['Red'], occ.inputs['Occlusion'])
    if emissive_path is not None:
        te = _image_node(nt, bpy.data.images.load(emissive_path, check_existing=False), 'UV1', False, (-600, -650))
        nt.links.new(te.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = emissive_strength
    if normal_img is not None:
        if isinstance(normal_img, str):
            normal_img = bpy.data.images.load(normal_img, check_existing=False)
        tn = _image_node(nt, normal_img, normal_uv, True, (-600, -350))
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.uv_map = normal_uv
        nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


# ------------------------------------------------------------------ UVs
def unwrap_uv1(objs, uv0_tile, margin=0.004):
    """UV1 = non-overlapping unique unwrap (smart project + pack) for baking.
    UV0 = UV1 × k so one UV0 unit is `uv0_tile` metres (uniform texel density, tiling detail maps)."""
    for o in objs:
        me = o.data
        while len(me.uv_layers):
            me.uv_layers.remove(me.uv_layers[0])
        me.uv_layers.new(name='UV0')
        me.uv_layers.active = me.uv_layers.new(name='UV1')
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=margin, scale_to_bounds=True)
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    # uniform scale factor world-area / uv-area over all objects
    area_w = area_uv = 0.0
    for o in objs:
        me = o.data
        uv1 = me.uv_layers['UV1'].data
        for pl in me.polygons:
            area_w += pl.area
            uvs = [uv1[li].uv for li in pl.loop_indices]
            a = 0.0
            for i in range(len(uvs)):
                x0, y0 = uvs[i]
                x1, y1 = uvs[(i + 1) % len(uvs)]
                a += x0 * y1 - x1 * y0
            area_uv += abs(a) / 2
    k = math.sqrt(area_w / max(area_uv, 1e-9)) / uv0_tile
    for o in objs:
        me = o.data
        src = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers['UV1'].data.foreach_get('uv', src)
        me.uv_layers['UV0'].data.foreach_set('uv', src * k)
        me.uv_layers['UV0'].active_render = True
    return k


# ------------------------------------------------------------------ weathering bake
def bake_weathering(objs, name, out_dir, size=1024, dirt_height=0.12, fade=0.4, edge_wear=0.35,
                    stains=0.0, soot_front=0.0, ao_distance=0.2, seed=0.0,
                    chips=0.0, chip_color='#6c6a64', soot_top=None, metal=False,
                    soot_bottom=None, rust=0.0, patterns=False, glow_z=(0.0, 1.0), normal_depth=0.0025,
                    tip_color=None, glow_colors=('#7a1e04', '#ffb066')):
    """Bake a weathered base colour and ORM (AO / roughness / metal) into UV1 for `objs`.

    Each object supplies its own look through custom properties:
        cf_color  (r, g, b) linear base colour     cf_rough  base roughness
    Weathering (object space, origin on the ground, front = −Y):
        variation · sun fade on up-facing surfaces · ground dirt below `dirt_height` ·
        edge wear on convex edges (pointiness) · optional stains / soot · AO crease grime
    Painted metal (metal=True): per-object `cf_metal`; `chips` > 0 flakes paint off convex edges and in
    scattered spots, exposing bare metal (`chip_color`, metallic 1) ringed with rust;
    `soot_top` = (z0, z1, amount) blackens surfaces above z0 (lamp chimneys, pot rims);
    `soot_bottom` = (z0, z1, amount) blackens surfaces below z1 (pots over a fire, z0 = full soot);
    `rust` > 0 adds orange-brown oxide patches (matte, non-metallic).
    Wood & fire (patterns=True): per-object `cf_pattern` selects an object-space surface pattern
    (objects are modelled along their local Z):
        1 bark (fissures along Z)  2 end grain (growth rings round Z)  3 debarked wood grain
        4 charcoal (alligator cracks)  5 ember cloth (glows from glow_z[0] up to glow_z[1])
    and two more maps are baked into UV1: a tangent-space normal map from the pattern relief
    (`normal_depth` m) and an emissive map (glowing char cracks / ember gradient) ramping from
    glow_colors[0] (dim) to glow_colors[1] (hottest) — keep it deep if the runtime drives intensity > 1.
    `tip_color`: a per-vertex float attribute `cf_tip` (0..1) blends toward this colour (weathered scale tips).
    Returns [basecolor, orm] (+ [normal, emissive] when patterns=True).
    """
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    world = bpy.data.worlds.new('BakeWorld')
    world.light_settings.distance = ao_distance
    sc.world = world
    mat = bpy.data.materials.new(name + '_bake')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputMaterial')
    emis = N('ShaderNodeEmission')
    L(emis.outputs['Emission'], out.inputs['Surface'])
    geo = N('ShaderNodeNewGeometry')
    tc = N('ShaderNodeTexCoord')
    sp = N('ShaderNodeSeparateXYZ')
    L(tc.outputs['Object'], sp.inputs['Vector'])
    sn = N('ShaderNodeSeparateXYZ')
    L(geo.outputs['Normal'], sn.inputs['Vector'])
    attr_c = N('ShaderNodeAttribute')
    attr_c.attribute_type, attr_c.attribute_name = 'OBJECT', 'cf_color'
    attr_r = N('ShaderNodeAttribute')
    attr_r.attribute_type, attr_r.attribute_name = 'OBJECT', 'cf_rough'

    def noise(scale, detail=3.0, rough=0.55, sc3=(1, 1, 1)):
        n = N('ShaderNodeTexNoise')
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        mp = N('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = sc3
        mp.inputs['Location'].default_value = (seed * 3.1, seed * 1.7, seed * 2.3)
        L(tc.outputs['Object'], mp.inputs['Vector'])
        L(mp.outputs['Vector'], n.inputs['Vector'])
        return n.outputs['Fac']

    def mr(src, a, b, c=0.0, d=1.0):
        m = N('ShaderNodeMapRange')
        m.interpolation_type = 'SMOOTHSTEP'
        m.inputs['From Min'].default_value, m.inputs['From Max'].default_value = a, b
        m.inputs['To Min'].default_value, m.inputs['To Max'].default_value = c, d
        L(src, m.inputs['Value'])
        return m.outputs['Result']

    def op(kind, a, b):
        m = N('ShaderNodeMath')
        m.operation = kind
        for i, x in enumerate((a, b)):
            if isinstance(x, (int, float)):
                m.inputs[i].default_value = x
            else:
                L(x, m.inputs[i])
        return m.outputs['Value']

    def mix(a, b, fac, blend='MIX'):
        m = N('ShaderNodeMix')
        m.data_type, m.blend_type = 'RGBA', blend
        for sock, x in ((m.inputs[6], a), (m.inputs[7], b)):
            if isinstance(x, tuple):
                sock.default_value = (*x, 1.0)
            else:
                L(x, sock)
        if isinstance(fac, (int, float)):
            m.inputs[0].default_value = fac
        else:
            L(fac, m.inputs[0])
        return m.outputs[2]

    hsv = N('ShaderNodeHueSaturation')
    L(attr_c.outputs['Color'], hsv.inputs['Color'])
    var = op('ADD', mr(noise(3.0), 0.3, 0.7, -0.09, 0.09), mr(noise(45.0, 2.0), 0.3, 0.7, -0.035, 0.035))
    L(op('ADD', var, 1.0), hsv.inputs['Value'])
    col = hsv.outputs['Color']
    if tip_color is not None:
        attr_t = N('ShaderNodeAttribute')
        attr_t.attribute_type, attr_t.attribute_name = 'GEOMETRY', 'cf_tip'
        col = mix(col, srgb(tip_color), attr_t.outputs['Fac'])
    height = glow = None
    if patterns:
        attr_p = N('ShaderNodeAttribute')
        attr_p.attribute_type, attr_p.attribute_name = 'OBJECT', 'cf_pattern'
        pv = attr_p.outputs['Fac']

        def w(k):
            return op('MAXIMUM', op('SUBTRACT', 1.0, op('ABSOLUTE', op('SUBTRACT', pv, float(k)), 0.0)), 0.0)

        # 1 bark: plates split by deep fissures running along the log
        # fissures = narrow zero-crossing lines of noise stretched along Z (two scales)
        fis_a = op('ABSOLUTE', op('SUBTRACT', noise(20.0, 4.0, 0.55, (1, 1, 0.1)), 0.5), 0.0)
        fis_b = op('ABSOLUTE', op('SUBTRACT', noise(48.0, 3.0, 0.55, (1, 1, 0.14)), 0.5), 0.0)
        crack1 = op('MAXIMUM', mr(fis_a, 0.0, 0.035, 1.0, 0.0), op('MULTIPLY', mr(fis_b, 0.0, 0.025, 1.0, 0.0), 0.6))
        plate = noise(70.0, 4.0, 0.6, (1, 1, 0.35))
        f1 = op('SUBTRACT', op('ADD', 0.9, op('MULTIPLY', plate, 0.25)), op('MULTIPLY', crack1, 0.72))
        h1 = op('ADD', op('MULTIPLY', plate, 0.3), op('SUBTRACT', 0.62, op('MULTIPLY', crack1, 0.75)))
        # optional scorching toward a burning end: cf_scorch (amount) above cf_scorch_z
        attr_sa = N('ShaderNodeAttribute')
        attr_sa.attribute_type, attr_sa.attribute_name = 'OBJECT', 'cf_scorch'
        attr_sz = N('ShaderNodeAttribute')
        attr_sz.attribute_type, attr_sz.attribute_name = 'OBJECT', 'cf_scorch_z'
        zrel = op('SUBTRACT', op('ADD', sp.outputs['Z'], op('MULTIPLY', op('SUBTRACT', noise(7.0, 3.0), 0.5), 0.08)),
                  attr_sz.outputs['Fac'])
        scorch = op('MULTIPLY', attr_sa.outputs['Fac'], mr(zrel, 0.0, 0.16))
        f1 = op('MULTIPLY', f1, op('SUBTRACT', 1.0, op('MULTIPLY', scorch, 0.8)))
        # 2 end grain: growth rings round the axis, darker pith
        cxy = N('ShaderNodeCombineXYZ')
        L(sp.outputs['X'], cxy.inputs['X'])
        L(sp.outputs['Y'], cxy.inputs['Y'])
        vlen = N('ShaderNodeVectorMath')
        vlen.operation = 'LENGTH'
        L(cxy.outputs['Vector'], vlen.inputs[0])
        rr = vlen.outputs['Value']
        ring = op('SINE', op('ADD', op('MULTIPLY', rr, 690.0), op('MULTIPLY', noise(12.0, 3.0), 7.0)), 0.0)
        late = mr(ring, 0.5, 0.95)
        f2 = op('SUBTRACT', op('SUBTRACT', 1.0, op('MULTIPLY', late, 0.32)), op('MULTIPLY', mr(rr, 0.006, 0.0), 0.4))
        h2 = op('SUBTRACT', 0.5, op('MULTIPLY', late, 0.2))
        # 3 debarked wood: long streaks and fine fibre
        streak = noise(26.0, 5.0, 0.6, (1, 1, 0.04))
        fibre = noise(150.0, 2.0, 0.5, (1, 1, 0.05))
        f3 = op('ADD', 0.82, op('MULTIPLY', mr(streak, 0.3, 0.7), 0.3))
        h3 = op('ADD', 0.4, op('ADD', op('MULTIPLY', streak, 0.12), op('MULTIPLY', fibre, 0.1)))
        # 4 charcoal: alligator cells, deep cracks that glow
        mp = N('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (1, 1, 1.6)     # checks run round the log more than along it
        mp.inputs['Location'].default_value = (seed * 1.3, seed * 0.7, seed * 2.1)
        L(tc.outputs['Object'], mp.inputs['Vector'])
        vor = N('ShaderNodeTexVoronoi')
        vor.feature = 'DISTANCE_TO_EDGE'
        vor.inputs['Scale'].default_value = 75.0
        L(mp.outputs['Vector'], vor.inputs['Vector'])
        crack4 = mr(vor.outputs['Distance'], 0.0, 0.05, 1.0, 0.0)
        f4 = op('SUBTRACT', op('ADD', 0.85, op('MULTIPLY', noise(20.0, 3.0), 0.3)), op('MULTIPLY', crack4, 0.6))
        h4 = op('ADD', op('SUBTRACT', 0.6, op('MULTIPLY', crack4, 0.6)), op('MULTIPLY', noise(90.0, 2.0), 0.1))
        # cracks glow patchily (not every crack is live) over a dim ember baseline on the whole char surface
        g4 = op('ADD', op('MULTIPLY', crack4, mr(noise(5.0, 3.0), 0.3, 0.6, 0.35, 1.0)),
                op('MULTIPLY', mr(noise(9.0, 3.0), 0.3, 0.7), 0.16))
        # 5 ember cloth: charred and glowing toward the top, ragged burn line
        zz = op('ADD', sp.outputs['Z'], op('MULTIPLY', op('SUBTRACT', noise(9.0, 4.0), 0.5), 0.06))
        g5 = mr(zz, glow_z[0], glow_z[1])
        f5 = op('SUBTRACT', 1.0, op('MULTIPLY', g5, 0.75))

        fac = op('ADD', op('ADD', op('MULTIPLY', w(1), op('SUBTRACT', f1, 1.0)), op('MULTIPLY', w(2), op('SUBTRACT', f2, 1.0))),
                 op('ADD', op('MULTIPLY', w(3), op('SUBTRACT', f3, 1.0)),
                    op('ADD', op('MULTIPLY', w(4), op('SUBTRACT', f4, 1.0)), op('MULTIPLY', w(5), op('SUBTRACT', f5, 1.0)))))
        fac = op('ADD', fac, 1.0)
        f3c = N('ShaderNodeCombineColor')
        for ch in ('Red', 'Green', 'Blue'):
            L(fac, f3c.inputs[ch])
        col = mix(col, f3c.outputs['Color'], 1.0, 'MULTIPLY')
        height = 0.5
        for k, hk in ((1, h1), (2, h2), (3, h3), (4, h4)):
            height = op('ADD', height, op('MULTIPLY', w(k), op('SUBTRACT', hk, 0.5)))
        glow = op('ADD', op('MULTIPLY', w(4), g4), op('MULTIPLY', w(5), g5))
    sun = op('MULTIPLY', mr(sn.outputs['Z'], 0.3, 0.95), mr(noise(4.0), 0.25, 0.75, 0.5, 1.0))
    faded = N('ShaderNodeHueSaturation')
    faded.inputs['Saturation'].default_value = 0.55
    faded.inputs['Value'].default_value = 1.45
    L(col, faded.inputs['Color'])
    col = mix(col, faded.outputs['Color'], op('MULTIPLY', sun, fade))
    low = mr(sp.outputs['Z'], dirt_height, 0.0)
    speck = mr(noise(28.0, 6.0, 0.7), 0.46, 0.62)
    dirt = op('MULTIPLY', low, op('ADD', op('MULTIPLY', speck, 0.6), op('MULTIPLY', low, 0.5)))
    col = mix(col, srgb('#3b3024'), op('MINIMUM', dirt, 0.8))
    # edge wear: convex edges scuffed lighter and drier
    wear = op('MULTIPLY', mr(geo.outputs['Pointiness'], 0.52, 0.6), mr(noise(20.0, 4.0), 0.35, 0.7))
    worn = N('ShaderNodeHueSaturation')
    worn.inputs['Saturation'].default_value = 0.6
    worn.inputs['Value'].default_value = 1.6
    L(col, worn.inputs['Color'])
    col = mix(col, worn.outputs['Color'], op('MULTIPLY', wear, edge_wear))
    if stains > 0:
        st = op('MULTIPLY', mr(noise(7.0, 2.0, 0.4), 0.62, 0.68), mr(sn.outputs['Z'], 0.4, 0.9))
        col = mix(col, srgb('#2a1d14'), op('MULTIPLY', st, stains))
    if soot_front > 0:
        front = mr(sp.outputs['Y'], 0.0, -0.3)
        col = mix(col, srgb('#1c1b1a'), op('MULTIPLY', op('MULTIPLY', front, mr(noise(3.0), 0.3, 0.8)), soot_front))
    soot = None
    if soot_top is not None:
        z0, z1, amt = soot_top
        soot = op('MULTIPLY', mr(sp.outputs['Z'], z0, z1), op('MULTIPLY', mr(noise(6.0, 3.0), 0.25, 0.7, 0.55, 1.0), amt))
        col = mix(col, srgb('#15130f'), soot)
    if soot_bottom is not None:
        z0, z1, amt = soot_bottom
        sb = op('MULTIPLY', mr(sp.outputs['Z'], z1, z0), op('MULTIPLY', mr(noise(5.0, 4.0), 0.3, 0.65, 0.6, 1.0), amt))
        col = mix(col, srgb('#0d0c0b'), sb)
        soot = sb if soot is None else op('MAXIMUM', soot, sb)
    rusty = None
    if rust > 0:
        rusty = op('MULTIPLY', mr(op('ADD', noise(9.0, 5.0, 0.6), op('MULTIPLY', noise(40.0, 6.0), 0.25)), 0.66, 0.78), rust)
        col = mix(col, srgb('#5b3620'), rusty)
    chip = None
    if chips > 0:
        # one field drives chips (bare metal) and the rust ring around them
        # edges only chip where the noise agrees (patchy, not an outline); flats chip only at rare peaks
        field = op('ADD', op('MULTIPLY', mr(geo.outputs['Pointiness'], 0.5, 0.58), 0.35),
                   op('ADD', op('MULTIPLY', mr(noise(38.0, 8.0, 0.75), 0.4, 0.7), 0.6),
                      op('MULTIPLY', mr(noise(6.0, 3.0), 0.35, 0.65), 0.25)))
        thr = 1.25 - 0.4 * chips
        chip = mr(field, thr, thr + 0.015)
        rust = op('SUBTRACT', mr(field, thr - 0.045, thr - 0.005), chip)
        col = mix(col, srgb('#3d2719'), op('MULTIPLY', op('MAXIMUM', rust, 0.0), 0.65))
        col = mix(col, srgb(chip_color), chip)
    ao = N('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = ao_distance
    ao.samples = 12
    grime = mr(ao.outputs['AO'], 0.3, 1.0, 0.7, 1.0)
    g3 = N('ShaderNodeCombineColor')
    for ch in ('Red', 'Green', 'Blue'):
        L(grime, g3.inputs[ch])
    base_out = mix(col, g3.outputs['Color'], 1.0, 'MULTIPLY')
    rough = op('ADD', attr_r.outputs['Fac'], mr(noise(10.0), 0.3, 0.7, -0.05, 0.05))
    rough = op('ADD', rough, op('MULTIPLY', dirt, 0.08))
    rough = op('ADD', rough, op('MULTIPLY', wear, 0.06))
    if soot is not None:
        rough = op('ADD', rough, op('MULTIPLY', soot, 0.35))
    if rusty is not None:
        rough = op('ADD', rough, op('MULTIPLY', rusty, 0.25))
    if chip is not None:
        rough = op('ADD', op('MULTIPLY', rough, op('SUBTRACT', 1.0, chip)), op('MULTIPLY', chip, 0.48))
    r3 = N('ShaderNodeCombineColor')
    for ch in ('Red', 'Green', 'Blue'):
        L(rough, r3.inputs[ch])
    m3 = None
    if metal:
        attr_m = N('ShaderNodeAttribute')
        attr_m.attribute_type, attr_m.attribute_name = 'OBJECT', 'cf_metal'
        met = attr_m.outputs['Fac']
        for dull in (soot, rusty):          # soot and oxide are not metallic
            if dull is not None:
                met = op('MULTIPLY', met, op('SUBTRACT', 1.0, op('MINIMUM', dull, 1.0)))
        if chip is not None:
            met = op('MAXIMUM', met, chip)
        m3 = N('ShaderNodeCombineColor')
        for ch in ('Red', 'Green', 'Blue'):
            L(met, m3.inputs[ch])
    target = N('ShaderNodeTexImage')
    nt.nodes.active = target

    saved = {o: list(o.data.materials) for o in objs}
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

    def img(n, non_color):
        im = bpy.data.images.new(n, size, size, alpha=False)
        if non_color:
            im.colorspace_settings.name = 'Non-Color'
        return im

    i_base, i_rough, i_ao = img(name + '_base', False), img(name + '_rough', True), img(name + '_ao', True)

    def bake(im, kind, src=None, samples=16):
        target.image = im
        sc.cycles.samples = samples
        if src is not None:
            L(src, emis.inputs['Color'])
        bpy.ops.object.bake(type=kind, uv_layer='UV1', use_clear=True, margin=6)

    bake(i_base, 'EMIT', base_out)
    bake(i_rough, 'EMIT', r3.outputs['Color'])
    bake(i_ao, 'AO', samples=48)
    ao_px = np.array(i_ao.pixels[:], np.float32).reshape(size, size, 4)
    ro_px = np.array(i_rough.pixels[:], np.float32).reshape(size, size, 4)
    orm = np.zeros_like(ao_px)
    orm[..., 0] = 0.3 + 0.7 * ao_px[..., 0]
    orm[..., 1] = np.clip(ro_px[..., 0], 0, 1)
    orm[..., 3] = 1
    if m3 is not None:
        i_met = img(name + '_metal', True)
        bake(i_met, 'EMIT', m3.outputs['Color'])
        orm[..., 2] = np.clip(np.array(i_met.pixels[:], np.float32).reshape(size, size, 4)[..., 0], 0, 1)
        bpy.data.images.remove(i_met)
    i_orm = img(name + '_orm', True)
    i_orm.pixels.foreach_set(orm.ravel())
    outputs = [(i_base, f'{name}_basecolor.jpg'), (i_orm, f'{name}_orm.jpg')]
    if patterns:
        # relief → tangent-space normal (UV1): a diffuse BSDF with the bumped normal, baked as NORMAL
        bump = N('ShaderNodeBump')
        bump.inputs['Distance'].default_value = normal_depth
        L(height, bump.inputs['Height'])
        dif = N('ShaderNodeBsdfDiffuse')
        L(bump.outputs['Normal'], dif.inputs['Normal'])
        L(dif.outputs['BSDF'], out.inputs['Surface'])
        sc.render.bake.normal_space = 'TANGENT'
        i_nrm = img(name + '_normal', True)
        bake(i_nrm, 'NORMAL', samples=4)
        L(emis.outputs['Emission'], out.inputs['Surface'])
        # glow → emissive colour map: deep ember red in the dim parts, hot orange in the brightest cracks
        gm = N('ShaderNodeMix')
        gm.data_type = 'RGBA'
        gm.inputs[6].default_value = (*srgb(glow_colors[0]), 1.0)
        gm.inputs[7].default_value = (*srgb(glow_colors[1]), 1.0)
        L(glow, gm.inputs[0])
        g3e = N('ShaderNodeCombineColor')
        for ch in ('Red', 'Green', 'Blue'):
            L(glow, g3e.inputs[ch])
        i_emi = img(name + '_emissive', False)
        bake(i_emi, 'EMIT', mix(gm.outputs[2], g3e.outputs['Color'], 1.0, 'MULTIPLY'), samples=4)
        outputs += [(i_nrm, f'{name}_normal.jpg'), (i_emi, f'{name}_emissive.jpg')]
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for im, fn in outputs:
        pth = os.path.join(out_dir, fn)
        im.filepath_raw = pth
        im.file_format = 'JPEG'
        im.save(filepath=pth, quality=92)
        paths.append(pth)
    for im in [i_base, i_rough, i_ao] + [im for im, _ in outputs[1:]]:
        bpy.data.images.remove(im)
    for o in objs:
        o.data.materials.clear()
        for m in saved[o]:
            o.data.materials.append(m)
    bpy.data.materials.remove(mat)
    return paths


# ------------------------------------------------------------------ output
def triangle_count():
    dg = bpy.context.evaluated_depsgraph_get()
    tris = 0
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            me = o.evaluated_get(dg).data
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
    return tris


def export_glb(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=False,
        export_apply=True, export_extras=True, export_yup=True,
        export_lights=False, export_cameras=False, export_animations=False,
        export_texcoords=True, export_normals=True, export_tangents=False,
        export_image_format='AUTO', export_materials='EXPORT')
    return os.path.getsize(path)


def save_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    backup = path + '1'
    if os.path.exists(backup):
        os.remove(backup)
    return os.path.getsize(path)


def preview(path, cam_loc, target, key_loc=(0.8, -2.5, 1.2), size=(900, 700), samples=48):
    sc = bpy.context.scene
    cam = link(bpy.data.objects.new('PreviewCam', bpy.data.cameras.new('PreviewCam')))
    cam.location = cam_loc
    cam.rotation_euler = (Vector(target) - Vector(cam_loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 50
    sc.camera = cam
    key = link(bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'POINT')))
    key.data.energy, key.data.color, key.location = 80, (1.0, 0.6, 0.3), key_loc
    w = bpy.data.worlds.new('Preview')
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.22, 0.27, 0.38, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.7
    bpy.ops.mesh.primitive_plane_add(size=6)
    sc.cycles.samples = samples
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
