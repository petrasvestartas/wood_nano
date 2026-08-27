from __future__ import annotations

from session_py import Polyline
from session_py.mesh import Mesh

from wood_nano._reflex_fold import make_reflex_fold, make_default_reflex_fold
from wood_nano.wood_element import WoodElement, _to_mesh


def reflex_fold_elements(
    cross_section: Polyline | None = None,
    profile: Polyline | None = None,
    thickness: float = 10.0,
    chamfer: float = 20.0,
    chamfer_angle: float = 180.0,
) -> tuple[Mesh, list[WoodElement]]:
    """Fold profile along cross_section → shell mesh + plate elements.

    Parameters
    ----------
    cross_section : session_py.Polyline, optional
        Cross-section curve. None = C++ built-in fold geometry.
    profile : session_py.Polyline, optional
        Sweep path. None = C++ built-in fold geometry.
    chamfer : float
        Miter offset distance applied to both faces of each plate.
    chamfer_angle : float
        Interior corner angle threshold in degrees. Corners sharper than this
        receive the miter offset. 0 = no offset, 180 = offset all corners.

    Returns
    -------
    tuple[session_py.Mesh, list[WoodElement]]
    """
    if cross_section is None and profile is None:
        rf = make_default_reflex_fold(
            float(thickness), float(chamfer), float(chamfer_angle))
    else:
        if cross_section is None or profile is None:
            raise ValueError("Provide both cross_section and profile, or neither.")
        c, p = cross_section.coords, profile.coords
        rf = make_reflex_fold(
            [c[i:i+3] for i in range(0, len(c), 3)],
            [p[i:i+3] for i in range(0, len(p), 3)],
            float(thickness), float(chamfer), float(chamfer_angle))

    return _to_mesh(rf.mesh), [WoodElement(e) for e in rf.elements]
