from session_py.mesh import Mesh
from session_py.polyline import Polyline
from wood_nano import reciprocal_rotation_elements

dome: Mesh
beams: list[Mesh]
side0: list[Polyline]
side1: list[Polyline]
dome, beams, side0, side1 = reciprocal_rotation_elements(
    nx=6, ny=6,
    W=6000.0, D=5000.0, h=1500.0,
    angle=0.2,
    scale=1.4,
    beam_w=50.0, beam_h=200.0,
    cut_offset_factor=2.0,
)
print(dome.number_of_faces(), len(beams))
