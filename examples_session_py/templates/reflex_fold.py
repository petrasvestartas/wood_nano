from session_py.mesh import Mesh
from session_py.point import Point
from session_py.polyline import Polyline
from wood_nano import reflex_fold_elements
from wood_nano.wood_element import WoodElement

# default
mesh: Mesh
elements: list[WoodElement]
mesh, elements = reflex_fold_elements(thickness=10.0, chamfer=20.0, chamfer_angle=45.0)
print(mesh.number_of_vertices(), mesh.number_of_faces(), len(elements))

# custom polyline inputs
cross_section: Polyline = Polyline([
    Point(   0, 0,   0), Point( 500, 0, 200),
    Point(1000, 0, 300), Point(1500, 0, 200), Point(2000, 0, 0),
])
profile: Polyline = Polyline([
    Point(0,    0, 0), Point(0,  -90, 0),
    Point(0, -180, 0), Point(0, -270, 0), Point(0, -360, 0),
])
mesh2: Mesh
elements2: list[WoodElement]
mesh2, elements2 = reflex_fold_elements(
    cross_section, profile, thickness=10.0, chamfer=20.0, chamfer_angle=45.0)
print(mesh2.number_of_vertices(), mesh2.number_of_faces(), len(elements2))
