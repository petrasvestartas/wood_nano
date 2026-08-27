#! python3
# venv: wood_env
# r: wood-nano
from typing import Any

import Rhino

from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import reflex_fold_elements
from wood_nano.plate_topology import PlateTopology

EXPLODE: bool = True  # True = each face separate; False = welded solid mesh

session: Session    = Session()
topo: PlateTopology = PlateTopology()


def _run(v: dict[str, Any], _: Any) -> None:
    # =========================================================================
    # RHINO UI — validate input
    # =========================================================================
    if v["thickness"] == 0:
        Rhino.RhinoApp.WriteLine("thickness must not be zero.")
        return
    pls: list[Rhino.Geometry.Polyline] = v["polylines"]
    if len(pls) == 1:
        Rhino.RhinoApp.WriteLine("Select 2 polylines: cross_section first, profile second.")
        return

    # =========================================================================
    # WOOD-NANO — compute shell elements
    # =========================================================================
    shell, elements = reflex_fold_elements(
        cross_section=pls[0] if len(pls) >= 2 else None,
        profile=pls[1]       if len(pls) >= 2 else None,
        thickness=v["thickness"], chamfer=v["chamfer"], chamfer_angle=v["chamfer_angle"],
    )

    # =========================================================================
    # RHINO UI — draw results
    # =========================================================================
    session.add(shell)
    session.draw()

    topo.clear()
    for i, el in enumerate(elements):
        topo.add_plate(i, el.bottom, el.top, el.loft_mesh_unwelded() if EXPLODE else el.loft_mesh())
    Rhino.RhinoDoc.ActiveDoc.Views.Redraw()


process_input(
    {
        "polylines":     ([], list[Rhino.Geometry.Polyline], "Select 2 polylines: cross_section first, profile second."),
        "thickness":     (10.0, float),
        "chamfer":       (20.0, float),
        "chamfer_angle": (180.0, float),
    },
    callback=_run,
)
