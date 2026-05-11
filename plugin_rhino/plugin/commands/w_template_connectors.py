#! python3
# venv: wood_env
# r: wood-nano
"""connectors — Rhino interactive example.

Generates face plates (top/bottom outlines) and edge connector rectangles
from any mesh. Supply a Rhino mesh via the ``mesh`` input or leave it empty
to use the built-in default hex mesh.
"""
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import connectors_elements
from session_rhino.rhino_polyline import to_rhino as _pl_to_rhino
from wood_nano.plate_topology import PlateTopology

session = Session()
topo    = PlateTopology()


def _extract_mesh(rhino_mesh: rg.Mesh):
    """Convert a Rhino mesh (including ngons) to ``(vertices, faces)`` lists."""
    rhino_mesh.Weld(0.01)
    verts = [[v.X, v.Y, v.Z] for v in rhino_mesh.Vertices]

    ngon_face_indices = set()
    faces = []
    if rhino_mesh.Ngons.Count > 0:
        for i in range(rhino_mesh.Ngons.Count):
            ngon = rhino_mesh.Ngons[i]
            for fi in ngon.FaceIndexList():
                ngon_face_indices.add(fi)
            faces.append(list(ngon.BoundaryVertexIndexList()))

    for i, f in enumerate(rhino_mesh.Faces):
        if i in ngon_face_indices:
            continue
        if f.IsTriangle:
            faces.append([f.A, f.B, f.C])
        else:
            faces.append([f.A, f.B, f.C, f.D])

    return verts, faces


def _pt3d(p):
    return rg.Point3d(float(p[0]), float(p[1]), float(p[2]))


def _add_cap(mesh, vstart, n, reverse):
    """Add a polygonal cap face starting at vertex index vstart with n vertices."""
    vi = list(range(vstart, vstart + n))
    if reverse:
        vi = vi[::-1]
    if n == 3:
        mesh.Faces.AddFace(vi[0], vi[1], vi[2])
    elif n == 4:
        mesh.Faces.AddFace(vi[0], vi[1], vi[2], vi[3])
    else:
        # N-gon: fan-triangulate and register as Ngon so Rhino keeps it polygonal
        tri_fi = []
        for i in range(1, n - 1):
            fi = mesh.Faces.Count
            mesh.Faces.AddFace(vi[0], vi[i], vi[i + 1])
            tri_fi.append(fi)
        mesh.Ngons.AddNgon(rg.MeshNgon.Create(vi, tri_fi))


def _loft_panel(bot_pl, top_pl):
    """Loft two closed polylines into a flat-shaded polygonal solid mesh.

    Each face gets its own private vertices so normals are flat per face.
    Cap faces (n > 4) use fan triangulation registered as an Ngon so Rhino
    displays them as a single polygon rather than visible triangles.
    """
    bpts = bot_pl.get_points()
    tpts = top_pl.get_points()
    if len(bpts) < 4 or len(tpts) < 4:
        return None
    bp = [_pt3d(p) for p in bpts[:-1]]  # drop closing duplicate
    tp = [_pt3d(p) for p in tpts[:-1]]
    n = len(bp)
    if n != len(tp) or n < 3:
        return None

    mesh = rg.Mesh()

    # Bottom cap — own vertices (0 .. n-1), normal points down
    for p in bp:
        mesh.Vertices.Add(p)
    _add_cap(mesh, 0, n, reverse=True)

    # Top cap — own vertices (n .. 2n-1), normal points up
    for p in tp:
        mesh.Vertices.Add(p)
    _add_cap(mesh, n, n, reverse=False)

    # Side quads — each gets 4 private vertices so the face is flat-shaded
    for i in range(n):
        j = (i + 1) % n
        base = mesh.Vertices.Count
        mesh.Vertices.Add(tp[i])   # base+0
        mesh.Vertices.Add(bp[i])   # base+1
        mesh.Vertices.Add(bp[j])   # base+2
        mesh.Vertices.Add(tp[j])   # base+3
        mesh.Faces.AddFace(base, base + 1, base + 2, base + 3)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def _run(v, _):
    doc = sc.doc

    meshes        = v["mesh"]
    face_thick    = v["face_thickness"]
    face_pos      = v["face_positions"]
    edge_div      = v["edge_divisions"]
    edge_div_len  = v["edge_division_len"]
    rh_lines      = v["insertion_lines"]
    rw            = v["rect_width"]
    rh            = v["rect_height"]
    rt            = v["rect_thickness"]

    if meshes:
        mesh_arg = _extract_mesh(meshes[0])
        label    = "[user mesh]"
    else:
        mesh_arg = None
        label    = "[default]"

    # Convert Rhino Line objects to [[x0,y0,z0],[x1,y1,z1]] pairs
    ils = [
        [[ln.From.X, ln.From.Y, ln.From.Z], [ln.To.X, ln.To.Y, ln.To.Z]]
        for ln in rh_lines
    ]

    f_pl, f_planes, f_idx, e_pl, e_planes, e_idx = connectors_elements(
        mesh=mesh_arg,
        face_thickness=face_thick,
        face_positions=face_pos,
        edge_divisions=edge_div,
        edge_division_len=edge_div_len,
        insertion_lines=ils,
        rect_width=rw,
        rect_height=rh,
        rect_thickness=rt,
    )

    # Add face plates and edge connectors with persistent topology tagging.
    # Each (bot, top) polyline pair at positions [j, j+1] in a row is one plate.
    # Loft meshes are RhinoCommon-native (from _loft_panel), so use add_plate_rh.
    topo.clear()
    face_mesh_count = 0
    face_id = 0
    for face_row in f_pl:
        for j in range(0, len(face_row) - 1, 2):
            bot, top = face_row[j], face_row[j + 1]
            if len(bot.get_points()) < 2:
                continue
            rh_mesh = _loft_panel(bot, top)
            topo.add_plate_rh(face_id, _pl_to_rhino(bot), _pl_to_rhino(top), rh_mesh,
                              plate_type="face")
            if rh_mesh:
                face_mesh_count += 1
            face_id += 1

    edge_id = face_id  # continue from face IDs so plate_id is globally unique
    for edge_row in e_pl:
        for j in range(0, len(edge_row) - 1, 2):
            bot, top = edge_row[j], edge_row[j + 1]
            if len(bot.get_points()) < 2 or len(top.get_points()) < 2:
                continue
            rh_mesh = _loft_panel(bot, top)
            topo.add_plate_rh(edge_id, _pl_to_rhino(bot), _pl_to_rhino(top), rh_mesh,
                              plate_type="edge")
            edge_id += 1

    session.draw()
    doc.Views.Redraw()

    Rhino.RhinoApp.WriteLine(
        f"faces: {len(f_pl)}  face plates: {face_id}"
        f"  edge connectors: {edge_id - face_id}"
        f"  face meshes: {face_mesh_count}"
        f"  {label}"
    )


process_input(
    {
        "mesh":             ([], list[rg.Mesh]),   # optional; overrides default
        "face_thickness":   (20.0,  float),
        "face_positions":   ([0.0], list[float]),  # multiple values = multiple panel layers e.g. [-50.0, 50.0]
        "edge_divisions":   ([2],   list[int]),    # integer connector count per edge (ignored if edge_division_len set)
        "edge_division_len":([], list[float]),     # connector spacing by length; overrides edge_divisions when non-empty
        "insertion_lines":  ([], list[rg.Line]),   # lines whose direction overrides connector orientation at matched edges
        "rect_width":       (200.0,  float),
        "rect_height":      (300.0,  float),
        "rect_thickness":   (20.0,   float),
    },
    callback=_run,
)
