from __future__ import annotations

from session_py.mesh import Mesh
from session_py.point import Point
from session_py.polyline import Polyline

from wood_nano import _joinery_solver
from wood_nano.wood_element import _to_mesh, _to_polyline


def _pts_to_polyline(pts: list) -> Polyline:
    return Polyline([Point(float(p[0]), float(p[1]), float(p[2])) for p in pts])


class JoineryElement:
    """Merged plate element returned by the joinery solver.

    Attributes
    ----------
    top_outlines : list[Polyline]
        Merged top-face cut outlines (outer boundary + notch holes).
    bottom_outlines : list[Polyline]
        Merged bottom-face cut outlines (outer boundary + notch holes).
    """

    def __init__(self, data: dict):
        self.top_outlines: list[Polyline] = [
            _pts_to_polyline(pts) for pts in data["top_outlines"]
        ]
        self.bottom_outlines: list[Polyline] = [
            _pts_to_polyline(pts) for pts in data["bottom_outlines"]
        ]
        self._mesh_data = data["loft_mesh"]

    def loft_mesh(self) -> Mesh:
        """Lofted solid mesh of the plate (bottom cap + top cap + side faces)."""
        return _to_mesh(self._mesh_data)


class JointResult:
    """Detected joint between two plate elements.

    Attributes
    ----------
    element_ids : tuple[int, int]
        Indices of the two participating elements.
    joint_type : int
        Joint type code (e.g. 30 = cross/lap joint).
    area : Polyline
        Closed quad polyline on the joint mid-plane.
    volumes : list[Polyline]
        Cut volume polylines bounding the joint region.
    lines : list[Polyline]
        Centerlines (2-point polylines) of the joint.
    """

    def __init__(self, data: dict):
        self.element_ids: tuple[int, int] = tuple(data["el_ids"])
        self.joint_type: int = int(data["joint_type"])
        self.area: Polyline = _pts_to_polyline(data["joint_area"])
        self.volumes: list[Polyline] = [
            _pts_to_polyline(pts) for pts in data["joint_volumes"]
        ]
        self.lines: list[Polyline] = [
            _pts_to_polyline(pts) for pts in data["joint_lines"]
        ]


# Search type constants (mirror of C++ SearchType enum)
SEARCH_FACE_TO_FACE = 0
SEARCH_CROSS_JOINT  = 1
SEARCH_BOTH         = 2


def joinery_solver_elements(
    bottom_polylines: list,
    top_polylines: list,
    search_type: int = SEARCH_CROSS_JOINT,
    joint_params: list | None = None,
    joint_volume_ext: list | None = None,
    per_element_insertion_vectors: list | None = None,
    per_element_joint_types: list | None = None,
    three_valence: list | None = None,
    adjacency: list | None = None,
    bottom_hole_polylines: list | None = None,
    top_hole_polylines: list | None = None,
) -> tuple[list[JoineryElement], list[JointResult]]:
    """Detect joinery between plate elements defined by bottom/top polyline pairs.

    Each pair (bottom_polylines[i], top_polylines[i]) defines one plate element.
    The wood cross-joint detection pipeline is run in C++ and the resulting
    merged cut outlines and joint geometry are returned.

    Parameters
    ----------
    bottom_polylines : list
        Bottom outline for each plate.  Each entry is either a session_py.Polyline
        or a list of [x, y, z] point triples.
    top_polylines : list
        Top outline for each plate.  Same length as bottom_polylines.
    search_type : int
        0 = face-to-face (coplanar), 1 = cross-joint (default), 2 = both.
    joint_params : list[float] or None
        Optional 21-element flat list overriding the C++ joint family defaults
        (7 families × 3 values: division_length, shift, type_id).
        ``None`` or empty list → use C++ ``reset_defaults()`` values.
    bottom_hole_polylines : list[list[Polyline]] or None
        Per-element lists of bottom hole outline polylines. None = no holes.
    top_hole_polylines : list[list[Polyline]] or None
        Per-element lists of top hole outline polylines. None = no holes.

    Returns
    -------
    tuple[list[JoineryElement], list[JointResult]]
        Per-element merged cut geometry and the list of detected joints.
    """
    if len(bottom_polylines) != len(top_polylines):
        raise ValueError(
            f"bottom_polylines ({len(bottom_polylines)}) and "
            f"top_polylines ({len(top_polylines)}) must have the same length."
        )

    def _to_pts(pl) -> list:
        """Accept session_py.Polyline or a raw list of [x,y,z].
        Each point must be a tuple so nanobind can coerce it to std::array<double,3>.
        """
        if hasattr(pl, "coords"):
            # session_py.Polyline: coords is a flat [x0,y0,z0, x1,y1,z1, ...]
            c = pl.coords
            return [(float(c[i]), float(c[i+1]), float(c[i+2]))
                    for i in range(0, len(c), 3)]
        # assume already list of [x,y,z]
        return [(float(p[0]), float(p[1]), float(p[2])) for p in pl]

    plates_data = []
    for i, (bot, top) in enumerate(zip(bottom_polylines, top_polylines)):
        plate = [_to_pts(bot), _to_pts(top)]
        if (bottom_hole_polylines and i < len(bottom_hole_polylines) and
                top_hole_polylines and i < len(top_hole_polylines)):
            for h_bot, h_top in zip(bottom_hole_polylines[i], top_hole_polylines[i]):
                plate.append(_to_pts(h_bot))
                plate.append(_to_pts(h_top))
        plates_data.append(plate)

    raw = _joinery_solver.solve_joinery(
        plates_data, int(search_type),
        joint_params     if joint_params     else [],
        joint_volume_ext if joint_volume_ext else [],
        [tuple(float(x) for x in iv) for iv in per_element_insertion_vectors]
            if per_element_insertion_vectors else [],
        [tuple(int(x)   for x in jt) for jt in per_element_joint_types]
            if per_element_joint_types       else [],
        [tuple(int(x)   for x in tv) for tv in three_valence]
            if three_valence                 else [],
        [(int(a), int(b)) for a, b in adjacency]
            if adjacency                     else [],
    )

    elements = [JoineryElement(d) for d in raw["elements"]]
    joints   = [JointResult(d)   for d in raw["joints"]]
    return elements, joints
