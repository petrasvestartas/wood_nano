from __future__ import annotations

from session_py.plane import Plane
from session_py.point import Point
from session_py.polyline import Polyline
from session_py.vector import Vector

from wood_nano._connectors import make_default_vda_mesh, make_vda_mesh


def _to_polyline(raw: list) -> Polyline:
    return Polyline([Point(float(p[0]), float(p[1]), float(p[2])) for p in raw])


def _to_plane(d) -> Plane | None:
    if d is None:
        return None
    o = d["origin"]
    x = d["x_axis"]
    y = d["y_axis"]
    return Plane(
        Point(float(o[0]), float(o[1]), float(o[2])),
        Vector(float(x[0]), float(x[1]), float(x[2])),
        Vector(float(y[0]), float(y[1]), float(y[2])),
    )


def connectors_elements(
    mesh=None,
    face_thickness: float = 20.0,
    face_positions: tuple | list = (0.0,),
    edge_divisions: tuple | list = (2,),
    edge_division_len: tuple | list = (),
    insertion_lines: tuple | list = (),
    rect_width: float = 200.0,
    rect_height: float = 200.0,
    rect_thickness: float = 20.0,
):
    """Mesh-to-plates-and-connectors.

    Parameters
    ----------
    mesh : tuple[list, list] or None
        ``(vertices, faces)`` where *vertices* is a list of ``[x, y, z]`` and
        *faces* is a list of ``[i, j, k]`` / ``[i, j, k, l]`` index lists.
        Pass ``None`` to use the built-in default two-quad mesh.
    face_thickness : float
        Plate thickness along the face normal.
    face_positions : sequence of float
        Offsets along face normal where plates are placed (one layer each).
    edge_divisions : sequence of int
        Number of interior connector positions per edge (one value or one per edge).
    edge_division_len : sequence of float
        If non-empty, connector spacing is ``edge_length / division_len`` instead.
    insertion_lines : sequence of [[x0,y0,z0],[x1,y1,z1]]
        Lines that override connector orientation at matched edges.  Each line
        is matched to the nearest mesh edge by endpoint proximity; its direction
        is projected onto the edge plane to define the connector's x-axis.
        Pass an empty list (default) to use the automatic orientation.
    rect_width, rect_height : float
        Connector rectangle dimensions in the edge-perpendicular plane.
    rect_thickness : float
        Connector rectangle thickness along the edge direction.

    Returns
    -------
    tuple of six parallel nested lists
        ``(f_polylines, f_planes, f_index, e_polylines, e_planes, e_index)``

        * **f_polylines** ``list[list[Polyline]]`` — ``[face_i][pos_j*2+0/1]``
          bottom/top outlines per face per position layer.
        * **f_planes** ``list[list[Plane | None]]`` — top plane per face per layer.
        * **f_index** ``list[list[str]]`` — label string per face per layer.
        * **e_polylines** ``list[list[Polyline]]`` — ``[edge_i][div_j*2+0/1]``
          two connector rectangles per subdivision of each internal edge.
        * **e_planes** ``list[list[Plane | None]]`` — connector plane per subdivision.
        * **e_index** ``list[list[str]]`` — ``"f0-f1_j"`` label per subdivision.
    """
    fp  = list(face_positions)   or [0.0]
    ed  = list(edge_divisions)   or [2]
    edl = list(edge_division_len)
    ils = list(insertion_lines)

    if mesh is None:
        raw = make_default_vda_mesh(
            face_thickness, fp, ed, edl, ils,
            rect_width, rect_height, rect_thickness)
    else:
        verts, faces = mesh
        raw = make_vda_mesh(
            verts, faces,
            face_thickness, fp, ed, edl, ils,
            rect_width, rect_height, rect_thickness)

    f_polylines = [[_to_polyline(pl) for pl in row] for row in raw.f_polylines]
    f_planes    = [[_to_plane(pl)    for pl in row] for row in raw.f_polylines_planes]
    f_index     = [list(row)                        for row in raw.f_polylines_index]
    e_polylines = [[_to_polyline(pl) for pl in row] for row in raw.e_polylines]
    e_planes    = [[_to_plane(pl)    for pl in row] for row in raw.e_polylines_planes]
    e_index     = [list(row)                        for row in raw.e_polylines_index]

    return f_polylines, f_planes, f_index, e_polylines, e_planes, e_index
