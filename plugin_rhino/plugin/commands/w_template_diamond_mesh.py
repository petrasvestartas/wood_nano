#! python3
# venv: wood_env
# r: wood-nano
from typing import Any

import Rhino
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import (
    diamond_mesh_elements,
    diamond_mesh_elements_from_surface,
)
from wood_nano.plate_topology import PlateTopology
from session_rhino.rhino_ui import extract_nurbs_surface

EXPLODE: bool = True  # True = each face separate; False = welded solid mesh

session: Session    = Session()
topo: PlateTopology = PlateTopology()
_srf_guids: list    = []


def _run(v: dict[str, Any], _: Any) -> None:
    global _srf_guids, _first_run

    # =========================================================================
    # RHINO UI — clear previous preview objects; extract input surface
    # =========================================================================
    doc = Rhino.RhinoDoc.ActiveDoc
    for g in _srf_guids:
        doc.Objects.Delete(g, True)
    _srf_guids.clear()

    u_div: int         = v["u_div"]
    v_div: int         = v["v_div"]
    thickness: float   = v["thickness"]
    chamfer: float     = v["chamfer"]
    chamfer_ang: float = v["chamfer_angle"]
    label: str

    if v["surface"]:
        pts, ku, kv, du, dv, nu, nv = extract_nurbs_surface(v["surface"][0])
        label = "[user surface]"
        # DEBUG — print NURBS control point structure
        Rhino.RhinoApp.WriteLine(f"NURBS: degree=({du},{dv})  n_u={nu}  n_v={nv}  total={len(pts)}")
        Rhino.RhinoApp.WriteLine(f"  knots_u len={len(ku)}: [{ku[0]:.2f} .. {ku[-1]:.2f}]")
        Rhino.RhinoApp.WriteLine(f"  knots_v len={len(kv)}: [{kv[0]:.2f} .. {kv[-1]:.2f}]")
        Rhino.RhinoApp.WriteLine("  Control pts [i*nv+j] -> (x, y, z):")
        for i in range(min(nu, 3)):
            for j in range(nv):
                p = pts[i * nv + j]
                Rhino.RhinoApp.WriteLine(f"    [{i},{j}] ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
        if nu > 3:
            Rhino.RhinoApp.WriteLine(f"    ... ({nu - 3} more rows)")
        # DEBUG — add NURBS control points so they can be compared to the Rhino surface
        for p in pts:
            g = doc.Objects.AddPoint(Rhino.Geometry.Point3d(p[0], p[1], p[2]))
            _srf_guids.append(g)
    else:
        label = "[default]"

    # =========================================================================
    # WOOD-NANO — compute shell elements
    # =========================================================================
    if v["surface"]:
        shell, elements = diamond_mesh_elements_from_surface(
            pts, ku, kv, du, dv, nu, nv,
            u_div=u_div, v_div=v_div,
            thickness=thickness, chamfer=chamfer, chamfer_angle=chamfer_ang,
        )
    else:
        shell, elements = diamond_mesh_elements(
            u_div=u_div, v_div=v_div,
            thickness=thickness, chamfer=chamfer, chamfer_angle=chamfer_ang,
        )

    # =========================================================================
    # RHINO UI — draw results
    # =========================================================================
    session.add(shell)
    session.draw()

    topo.clear()
    for i, el in enumerate(elements):
        topo.add_plate(i, el.bottom, el.top, el.loft_mesh_unwelded() if EXPLODE else el.loft_mesh())

    Rhino.RhinoApp.WriteLine(
        f"shell: {shell.number_of_faces()} faces  plates: {len(elements)}  {label}"
    )
    doc.Views.Redraw()


process_input(
    {
        "surface":       ([], list[Rhino.Geometry.Surface]),
        "u_div":         (5,      int),
        "v_div":         (2,      int),
        "thickness":     (-15.0,  float),
        "chamfer":       (30.0,   float),
        "chamfer_angle": (180.0,  float),
    },
    callback=_run,
)
