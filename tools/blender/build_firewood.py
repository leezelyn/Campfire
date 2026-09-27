"""
Campfire · Firewood rounds (Blender 4.x, bpy) — Stage 5

    blender --background --python tools/blender/build_firewood.py [-- --preview]
    python tools/blender/build_firewood.py [--preview]              # pip "bpy" module

Outputs  assets/models/firewood.glb (three roots) · assets/source/firewood/firewood.blend (+ preview.png)
Contract Log1Root / Log2Root / Log3Root — origin = centre of the outer (bottom) end, axis +Z (glTF +Y),
         lengths 0.66 / 0.70 / 0.74 m · parts Bark, CharEnd · materials Bark (colour driven: charring),
         Charcoal (emissive intensity driven: glowing cracks)   (see src/assets/ModelRegistry.js)

Split-free branch rounds as used in the teepee: an irregular, slightly tapered and bent trunk with plated
bark and a branch stub, sawn end faces showing growth rings inside a bark rim, and — as its own mesh —
the burning end: a charred shell over the top ~40 % that swells out of the bark and closes in a burnt,
rounded tip. Hiding CharEnd leaves a fresh sawn log (used for the logs the player adds).
One baked atlas (UV1): colour / ORM / relief normal / emissive (glowing char cracks).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_common as C            # noqa: E402  (imports bpy first)
import bpy                       # noqa: E402
from mathutils import Vector, noise as mnoise     # noqa: E402

OUT_GLB = os.path.join(C.REPO, 'assets', 'models', 'firewood.glb')
SRC = os.path.join(C.REPO, 'assets', 'source', 'firewood')
TEX = os.path.join(SRC, 'textures')
PREVIEW = '--preview' in sys.argv

VARIANTS = [  # length, radius, bend, seed
    (0.66, 0.068, 0.012, 1.0),
    (0.70, 0.076, 0.018, 2.0),
    (0.74, 0.082, 0.010, 3.0),
]
SIDES, RINGS = 20, 14
CHAR_FROM = 0.60                  # CharEnd covers the top 40 %
BARK = '#4b4036'
WOOD = '#9c7a52'
CHAR = '#161009'

C.reset()


def tag(ob, hexcol, rough, pattern):
    ob['cf_color'] = C.srgb(hexcol)
    ob['cf_rough'] = rough
    ob['cf_pattern'] = float(pattern)
    return ob


def trunk_fn(L, R, bend, seed):
    """Centre line and radius of the round at height z (irregular, tapered, slightly bent)."""
    def centre(z):
        u = z / L
        return Vector((bend * math.sin(math.pi * u) + 0.004 * mnoise.noise(Vector((seed, u * 3, 0))),
                       0.006 * mnoise.noise(Vector((u * 2.5, seed, 1))), z))

    def radius(z, a):
        u = z / L
        lobe = 0.05 * mnoise.noise(Vector((math.cos(a) * 1.3, math.sin(a) * 1.3, seed + u * 2.2)))
        return R * (1.0 - 0.1 * u) * (1.0 + lobe + 0.02 * math.sin(3 * a + seed))
    return centre, radius


def tube_mesh(name, L, centre, radius, z0, z1, rings, scale=1.0, tip=None, ragged=0.0, seed=0.0):
    """Open tube from z0 to z1 following centre/radius; optional rounded tip cap and a ragged lower edge."""
    verts, faces = [], []
    zs = [z0 + (z1 - z0) * i / (rings - 1) for i in range(rings)]
    for i, z in enumerate(zs):
        for k in range(SIDES):
            a = 2 * math.pi * k / SIDES
            zz = z
            if ragged and i < 2:
                zz = z + ragged * (1 - i * 0.6) * mnoise.noise(Vector((math.cos(a) * 1.7, math.sin(a) * 1.7, seed)))
            c = centre(zz)
            s = scale(zz) if callable(scale) else scale
            r = radius(zz, a) * s
            verts.append((c.x + r * math.cos(a), c.y + r * math.sin(a), zz))
    for i in range(rings - 1):
        for k in range(SIDES):
            a, b = i * SIDES + k, i * SIDES + (k + 1) % SIDES
            faces.append((a, b, b + SIDES, a + SIDES))
    if tip is not None:
        # burnt, rounded end: shrinking rings up to a pole
        last = (rings - 1) * SIDES
        c = centre(z1)
        prev = list(range(last, last + SIDES))
        for j, (f, dz) in enumerate(tip):
            ring = []
            for k in range(SIDES):
                a = 2 * math.pi * k / SIDES
                r = radius(z1, a) * (scale(z1) if callable(scale) else scale) * f
                ring.append(len(verts))
                verts.append((c.x + r * math.cos(a), c.y + r * math.sin(a), z1 + dz))
            for k in range(SIDES):
                faces.append((prev[k], prev[(k + 1) % SIDES], ring[(k + 1) % SIDES], ring[k]))
            prev = ring
        pole = len(verts)
        verts.append((c.x, c.y, z1 + tip[-1][1] + 0.006))
        for k in range(SIDES):
            faces.append((prev[k], prev[(k + 1) % SIDES], pole))
    return C.mesh_object(name, verts, faces)


def end_face(name, centre, radius, z, up, inset):
    """Sawn end: end-grain disc (pattern 2) inside a bark rim (pattern 1 colour, darker)."""
    c = centre(z)
    verts, faces = [], []
    for k in range(SIDES):
        a = 2 * math.pi * k / SIDES
        r = radius(z, a)
        verts.append((c.x + r * math.cos(a), c.y + r * math.sin(a), z))
    for k in range(SIDES):
        a = 2 * math.pi * k / SIDES
        r = radius(z, a) * inset
        verts.append((c.x + r * math.cos(a), c.y + r * math.sin(a), z + up * 0.002))
    for k in range(SIDES):
        k2 = (k + 1) % SIDES
        f = (k, k2, SIDES + k2, SIDES + k)
        faces.append(f if up > 0 else tuple(reversed(f)))
    rim = C.mesh_object(name + 'Rim', verts, faces, smooth=False)
    dv = [verts[SIDES + k] for k in range(SIDES)] + [(c.x, c.y, z + up * 0.003)]
    df = [((k + 1) % SIDES, k, SIDES) if up < 0 else (k, (k + 1) % SIDES, SIDES) for k in range(SIDES)]
    disc = C.mesh_object(name, dv, df, smooth=False)
    # the grain pattern is centred on the object origin: keep the disc's rings round its own centre
    for v in disc.data.vertices:
        v.co.x -= c.x
        v.co.y -= c.y
    disc.location = (c.x, c.y, 0)
    return rim, disc


roots = []
for idx, (L, R, bend, seed) in enumerate(VARIANTS, 1):
    root = C.empty(f'Log{idx}Root', size=0.1)
    centre, radius = trunk_fn(L, R, bend, seed)
    bark_parts, char_parts = [], []
    trunk = tag(tube_mesh('Trunk', L, centre, radius, 0.0, L, RINGS), BARK, 0.9, 1)
    trunk['cf_scorch'], trunk['cf_scorch_z'] = 1.0, L * CHAR_FROM - 0.14    # heat-darkened below the char
    bark_parts.append(trunk)
    for z, up in ((0.0, -1), (L, 1)):
        rim, disc = end_face('EndGrain', centre, radius, z, up, 0.86)
        bark_parts.append(tag(rim, '#2f2016', 0.95, 0))
        bark_parts.append(tag(disc, WOOD, 0.85, 2))
    # branch stub: short tapering spur, sawn flush-ish
    a = seed * 2.1
    zc = L * (0.28 + 0.1 * (seed % 2))
    c0 = centre(zc)
    d = Vector((math.cos(a), math.sin(a), 0.55)).normalized()
    base = c0 + Vector((math.cos(a), math.sin(a), 0)) * radius(zc, a) * 0.6
    stub = C.sweep('Stub', [tuple(base), tuple(base + d * 0.03), tuple(base + d * 0.055)],
                   [R * 0.34, R * 0.3, R * 0.27], sides=8, cap_start=False, cap_end=True)
    bark_parts.append(tag(stub, BARK, 0.9, 1))

    # burning end: charred shell swelling out of the bark, rounded burnt tip
    z0 = L * CHAR_FROM
    swell = lambda z, z0=z0: 0.985 + 0.05 * min(1.0, max(0.0, z - z0 + 0.03) / 0.08)   # noqa: E731
    char = tube_mesh('CharShell', L, centre, radius, z0, L, 7, scale=swell,
                     tip=[(0.92, 0.012), (0.72, 0.024), (0.42, 0.032)], ragged=0.03, seed=seed)
    char_parts.append(tag(char, CHAR, 0.97, 4))

    for o in bark_parts + char_parts:
        o.parent = root
    roots.append((root, bark_parts, char_parts, L))

# lay the three rounds side by side in the .blend (each root is placed by the scene at runtime)
for i, (root, *_rest) in enumerate(roots):
    root.location = (0.25 * (i - 1), 0, 0)
bpy.context.view_layer.update()

all_parts = [o for _, b, c, _ in roots for o in b + c]
C.unwrap_uv1(all_parts, uv0_tile=0.1)
base_p, orm_p, nrm_p, emi_p = C.bake_weathering(
    all_parts, 'firewood', TEX, size=1024, dirt_height=0.0, fade=0.0, edge_wear=0.0, ao_distance=0.03,
    seed=23.0, patterns=True, normal_depth=0.004,
    glow_colors=('#4a0e02', '#ff5a12'))   # deep: the fire logic drives Charcoal up to ~2.3× (hotter → clips to white)
M_BARK = C.baked_material('Bark', base_p, orm_p, nrm_p, 1.0, normal_uv='UV1')
M_CHAR = C.baked_material('Charcoal', base_p, orm_p, nrm_p, 1.0, normal_uv='UV1',
                          emissive_path=emi_p, emissive_strength=1.0)

for root, bark_parts, char_parts, L in roots:
    for o in bark_parts:
        C.set_material(o, M_BARK)
    C.join(bark_parts, 'Bark')
    for o in char_parts:
        C.set_material(o, M_CHAR)
    ch = C.join(char_parts, 'CharEnd')
    ch['noCastShadow'] = True          # sits inside the flames; the bark already casts the log's shadow

print(f'[firewood] triangles: {C.triangle_count()}')
print(f'[firewood] exported {OUT_GLB} ({C.export_glb(OUT_GLB) / 1024:.0f} KB)')
print(f'[firewood] saved .blend ({C.save_blend(os.path.join(SRC, "firewood.blend")) / 1024:.0f} KB)')
if PREVIEW:
    C.preview(os.path.join(SRC, 'preview.png'), (0.75, -1.05, 0.55), (0, 0, 0.36), key_loc=(0.5, -0.9, 0.9))
    print('[firewood] preview rendered')
