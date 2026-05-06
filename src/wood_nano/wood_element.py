from __future__ import annotations

from session_py.mesh import Mesh
from session_py.point import Point
from session_py.polyline import Polyline

from wood_nano import _wood_element


def _to_polyline(pts: list) -> Polyline:
    return Polyline([Point(float(p[0]), float(p[1]), float(p[2])) for p in pts])


def _to_mesh(r: dict) -> Mesh:
    pts = [Point(float(v[0]), float(v[1]), float(v[2])) for v in r["vertices"]]
    fcs = [list(map(int, f)) for f in r["faces"]]
    return Mesh.from_vertices_and_faces(pts, fcs)


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
