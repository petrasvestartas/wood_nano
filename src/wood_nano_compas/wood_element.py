"""compas wrappers for C++ WoodElement, JoineryElement, and JointResult."""

from compas.datastructures import Mesh
from compas.geometry import Polyline

from wood_nano import _joinery_solver
from wood_nano_compas.convert import mesh_from_cpp, polyline_from_cpp


class WoodElementCompas:
    """compas adapter for C++ ``wood_session::WoodElement``."""

    def __init__(self, cpp_el):
        self._el = cpp_el

    @property
    def bottom(self) -> Polyline:
        return polyline_from_cpp(self._el.bottom)

    @property
    def top(self) -> Polyline:
        return polyline_from_cpp(self._el.top)

    @property
    def thickness(self) -> float:
        return float(self._el.thickness)

    def loft_mesh(self) -> Mesh:
        mesh = mesh_from_cpp(self._el.loft_mesh())
        mesh.unify_cycles()
        bot = self._el.bottom
        top = self._el.top
        bc = [sum(p[i] for p in bot) / len(bot) for i in range(3)]
        tc = [sum(p[i] for p in top) / len(top) for i in range(3)]
        up = [tc[i] - bc[i] for i in range(3)]
        n = mesh.normal()
        if n[0] * up[0] + n[1] * up[1] + n[2] * up[2] < 0:
            mesh.flip_cycles()
        return mesh


class JoineryElementCompas:
    """Merged plate element returned by the joinery solver."""

    def __init__(self, data: dict):
        self.top_outlines: list[Polyline] = [
            polyline_from_cpp(pts) for pts in data["top_outlines"]
        ]
        self.bottom_outlines: list[Polyline] = [
            polyline_from_cpp(pts) for pts in data["bottom_outlines"]
        ]

    def loft_mesh(self) -> Mesh:
        def _pts(pl): return [[float(p[0]), float(p[1]), float(p[2])] for p in pl.points]
        bot = [_pts(pl) for pl in self.bottom_outlines]
        top = [_pts(pl) for pl in self.top_outlines]
        mesh = mesh_from_cpp(_joinery_solver.loft(bot, top))
        mesh.unify_cycles()
        bc = [sum(p[i] for pts in bot for p in pts) / sum(len(pts) for pts in bot) for i in range(3)]
        tc = [sum(p[i] for pts in top for p in pts) / sum(len(pts) for pts in top) for i in range(3)]
        up = [tc[i] - bc[i] for i in range(3)]
        n = mesh.normal()
        if n[0] * up[0] + n[1] * up[1] + n[2] * up[2] < 0:
            mesh.flip_cycles()
        return mesh


class JointResultCompas:
    """Detected joint between two plate elements."""

    def __init__(self, data: dict):
        self.element_ids: tuple[int, int] = tuple(data["el_ids"])
        self.joint_type: int = int(data["joint_type"])
        self.area: Polyline = polyline_from_cpp(data["joint_area"])
        self.volumes: list[Polyline] = [polyline_from_cpp(pts) for pts in data["joint_volumes"]]
        self.lines: list[Polyline] = [polyline_from_cpp(pts) for pts in data["joint_lines"]]
