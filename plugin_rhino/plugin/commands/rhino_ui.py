#! python3
"""Shared Rhino geometry helpers used across wood_nano plugin commands.

Import specific helpers instead of importing the whole module:

    from rhino_ui import extract_mesh, extract_nurbs_surface
    from rhino_ui import expand_knots
    from rhino_ui import write_plate_userstring
"""
import scriptcontext as sc
import Rhino.Geometry as rg


def extract_mesh(rhino_mesh: rg.Mesh):
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


def extract_nurbs_surface(rhino_srf):
    """Extract control points and knots from a Rhino NURBS surface.

    Returns ``(pts, knots_u, knots_v, degree_u, degree_v, n_u, n_v)`` ready to
    pass directly to any ``*_from_surface`` or ``*_nurbs`` wood_nano function.
    """
    ns = rhino_srf.ToNurbsSurface()
    n_u, n_v = ns.Points.CountU, ns.Points.CountV
    pts = []
    for i in range(n_u):
        for j in range(n_v):
            _, p = ns.Points.GetPoint(i, j)
            pts.append([p.X, p.Y, p.Z])
    knots_u = [ns.KnotsU[i] for i in range(ns.KnotsU.Count)]
    knots_v = [ns.KnotsV[j] for j in range(ns.KnotsV.Count)]
    return pts, knots_u, knots_v, ns.Degree(0), ns.Degree(1), n_u, n_v


def expand_knots(mults, vals):
    """Expand knot multiplicity/value pairs into a flat knot vector.

    Strips the first and last entry to match the OpenNURBS convention expected
    by wood_nano's NURBS surface functions.
    """
    knots = []
    for m, v in zip(mults, vals):
        knots.extend([v] * m)
    return knots[1:-1]


def write_plate_userstring(plate_map, plate_id, key, value_str):
    """Write one UserString to bot/top objects of a plate.

    Operates only on the GUIDs collected during selection (plate_map) so that
    other copies of the same layout with identical plate_id values are not
    accidentally updated.
    """
    roles = plate_map.get(plate_id, {})
    for role in ("bot", "top"):
        guid = roles.get(role)
        if guid is None:
            continue
        obj = sc.doc.Objects.FindId(guid)
        if obj is None:
            continue
        obj.Attributes.SetUserString(key, value_str)
        obj.CommitChanges()
