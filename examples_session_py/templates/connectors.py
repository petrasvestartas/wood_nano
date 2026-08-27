from session_py.plane import Plane
from session_py.polyline import Polyline
from wood_nano import connectors_elements

# default hex mesh
f_pl: list[list[Polyline]]
f_planes: list[list[Plane | None]]
f_idx: list[list[str]]
e_pl: list[list[Polyline]]
e_planes: list[list[Plane | None]]
e_idx: list[list[str]]
f_pl, f_planes, f_idx, e_pl, e_planes, e_idx = connectors_elements()
print(len(f_pl), len(e_pl))

# custom 2×2 quad grid, two face layers
verts: list[list[float]] = [
    [  0,   0, 0], [100,   0, 0], [200,   0, 0],
    [  0, 100, 0], [100, 100, 0], [200, 100, 0],
    [  0, 200, 0], [100, 200, 0], [200, 200, 0],
]
faces: list[list[int]] = [[0,1,4,3],[1,2,5,4],[3,4,7,6],[4,5,8,7]]

f_pl2, f_planes2, f_idx2, e_pl2, e_planes2, e_idx2 = connectors_elements(
    mesh=(verts, faces),
    face_thickness=5.0,
    face_positions=[-10.0, 10.0],
    edge_divisions=[3],
    rect_width=12.0,
    rect_height=12.0,
    rect_thickness=5.0,
)
print(len(f_pl2), len(e_pl2))
