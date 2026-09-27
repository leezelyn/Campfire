"""
Campfire · Stacked split firewood (Blender 4.x, bpy) — Stage 5b

    blender --background --python tools/blender/build_woodpile.py [-- --preview]
    python tools/blender/build_woodpile.py [--preview]              # pip "bpy" module

Outputs  assets/models/woodpile.glb · assets/source/woodpile/woodpile.blend (+ preview.png)
Contract WoodPileRoot (origin = ground centre of the stack, pieces lie along X) · part Pile
         (see src/assets/ModelRegistry.js)

A small campsite stack of split firewood: nine quartered/thirded splits from 16–19 cm rounds, three layers
(4 / 3 / 2) nested in each other's grooves, each piece rolled a little differently. Every split keeps its
log axis as the object Z axis, so the baked patterns line up like real wood: plated bark on the outer arc,
long grain on the split faces, growth rings (centred on the original pith) on the sawn ends.
One baked atlas (UV1): colour / ORM / relief normal.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402  (imports bpy first)
import bpy                       # noqa: E402
from mathutils import Matrix, Vector     # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'woodpile.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'woodpile')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv

BARK = '#4a3e33'
SPLIT = '#8c7458'           # weathered, slightly grey split faces
END = '#8e7152'
ARC = 7                          # segments along the bark arc

random.seed(11)
C.reset()
root = C.empty('WoodPileRoot', size=0.2)


def tag(ob, hexcol, rough, pattern):
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    ob['cf_pattern'] = float(pattern)
    return ob


def split_piece(name, R, span, length, a0):
    """One split: a sector of a round (radius R, angle span) with the apex knocked off, along local Z.
    Returns (bark, faces, ends) objects sharing the log's frame (origin on the pith)."""
    r_in = 0.14 * R
    angs = [a0 - span / 2 + span * i / ARC for i in range(ARC + 1)]
    wob = [1 + 0.04 * math.sin(3 * a + R * 40) for a in angs]
    outer = [(R * w * math.cos(a), R * w * math.sin(a)) for a, w in zip(angs, wob)]
    inner = [(r_in * math.cos(angs[-1]), r_in * math.sin(angs[-1])), (r_in * math.cos(angs[0]), r_in * math.sin(angs[0]))]
    ring = outer + inner                                   # closed polygon, CCW
    zs = [0.0, length * 0.5, length]
    bend = lambda z: 0.006 * math.sin(math.pi * z / length)   # noqa: E731

    def section(z):
        return [(x, y + bend(z), z) for x, y in ring]

    def band(idx_from, idx_to, nm):
        """Side band between consecutive ring vertices idx_from..idx_to (inclusive), all z stations."""
        v, f = [], []
        cols = list(range(idx_from, idx_to + 1)) if idx_to >= idx_from else list(range(idx_from, len(ring))) + list(range(0, idx_to + 1))
        for z in zs:
            sec = section(z)
            v += [sec[c] for c in cols]
        w = len(cols)
        for i in range(len(zs) - 1):
            for k in range(w - 1):
                a, b = i * w + k, i * w + k + 1
                f.append((a, b, b + w, a + w))
        return C.mesh_object(nm, v, f, smooth=True)

    bark = band(0, ARC, name + 'Bark')
    faces = band(ARC, 0, name + 'Split')                  # outer end → apex → other outer end
    for p_ in faces.data.polygons:
        p_.use_smooth = False
    ends_v, ends_f = [], []
    for z, flip in ((0.0, True), (length, False)):
        base = len(ends_v)
        ends_v += section(z)
        f = tuple(base + k for k in range(len(ring)))
        ends_f.append(tuple(reversed(f)) if flip else f)
    ends = C.mesh_object(name + 'Ends', ends_v, ends_f, smooth=False)
    return [tag(bark, BARK, 0.92, 1), tag(faces, SPLIT, 0.85, 3), tag(ends, END, 0.88, 2)]


def centroid(R, span, a0):
    pts = [(R * math.cos(a0 - span / 2 + span * i / ARC), R * math.sin(a0 - span / 2 + span * i / ARC)) for i in range(ARC + 1)]
    pts.append((0.0, 0.0))
    return Vector((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), 0))


LAYERS = [(0.050, [-0.225, -0.075, 0.075, 0.225]), (0.128, [-0.15, 0.0, 0.15]), (0.203, [-0.075, 0.075])]
pieces = []
n = 0
for layer, (y, zs_) in enumerate(LAYERS):
    for zc in zs_:
        R = random.uniform(0.08, 0.095)
        span = random.choice((math.pi / 2, 2 * math.pi / 3, 0.55 * math.pi))
        length = random.uniform(0.48, 0.56)
        # bark mostly up or down alternately; small random roll
        roll = (math.pi / 2 if (n + layer) % 2 else -math.pi / 2) + random.uniform(-0.35, 0.35)
        objs = split_piece(f'Split{n}', R, span, length, 0.0)
        c = centroid(R, span, 0.0)
        # piece frame: log axis (local Z) → world X; roll about it; centroid to the slot
        m = (Matrix.Translation((random.uniform(-0.025, 0.025), zc, y)) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
             @ Matrix.Rotation(roll, 4, 'Z') @ Matrix.Translation((-c.x, -c.y, -length / 2)))
        for o in objs:
            o.matrix_world = m
            o.parent = root
            o.matrix_parent_inverse = Matrix.Identity(4)
        pieces += objs
        n += 1
bpy.context.view_layer.update()

C.unwrap_uv1(pieces, uv0_tile=0.1)
base_p, orm_p, nrm_p, _ = C.bake_weathering(
    pieces, 'woodpile', TEX, size=512, dirt_height=0.0, fade=0.3, edge_wear=0.15, ao_distance=0.05,
    seed=61.0, patterns=True, normal_depth=0.003)
M = C.baked_material('StackedWood', base_p, orm_p, nrm_p, 0.9, normal_uv='UV1')
for o in pieces:
    C.set_material(o, M)
C.join(pieces, 'Pile')

print(f'[woodpile] triangles: {C.triangle_count()}')
print(f'[woodpile] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[woodpile] saved .blend ({C.save_blend(os.path.join(SRC, "woodpile.blend")) / 1024:.0f} KB)')
if PREVIEW:
    C.preview(os.path.join(SRC, 'preview.png'), (0.75, -0.9, 0.6), (0, 0, 0.12), key_loc=(0.6, -0.9, 1.0))
    print('[woodpile] preview rendered')
