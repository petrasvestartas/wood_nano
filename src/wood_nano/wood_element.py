from __future__ import annotations

from session_py.mesh import Mesh
from session_py.point import Point
from session_py.polyline import Polyline

from . import _wood_element


def _to_polyline(pts: list) -> Polyline:
    return Polyline([Point(float(p[0]), float(p[1]), float(p[2])) for p in pts])


def unweld_mesh(mesh: Mesh) -> Mesh:
    """Return a copy of mesh with per-face vertex copies (flat shading).

    Triangulation is remapped so that polygon faces (n>4) remain grouped
    as ngons in Rhino rather than being split into visible triangles/quads.
    Computation delegated to C++ (_wood_element.unweld_mesh_dict).
    """
    sorted_vkeys = sorted(mesh.vertex.keys())
    sorted_fkeys = sorted(mesh.face.keys())
    vk_to_idx = {vk: i for i, vk in enumerate(sorted_vkeys)}
    verts = [[float(mesh.vertex[vk][0]), float(mesh.vertex[vk][1]), float(mesh.vertex[vk][2])]
             for vk in sorted_vkeys]
    faces = [[vk_to_idx[vk] for vk in mesh.face[fk]] for fk in sorted_fkeys]
    face_tris = [[list(t) for t in mesh.triangulation.get(fk, [])] for fk in sorted_fkeys]
    return _to_mesh(_wood_element.unweld_mesh_dict(verts, faces, face_tris))


def _to_mesh(r: dict) -> Mesh:
    vr = r["vertices"]
    # ndarray rows indexed one scalar at a time are ~10x slower than a single
    # bulk tolist(); unweld_mesh_dict returns plain lists, hence the guard.
    rows = vr.tolist() if hasattr(vr, "tolist") else vr
    pts = [Point(float(x), float(y), float(z)) for x, y, z in rows]
    fcs = [list(map(int, f)) for f in r["faces"]]
    mesh = Mesh.from_vertices_and_faces(pts, fcs)
    # Populate triangulation for n>3 faces so to_rhino uses the welded-with-Ngons
    # path (showing original cell boundaries) instead of CDT/exploded path.
    # Vertex keys equal compact indices (0..n-1) because add_vertex starts at 0.
    face_tris = r.get("face_tris")
    if face_tris:
        for fk, tris in zip(sorted(mesh.face.keys()), face_tris):
            if tris:
                mesh.triangulation[fk] = [tuple(t) for t in tris]
    face_holes = r.get("face_holes")
    if face_holes:
        for fk_str, rings in face_holes.items():
            mesh.face_holes[int(fk_str)] = [list(map(int, ring)) for ring in rings]
    return mesh


class WoodElement:
    """session_py type adapter for C++ wood_session::WoodElement."""

    def __init__(self, cpp_el: _wood_element.WoodElement):
        self._el = cpp_el

    @property
    def bottom(self) -> Polyline:
        return _to_polyline(self._el.bottom)

    @property
    def top(self) -> Polyline:
        return _to_polyline(self._el.top)

    @property
    def thickness(self) -> float:
        return self._el.thickness

    def loft_mesh(self) -> Mesh:
        return _to_mesh(self._el.loft_mesh())

    def loft_mesh_unwelded(self) -> dict:
        """Return loft mesh with per-face vertex copies (flat shading), computed in C++.

        Returns the raw C++ dict (vertices, faces, face_tris) — bypasses session_py.Mesh
        so PlateTopology.add_plate can convert directly to Rhino.Geometry.Mesh via
        session_rhino.rhino_mesh.to_rhino_from_dict, skipping one _to_mesh round-trip.
        """
        return self._el.unweld_loft_mesh()
