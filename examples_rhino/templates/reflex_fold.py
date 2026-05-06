#! python3
import Rhino
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import reflex_fold_elements

session = Session()


def _run(v, _):
    if v["thickness"] == 0:
        Rhino.RhinoApp.WriteLine("thickness must not be zero.")
        return
    pls = v["polylines"]
    if len(pls) == 1:
        Rhino.RhinoApp.WriteLine("Select 2 polylines: cross_section first, profile second.")
        return
    shell, elements = reflex_fold_elements(
        cross_section=pls[0] if len(pls) >= 2 else None,
        profile=pls[1]       if len(pls) >= 2 else None,
        thickness=v["thickness"], chamfer=v["chamfer"], chamfer_angle=v["chamfer_angle"],
    )
    session.add(shell)
    for el in elements:
        session.add(el.bottom, el.top, el.loft_mesh())
    session.draw()


process_input(
    {
        "polylines":     ([], list[Rhino.Geometry.Polyline], "Select 2 polylines: cross_section first, profile second."),
        "thickness":     (10.0, float),
        "chamfer":       (20.0, float),
        "chamfer_angle": (180.0, float),
    },
    callback=_run,
)
