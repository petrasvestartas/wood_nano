#! python3
"""Raw CDT triangulation debug — plate_failing (15-vert outer + 4 holes).

Layers:
  Debug::InputTop    — input TOP polylines (outer + holes) as curves
  Debug::InputBot    — input BOT polylines (outer + holes) as curves
  Debug::Cap0        — face_tris[0] triangles, compact re-indexed vertices
  Debug::Cap1        — face_tris[1] triangles, compact re-indexed vertices
  Debug::Walls       — side wall quads (raw_faces where face_tris is None)
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.DocObjects as rdo
import System.Drawing
import scriptcontext as sc

from wood_nano._joinery_solver import solve_joinery

doc = sc.doc

# ── hardcoded plate_failing coordinates ───────────────────────────────────────

TOP_OUTER = [
    [ 711.660594, -1906.59468,  1126.880036],
    [ 605.549364, -1835.85386,   967.713191],
    [ 601.577501, -1801.190331,  985.767113],
    [  90.899853, -1460.738565,  219.75064 ],
    [  94.871715, -1495.402095,  201.696718],
    [  -9.83197,  -1425.599638,   44.641191],
    [ -25.439949, -1439.194318,    3.229221],
    [ -25.439949, -1893.0,       -337.12504 ],
    [ -12.023541, -1917.0,       -328.292224],
    [  75.988181, -1917.0,       -152.26878 ],
    [ 104.290124, -2011.339811,  -166.419752],
    [ 649.926131, -2011.339811,   924.852263],
    [ 621.624188, -1917.0,        939.003234],
    [ 713.852165, -1917.0,       1123.459189],
    [ 711.660594, -1906.59468,  1126.880036],
]
TOP_HOLE1 = [
    [ 308.393555, -1964.169906,  277.16454 ],
    [ 199.266354, -1964.169906,   58.910137],
    [ 185.115382, -1917.0,        65.985623],
    [ 294.242584, -1917.0,       284.240026],
    [ 308.393555, -1964.169906,  277.16454 ],
]
TOP_HOLE2 = [
    [ 526.647958, -1964.169906,  713.673346],
    [ 417.520757, -1964.169906,  495.418943],
    [ 403.369785, -1917.0,       502.494429],
    [ 512.496987, -1917.0,       720.748832],
    [ 526.647958, -1964.169906,  713.673346],
]
TOP_HOLE3 = [
    [ 401.278305, -1699.673154,  661.306602],
    [ 503.413834, -1767.763507,  814.509897],
    [ 507.385697, -1802.427037,  796.455975],
    [ 405.250167, -1734.336684,  643.25268 ],
    [ 401.278305, -1699.673154,  661.306602],
]
TOP_HOLE4 = [
    [ 197.007245, -1563.492448,  354.900013],
    [ 299.142775, -1631.582801,  508.103307],
    [ 303.114638, -1666.246331,  490.049386],
    [ 200.979108, -1598.155978,  336.846091],
    [ 197.007245, -1563.492448,  354.900013],
]
BOT_OUTER = [
    [ 734.392021, -1906.59468,  1101.588031],
    [ 632.396858, -1838.597905,  948.595287],
    [ 624.453132, -1769.270846,  984.70313 ],
    [ 113.775484, -1428.81908,   218.686657],
    [ 121.719209, -1498.146139,  182.578814],
    [  15.607979, -1427.40532,    23.411969],
    [   0.0,      -1441.0,        -18.0     ],
    [   0.0,      -1893.0,       -357.0     ],
    [  13.416408, -1917.0,       -348.167184],
    [ 104.290124, -1917.0,       -166.419752],
    [ 118.441096, -1964.169906,  -173.495238],
    [ 664.077103, -1964.169906,   917.776777],
    [ 649.926131, -1917.0,        924.852263],
    [ 736.583592, -1917.0,       1098.167184],
    [ 734.392021, -1906.59468,  1101.588031],
]
BOT_HOLE1 = [
    [ 322.544527, -1917.0,       270.089054],
    [ 213.417326, -1917.0,        51.834651],
    [ 199.266354, -1869.830094,   58.910137],
    [ 308.393555, -1869.830094,  277.16454 ],
    [ 322.544527, -1917.0,       270.089054],
]
BOT_HOLE2 = [
    [ 540.79893,  -1917.0,       706.59786 ],
    [ 431.671728, -1917.0,       488.343457],
    [ 417.520757, -1869.830094,  495.418943],
    [ 526.647958, -1869.830094,  713.673346],
    [ 540.79893,  -1917.0,       706.59786 ],
]
BOT_HOLE3 = [
    [ 424.153936, -1667.753669,  660.242619],
    [ 526.289465, -1735.844022,  813.445914],
    [ 530.261328, -1770.507552,  795.391992],
    [ 428.125798, -1702.417199,  642.188697],
    [ 424.153936, -1667.753669,  660.242619],
]
BOT_HOLE4 = [
    [ 219.882876, -1531.572963,  353.83603 ],
    [ 322.018406, -1599.663316,  507.039325],
    [ 325.990269, -1634.326846,  488.985403],
    [ 223.854739, -1566.236493,  335.782108],
    [ 219.882876, -1531.572963,  353.83603 ],
]

TOP_RINGS = [TOP_OUTER, TOP_HOLE1, TOP_HOLE2, TOP_HOLE3, TOP_HOLE4]
BOT_RINGS = [BOT_OUTER, BOT_HOLE1, BOT_HOLE2, BOT_HOLE3, BOT_HOLE4]

plates = [[
    BOT_OUTER, TOP_OUTER,
    BOT_HOLE1, TOP_HOLE1,
    BOT_HOLE2, TOP_HOLE2,
    BOT_HOLE3, TOP_HOLE3,
    BOT_HOLE4, TOP_HOLE4,
]]

# ── layer helpers ─────────────────────────────────────────────────────────────
LAYER_DEFS = {
    "InputTop": (255, 80,  40),
    "InputBot": (40,  120, 255),
    "Cap0":     (200, 60,  200),
    "Cap1":     (60,  200, 200),
    "Walls":    (120, 200, 80),
}

def _ensure_layer(child, r, g, b):
    full = f"Debug::{child}"
    idx = doc.Layers.FindByFullPath(full, -1)
    if idx >= 0:
        return idx
    parent_idx = doc.Layers.FindByFullPath("Debug", -1)
    layer = rdo.Layer()
    layer.Name = child
    layer.Color = System.Drawing.Color.FromArgb(r, g, b)
    if parent_idx >= 0:
        layer.ParentLayerId = doc.Layers[parent_idx].Id
    return doc.Layers.Add(layer)

def _clear_layer(child):
    full = f"Debug::{child}"
    old = doc.Objects.FindByLayer(full)
    if old:
        for o in old:
            doc.Objects.Delete(o, True)

def _add(geom, child, name=""):
    a = rdo.ObjectAttributes()
    a.LayerIndex = layer_idx[child]
    if name:
        a.Name = name
    if isinstance(geom, rg.Mesh):
        doc.Objects.AddMesh(geom, a)
    elif isinstance(geom, rg.Polyline):
        doc.Objects.AddPolyline(geom, a)
    elif isinstance(geom, rg.PolylineCurve):
        doc.Objects.AddCurve(geom, a)

layer_idx = {}
for child, (r, g, b) in LAYER_DEFS.items():
    _clear_layer(child)
    layer_idx[child] = _ensure_layer(child, r, g, b)


# ── draw input polylines ──────────────────────────────────────────────────────
def _draw_rings(rings, layer_key, prefix):
    for i, ring in enumerate(rings):
        pts = [rg.Point3d(p[0], p[1], p[2]) for p in ring]
        pl = rg.Polyline(pts)
        _add(pl, layer_key, f"{prefix}_{i}")

_draw_rings(TOP_RINGS, "InputTop", "top")
_draw_rings(BOT_RINGS, "InputBot", "bot")
print("Input polylines drawn.")


# ── run C++ solver ────────────────────────────────────────────────────────────
result   = solve_joinery(plates, search_type=0)
elements = result["elements"]
print(f"elements: {len(elements)}")


# ── build compact mesh from triangles (re-indexed) ────────────────────────────
def _make_mesh_from_tris(all_verts_np, tri_lists, label):
    old_to_new = {}
    new_verts  = []
    faces      = []
    for tri_list in tri_lists:
        if tri_list is None:
            continue
        for tri in tri_list:
            if len(tri) != 3 or any(t < 0 for t in tri):
                continue
            mapped = []
            for vi in tri:
                if vi not in old_to_new:
                    old_to_new[vi] = len(new_verts)
                    v = all_verts_np[vi]
                    new_verts.append(v)
                mapped.append(old_to_new[vi])
            faces.append(mapped)

    if not faces:
        return None

    # Print bounding box of vertices used so user can verify top vs bot
    xs = [v[0] for v in new_verts]
    ys = [v[1] for v in new_verts]
    zs = [v[2] for v in new_verts]
    print(f"  {label}: {len(new_verts)} verts  {len(faces)} tris")
    print(f"    X=[{min(xs):.1f}..{max(xs):.1f}]  Y=[{min(ys):.1f}..{max(ys):.1f}]  Z=[{min(zs):.1f}..{max(zs):.1f}]")

    m = rg.Mesh()
    for v in new_verts:
        m.Vertices.Add(float(v[0]), float(v[1]), float(v[2]))
    for f in faces:
        m.Faces.AddFace(f[0], f[1], f[2])
    m.Normals.ComputeNormals()
    m.Compact()
    return m


def _make_mesh_from_quads(all_verts_np, quad_lists, label):
    old_to_new = {}
    new_verts  = []
    faces      = []
    for f in quad_lists:
        if len(f) < 3:
            continue
        mapped = []
        for vi in f:
            if vi not in old_to_new:
                old_to_new[vi] = len(new_verts)
                new_verts.append(all_verts_np[vi])
            mapped.append(old_to_new[vi])
        faces.append(mapped)

    if not faces:
        return None
    print(f"  {label}: {len(new_verts)} verts  {len(faces)} quads")
    m = rg.Mesh()
    for v in new_verts:
        m.Vertices.Add(float(v[0]), float(v[1]), float(v[2]))
    for f in faces:
        if len(f) == 3:
            m.Faces.AddFace(f[0], f[1], f[2])
        else:
            m.Faces.AddFace(f[0], f[1], f[2], f[3])
    m.Normals.ComputeNormals()
    m.Compact()
    return m


# ── process elements ──────────────────────────────────────────────────────────
for ei, el in enumerate(elements):
    lm        = el.get("loft_mesh", {})
    verts_np  = lm.get("vertices")
    face_tris = lm.get("face_tris", [])
    raw_faces = lm.get("faces", [])

    if verts_np is None:
        print(f"elem {ei}: no vertices"); continue

    print(f"elem {ei}: total_verts={verts_np.shape}  faces={len(raw_faces)}  face_tris={len(face_tris)}")

    cap_tris   = []
    wall_quads = []
    for fi, tri_list in enumerate(face_tris):
        if tri_list is not None:
            print(f"  face {fi}: CDT  {len(tri_list)} tris")
            cap_tris.append(tri_list)
        else:
            if fi < len(raw_faces):
                wall_quads.append(raw_faces[fi])

    print(f"  cap faces={len(cap_tris)}  wall faces={len(wall_quads)}")

    if len(cap_tris) >= 1:
        m = _make_mesh_from_tris(verts_np, [cap_tris[0]], "Cap0")
        if m:
            _add(m, "Cap0", f"cap0_{ei}")

    if len(cap_tris) >= 2:
        m = _make_mesh_from_tris(verts_np, [cap_tris[1]], "Cap1")
        if m:
            _add(m, "Cap1", f"cap1_{ei}")

    m = _make_mesh_from_quads(verts_np, wall_quads, "Walls")
    if m:
        _add(m, "Walls", f"walls_{ei}")

doc.Views.Redraw()
print("done")
print("  Debug::InputTop  — orange curves = TOP input polylines")
print("  Debug::InputBot  — blue curves   = BOT input polylines")
print("  Debug::Cap0      — face_tris[0] triangles")
print("  Debug::Cap1      — face_tris[1] triangles")
print("  Debug::Walls     — side wall quads")
print("Check X range in print above: TOP outer ~711, BOT outer ~734")
