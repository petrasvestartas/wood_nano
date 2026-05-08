#! python3
"""reciprocal_move — Rhino interactive example.

Translation-based reciprocal frame (nexorade via edge translation + trim).
Supply a Rhino mesh via the ``mesh`` input or a NURBS surface via ``surface``,
or leave both empty to use the built-in sinusoidal dome.
"""
import Rhino
import Rhino.Geometry as rg
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import reciprocal_move_elements, reciprocal_move_elements_from_surface, reciprocal_move_elements_from_mesh
from wood_nano.wood_element import unweld_mesh

session = Session()


def _extract_surface(rhino_srf):
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


def _extract_mesh(rhino_mesh: rg.Mesh):
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


def _run(v, _):
    if v["beam_w"] <= 0:
        Rhino.RhinoApp.WriteLine("beam_w must be positive.")
        return

    mesh_type    = v["mesh_type"]
    srfs         = v["surface"]
    meshes       = v["mesh"]
    beam_offsets = v["beam_offsets"] or None

    if meshes:
        verts, faces = _extract_mesh(meshes[0])
        dome, beams, side0, side1 = reciprocal_move_elements_from_mesh(
            verts, faces,
            angle=v["move"],
            beam_w=v["beam_w"],
            beam_h=v["beam_h"],
            beam_offsets=beam_offsets,
        )
        source_label = "[user mesh]"
    elif srfs:
        pts, ku, kv, du, dv, nu, nv = _extract_surface(srfs[0])
        dome, beams, side0, side1 = reciprocal_move_elements_from_surface(
            pts, ku, kv, du, dv, nu, nv,
            mesh_type=mesh_type,
            u_count=v["u_count"],
            v_count=v["v_count"],
            angle=v["move"],
            beam_w=v["beam_w"],
            beam_h=v["beam_h"],
            beam_offsets=beam_offsets,
        )
        source_label = f"[surface / {mesh_type}]"
    else:
        dome, beams, side0, side1 = reciprocal_move_elements(
            nx=v["u_count"],
            ny=v["v_count"],
            mesh_type=mesh_type,
            angle=v["move"],
            beam_w=v["beam_w"],
            beam_h=v["beam_h"],
            beam_offsets=beam_offsets,
        )
        source_label = f"[dome / {mesh_type}]"

    session.add(unweld_mesh(dome))
    for m in beams:
        session.add(m)
    for pl in side0:
        session.add(pl)
    for pl in side1:
        session.add(pl)
    session.draw()
    Rhino.RhinoApp.WriteLine(
        f"dome: {dome.number_of_faces()} faces  beams: {len(beams)}  {source_label}"
    )


process_input(
    {
        "mesh":          ([], list[rg.Mesh]),    # optional user mesh
        "surface":       ([], list[rg.Surface]), # optional NURBS surface
        # Subdivision (ignored when a mesh is provided)
        "mesh_type":     (["quad", "hex", "diamond"], list[str]),
        "u_count":       (6,      int),
        "v_count":       (6,      int),
        # Reciprocal move parameters
        "move":          (200.0,  float),   # translation distance in mm
        "beam_w":        (200.0,  float),
        "beam_h":        (400.0,  float),
        # Per-direction height offsets (along face normal): 2 values for quad/diamond, 3 for hex
        "beam_offsets":  ([], list[float]),
    },
    callback=_run,
)
