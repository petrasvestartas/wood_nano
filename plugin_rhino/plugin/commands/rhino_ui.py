#! python3
# Compatibility shim — import from session_rhino.rhino_ui in new code.
from session_rhino.rhino_ui import (
    extract_mesh,
    extract_nurbs_surface,
    expand_knots,
    write_plate_userstring,
    dist_point_to_segment,
    get_polyline_points,
    cross,
    normalize,
    face_normal,
    loft_mesh_to_rhino,
)

__all__ = [
    "extract_mesh",
    "extract_nurbs_surface",
    "expand_knots",
    "write_plate_userstring",
    "dist_point_to_segment",
    "get_polyline_points",
    "cross",
    "normalize",
    "face_normal",
    "loft_mesh_to_rhino",
]
