#! python3
"""vda_mesh — Rhino interactive example.

Generates face plates (top/bottom outlines) and edge connector rectangles
from any mesh. Supply a Rhino mesh via the ``mesh`` input or leave it empty
to use the built-in default hex mesh.
"""
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import vda_mesh_elements

session     = Session()
_first_run  = True
_mesh_guids = []  # tracks lofted panel/connector meshes added directly to the doc


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
    global _first_run, _mesh_guids
    doc = sc.doc

    for guid in _mesh_guids:
        doc.Objects.Delete(guid, True)
    _mesh_guids = []

    meshes        = v["mesh"]
    face_thick    = v["face_thickness"]
    face_pos      = v["face_positions"]
    edge_div      = v["edge_divisions"]
    edge_div_len  = v["edge_division_len"]
    rw            = v["rect_width"]
    rh            = v["rect_height"]
    rt            = v["rect_thickness"]

    if meshes:
        mesh_arg = _extract_mesh(meshes[0])
        label    = "[user mesh]"
    else:
        mesh_arg = None
        label    = "[default]"

    f_pl, f_planes, f_idx, e_pl, e_planes, e_idx = vda_mesh_elements(
        mesh=mesh_arg,
        face_thickness=face_thick,
        face_positions=face_pos,
        edge_divisions=edge_div,
        edge_division_len=edge_div_len,
        rect_width=rw,
        rect_height=rh,
        rect_thickness=rt,
    )

    # Polyline outlines
    for face_row in f_pl:
        for pl in face_row:
            if len(pl.get_points()) > 1:
                session.add(pl)

    for edge_row in e_pl:
        for pl in edge_row:
            if len(pl.get_points()) > 1:
                session.add(pl)

    # Lofted solid meshes (panels + connectors)
    for face_row in f_pl:
        for j in range(0, len(face_row) - 1, 2):
            m = _loft_panel(face_row[j], face_row[j + 1])
            if m:
                _mesh_guids.append(doc.Objects.AddMesh(m))

    for edge_row in e_pl:
        for j in range(0, len(edge_row) - 1, 2):
            bot, top = edge_row[j], edge_row[j + 1]
            if len(bot.get_points()) > 1 and len(top.get_points()) > 1:
                m = _loft_panel(bot, top)
                if m:
                    _mesh_guids.append(doc.Objects.AddMesh(m))

    session.draw()
    doc.Views.Redraw()

    n_face_pl = sum(len(r) for r in f_pl)
    n_edge_pl = sum(len(r) for r in e_pl if any(len(p.get_points()) > 1 for p in r))
    Rhino.RhinoApp.WriteLine(
        f"faces: {len(f_pl)}  face polylines: {n_face_pl}"
        f"  internal edges: {n_edge_pl // 2}"
        f"  meshes: {len(_mesh_guids)}"
        f"  {label}"
    )


process_input(
    {
        "mesh":             ([], list[rg.Mesh]),   # optional; overrides default
        "face_thickness":   (20.0,  float),
        "face_positions":   ([0.0], list[float]),  # multiple values = multiple panel layers e.g. [-50.0, 50.0]
        "edge_divisions":   ([2],   list[int]),    # integer connector count per edge (ignored if edge_division_len set)
        "edge_division_len":([], list[float]),     # connector spacing by length; overrides edge_divisions when non-empty
        "rect_width":       (200.0,  float),
        "rect_height":      (200.0,  float),
        "rect_thickness":   (20.0,   float),
    },
    callback=_run,
)
