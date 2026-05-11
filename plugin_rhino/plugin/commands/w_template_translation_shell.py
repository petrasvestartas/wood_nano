#! python3
# venv: wood_env
# r: wood-nano
import Rhino
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import translation_shell_elements
from wood_nano.wood_element import unweld_mesh
from wood_nano.plate_topology import PlateTopology

session = Session()
topo    = PlateTopology()


def _run(v, _):
    if v["thickness"] == 0:
        Rhino.RhinoApp.WriteLine("thickness must not be zero.")
        return
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
    session.draw()

    topo.clear()
    for i, el in enumerate(elements):
        topo.add_plate(i, el.bottom, el.top, unweld_mesh(el.loft_mesh()))


process_input(
    {
        "polylines":     ([], list[Rhino.Geometry.Polyline], "Select 2 polylines: cross_section first, profile second."),
        "thickness":     (15.0, float),
        "chamfer":       (2.0,  float),
        "chamfer_angle": (180.0, float),
    },
    callback=_run,
)
