#! python3
import Rhino
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import chevron_elements

session = Session()


def _run(v, _):
    if v["plate_thickness"] == 0:
        Rhino.RhinoApp.WriteLine("plate_thickness must not be zero.")
        return
    shell, elements = chevron_elements(
        u_divisions=v["u_divisions"],
        v_division_dist=v["v_division_dist"],
        box_height=v["box_height"],
        plate_thickness=v["plate_thickness"],
        edge_rotation=v["edge_rotation"],
        edge_offset=v["edge_offset"],
    )
    session.add(shell)
    for el in elements:
        session.add(el.bottom, el.top, el.loft_mesh())
    session.draw()
    Rhino.RhinoApp.WriteLine(
        f"shell: {shell.number_of_faces()} faces  plates: {len(elements)}")


process_input(
    {
        "u_divisions":    (4,     int),
        "v_division_dist":(900.0, float),
        "box_height":     (760.0, float),
        "plate_thickness":(40.0,  float),
        "edge_rotation":  (1.0,   float),
        "edge_offset":    (0.5,   float),
    },
    callback=_run,
)
