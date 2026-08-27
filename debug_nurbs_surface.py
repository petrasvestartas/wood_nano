"""
Debug: are the NURBS surfaces in the annen-JSON path and the Rhino-user path equivalent?

The annen path (make_diamond_mesh_annen) loads the JSON surface and passes it
directly to DiamondMesh — no transpose.

The Rhino path (make_diamond_mesh_from_surface) passes raw pts/knots and then
explicitly calls srf.transpose() before DiamondMesh.

This script feeds annen surface 0 through BOTH paths and compares the mesh
vertices.  If there is a transpose mismatch the meshes will be rotated 90°.
"""
from __future__ import annotations

import json
from pathlib import Path

from wood_nano import (
    diamond_mesh_elements_annen,
    diamond_mesh_elements_from_surface,
)

# ---------------------------------------------------------------------------
# Load annen surface 0 from JSON — same data as the C++ loader
# ---------------------------------------------------------------------------
DATA = Path(__file__).parent / "src/wood_nano/data/annen_surfaces.json"
with open(DATA) as f:
    annen = json.load(f)

s = annen[0]
degree_u: int = s["degree_u"]
degree_v: int = s["degree_v"]
n_u:      int = s["n_u"]
n_v:      int = s["n_v"]
u_mults:  list = s["u_mults"]
v_mults:  list = s["v_mults"]
u_vals:   list = s["u_nurbsknots"]
v_vals:   list = s["v_nurbsknots"]
pts_2d:   list = s["points"]  # pts_2d[i][j] = [x,y,z],  i=u, j=v

print(f"Surface 0: degree_u={degree_u} degree_v={degree_v}  n_u={n_u} n_v={n_v}")

# Expand multiplicity knot vectors and strip first/last (OpenNURBS format)
def expand_knots(mults: list, vals: list) -> list:
    full = []
    for m, v in zip(mults, vals):
        full.extend([v] * m)
    return full[1:-1]  # strip first and last

knots_u = expand_knots(u_mults, u_vals)
knots_v = expand_knots(v_mults, v_vals)
print(f"  knots_u len={len(knots_u)}  knots_v len={len(knots_v)}")

# Flatten pts_2d[i][j] → flat list mimicking extract_nurbs_surface output
pts_flat = [pts_2d[i][j] for i in range(n_u) for j in range(n_v)]
print(f"  pts_flat len={len(pts_flat)}  (expected n_u*n_v={n_u*n_v})")

# ---------------------------------------------------------------------------
# Path A — annen loader (no transpose in binding)
# ---------------------------------------------------------------------------
U_DIV, V_DIV = 5, 2
THICK, CHAMP, CHAMP_ANG = -15.0, 30.0, 180.0

shell_a, elems_a = diamond_mesh_elements_annen(
    json_path=str(DATA),
    surface_idx=0,
    u_div=U_DIV, v_div=V_DIV,
    thickness=THICK, chamfer=CHAMP, chamfer_angle=CHAMP_ANG,
)

# ---------------------------------------------------------------------------
# Path B — user-surface (from_surface) that adds srf.transpose() in C++
# ---------------------------------------------------------------------------
shell_b, elems_b = diamond_mesh_elements_from_surface(
    pts_flat, knots_u, knots_v, degree_u, degree_v, n_u, n_v,
    u_div=U_DIV, v_div=V_DIV,
    thickness=THICK, chamfer=CHAMP, chamfer_angle=CHAMP_ANG,
)

# ---------------------------------------------------------------------------
# Compare meshes
# ---------------------------------------------------------------------------
import numpy as np

verts_a, _ = shell_a.to_vertices_and_faces()
verts_b, _ = shell_b.to_vertices_and_faces()

print(f"\nPath A (annen):         {shell_a.number_of_vertices()} vertices  {shell_a.number_of_faces()} faces")
print(f"Path B (from_surface):  {shell_b.number_of_vertices()} vertices  {shell_b.number_of_faces()} faces")

if len(verts_a) != len(verts_b):
    print("\nVERTEX COUNT DIFFERS — meshes are not equivalent (likely transpose bug)")
else:
    va = np.array([[p[0], p[1], p[2]] for p in verts_a])
    vb = np.array([[p[0], p[1], p[2]] for p in verts_b])
    diff = np.abs(va - vb)
    max_diff = diff.max()
    print(f"\nMax vertex deviation between A and B: {max_diff:.6f}")
    if max_diff < 1.0:
        print("  -> MATCH: both paths produce the same surface")
    else:
        print("  -> MISMATCH: paths diverge — check transpose logic")

# ---------------------------------------------------------------------------
# Print bounding boxes to see if surfaces are rotated vs. each other
# ---------------------------------------------------------------------------
for label, shell in [("Path A (annen)", shell_a), ("Path B (from_surface)", shell_b)]:
    raw_verts, _ = shell.to_vertices_and_faces()
    arr = np.array([[p[0], p[1], p[2]] for p in raw_verts])
    lo, hi = arr.min(axis=0), arr.max(axis=0)
    span = hi - lo
    print(f"\n{label} bbox:")
    print(f"  X: [{lo[0]:.1f}, {hi[0]:.1f}]  span={span[0]:.1f}")
    print(f"  Y: [{lo[1]:.1f}, {hi[1]:.1f}]  span={span[1]:.1f}")
    print(f"  Z: [{lo[2]:.1f}, {hi[2]:.1f}]  span={span[2]:.1f}")

# ---------------------------------------------------------------------------
# Also check first element's bottom polyline to see orientation
# ---------------------------------------------------------------------------
print("\n--- First element bottom polyline (first 3 pts) ---")
def first3(el):
    pts = [el.bottom.point(i) for i in range(min(3, el.bottom.point_count()))]
    return [(round(p.x,1), round(p.y,1), round(p.z,1)) for p in pts]
print(f"  Path A (annen / no-transpose): {first3(elems_a[0])}")
print(f"  Path B (from_surface / transpose): {first3(elems_b[0])}")
