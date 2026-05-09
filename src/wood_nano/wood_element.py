from __future__ import annotations

from session_py.mesh import Mesh
from session_py.point import Point
from session_py.polyline import Polyline

from wood_nano import _wood_element


def _to_polyline(pts: list) -> Polyline:
    return Polyline([Point(float(p[0]), float(p[1]), float(p[2])) for p in pts])


def unweld_mesh(mesh: Mesh) -> Mesh:
    """Return a copy of mesh with per-face vertex copies (flat shading).

    Triangulation is remapped so that polygon faces (n>4) remain grouped
    as ngons in Rhino rather than being split into visible triangles/quads.
    """
    face_keys = sorted(mesh.face.keys())
    new_pts, new_faces, vi = [], [], 0
    vk_remap = {}  # (old_face_key, old_vertex_key) -> new_vertex_key
    for fk in face_keys:
        vkeys = mesh.face[fk]
        face_verts = []
        for vk in vkeys:
            p = mesh.vertex[vk]
            new_pts.append(Point(float(p[0]), float(p[1]), float(p[2])))
            vk_remap[(fk, vk)] = vi
            face_verts.append(vi)
            vi += 1
        new_faces.append(face_verts)
    new_mesh = Mesh.from_vertices_and_faces(new_pts, new_faces)
    new_face_keys = sorted(new_mesh.face.keys())
    for old_fk, new_fk in zip(face_keys, new_face_keys):
        tris = mesh.triangulation.get(old_fk)
        if tris:
            new_mesh.triangulation[new_fk] = [
                [vk_remap.get((old_fk, v), v) for v in tri] for tri in tris
            ]
    return new_mesh


def _to_mesh(r: dict) -> Mesh:
    pts = [Point(float(v[0]), float(v[1]), float(v[2])) for v in r["vertices"]]
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
