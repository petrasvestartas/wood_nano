from __future__ import annotations

from session_py import Polyline
from session_py.mesh import Mesh

from wood_nano._translation_shell import make_translation_shell, make_default_translation_shell
from wood_nano.wood_element import WoodElement, _to_mesh


def translation_shell_elements(
    cross_section: Polyline | None = None,
    profile: Polyline | None = None,
    thickness: float = 10.0,
    chamfer: float = 1.0,
    chamfer_angle: float = 180.0,
) -> tuple[Mesh, list[WoodElement]]:
    """Sweep cross_section along profile → shell mesh + plate elements.

    Parameters
    ----------
    cross_section : session_py.Polyline, optional
        Cross-section curve. None = C++ built-in arch.
    profile : session_py.Polyline, optional
        Sweep path. None = C++ built-in arch.
    chamfer : float
        Chamfer cut distance. 0 = no chamfer.
    chamfer_angle : float
        Corners sharper than this angle (degrees) are chamfered.
        0 = none, 180 = all corners.

    Returns
    -------
    tuple[session_py.Mesh, list[WoodElement]]
    """
    if cross_section is None and profile is None:
        ts = make_default_translation_shell(
            float(thickness), float(chamfer), float(chamfer_angle))
    else:
        if cross_section is None or profile is None:
            raise ValueError("Provide both cross_section and profile, or neither.")
        c, p = cross_section.coords, profile.coords
        ts = make_translation_shell(
            [c[i:i+3] for i in range(0, len(c), 3)],
            [p[i:i+3] for i in range(0, len(p), 3)],
            float(thickness), float(chamfer), float(chamfer_angle))

    return _to_mesh(ts.mesh), [WoodElement(e) for e in ts.elements]
