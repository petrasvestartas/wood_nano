"""connectors — standalone Python example (no Rhino required).

Demonstrates the default two-quad mesh and a custom mesh with multiple
face layers and edge subdivisions.
"""
from wood_nano import connectors_elements

# ── default mesh ─────────────────────────────────────────────────────────────
f_pl, f_planes, f_idx, e_pl, e_planes, e_idx = connectors_elements()
print("=== default mesh (hex, 15 faces) ===")
print(f"faces           : {len(f_pl)}")
print(f"face polylines  : {sum(len(x) for x in f_pl)}  (2 per face = top+bot)")
print(f"edges           : {len(e_pl)}")
print(f"connectors      : {sum(len(x) for x in e_pl)}")
print()
for i, row in enumerate(f_pl):
    label = f_idx[i][0] if f_idx[i] else str(i)
    pts0 = len(row[0].get_points()) if row else 0
    print(f"  face {label}: {len(row)} polylines, bot has {pts0} pts")

print()
for i, row in enumerate(e_pl):
    if any(len(pl.get_points()) > 0 for pl in row):
        label = e_idx[i][0] if e_idx[i] else str(i)
        print(f"  edge {i} [{label}]: {len(row)} connector polylines")

# ── custom mesh: 2×2 grid of quads, two face layers ──────────────────────────
print()
print("=== custom 2×2 quad grid, 2 layers ===")

# 3×3 grid of vertices
verts = [
    [  0,   0, 0], [100,   0, 0], [200,   0, 0],
    [  0, 100, 0], [100, 100, 0], [200, 100, 0],
    [  0, 200, 0], [100, 200, 0], [200, 200, 0],
]
faces = [
    [0, 1, 4, 3],
    [1, 2, 5, 4],
    [3, 4, 7, 6],
    [4, 5, 8, 7],
]

f_pl2, f_planes2, f_idx2, e_pl2, e_planes2, e_idx2 = connectors_elements(
    mesh=(verts, faces),
    face_thickness=5.0,
    face_positions=[-10.0, 10.0],  # two layers
    edge_divisions=[3],
    rect_width=12.0,
    rect_height=12.0,
    rect_thickness=5.0,
)
print(f"faces           : {len(f_pl2)}")
print(f"face polylines  : {sum(len(x) for x in f_pl2)}  (4 per face = 2 layers × top+bot)")
print(f"edges           : {len(e_pl2)}")
print(f"connectors      : {sum(len(x) for x in e_pl2)}")
