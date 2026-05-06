#! python3
import Rhino
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import reciprocal_beam_elements

session = Session()


def _run(v, _):
    if v["beam_w"] <= 0:
        Rhino.RhinoApp.WriteLine("beam_w must be positive.")
        return
    dome, beams, side0, side1 = reciprocal_beam_elements(
        nx=v["nx"], ny=v["ny"],
        W=v["W"], D=v["D"], h=v["h"],
        angle=v["angle"], scale=v["scale"],
        beam_w=v["beam_w"],
    )
    session.add(dome)
    for m in beams:
        session.add(m)
    for pl in side0:
        session.add(pl)
    for pl in side1:
        session.add(pl)
    session.draw()
    Rhino.RhinoApp.WriteLine(
        f"dome: {dome.number_of_faces()} faces  beams: {len(beams)}")


process_input(
    {
        "nx":    (12,   int),
        "ny":    (10,   int),
        "W":     (12.0, float),
        "D":     (10.0, float),
        "h":     (3.0,  float),
        "angle": (0.35, float),
        "scale": (1.4,  float),
        "beam_w":(0.10, float),
    },
    callback=_run,
)
