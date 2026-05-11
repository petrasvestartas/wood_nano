from __future__ import annotations

from session_py.polyline import Polyline

from wood_nano import _joinery_solver
from wood_nano.wood_element import _to_mesh


def loft(polylines0: list[Polyline], polylines1: list[Polyline]):
    """Loft two sets of polylines (bottom + top) into a closed mesh with hole support.

    polylines0 / polylines1 : list of Polyline
        Index 0 = outer boundary, indices 1+ = holes.

    Returns a session_py Mesh.
    """
    def _pts(pl):
        pts = pl.get_points() if hasattr(pl, "get_points") else list(pl)
        return [[float(p[0]), float(p[1]), float(p[2])] for p in pts]

    bot = [_pts(pl) for pl in polylines0]
    top = [_pts(pl) for pl in polylines1]
    return _to_mesh(_joinery_solver.loft(bot, top))
