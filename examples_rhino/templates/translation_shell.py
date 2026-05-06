#! python3
import Rhino
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import translation_shell_elements

session = Session()


def _run(v, _):
    pls = v["polylines"]
    if len(pls) == 1:
        Rhino.RhinoApp.WriteLine("Select 2 polylines: cross_section first, profile second.")
        return
    shell, elements = translation_shell_elements(
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
        "thickness":     (15.0, float),
        "chamfer":       (2.0,  float),
        "chamfer_angle": (90.0, float),
    },
    callback=_run,
)
