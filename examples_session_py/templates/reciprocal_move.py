from session_py.mesh import Mesh
from session_py.polyline import Polyline
from wood_nano import reciprocal_move_elements, reciprocal_move_elements_from_mesh

# default sinusoidal dome
dome: Mesh
beams: list[Mesh]
side0: list[Polyline]
side1: list[Polyline]
dome, beams, side0, side1 = reciprocal_move_elements(
    nx=6, ny=6,
    W=6000.0, D=5000.0, h=1500.0,
    mesh_type="quad",
    angle=200.0,
    beam_w=200.0, beam_h=400.0,
)
print(dome.number_of_faces(), len(beams))

# from user mesh
verts: list[list[float]] = [
    [  0,   0, 0], [100,   0, 0], [200,   0, 0],
    [  0, 100, 0], [100, 100, 0], [200, 100, 0],
    [  0, 200, 0], [100, 200, 0], [200, 200, 0],
]
faces: list[list[int]] = [[0,1,4,3],[1,2,5,4],[3,4,7,6],[4,5,8,7]]
dome2: Mesh
beams2: list[Mesh]
dome2, beams2, side0_2, side1_2 = reciprocal_move_elements_from_mesh(
    verts, faces, angle=10.0, beam_w=10.0, beam_h=20.0,
)
print(dome2.number_of_faces(), len(beams2))
