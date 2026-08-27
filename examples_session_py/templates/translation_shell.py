from session_py.mesh import Mesh
from session_py.point import Point
from session_py.polyline import Polyline
from wood_nano import translation_shell_elements
from wood_nano.wood_element import WoodElement

# default arch
mesh: Mesh
elements: list[WoodElement]
mesh, elements = translation_shell_elements(thickness=15.0, chamfer=2.0, chamfer_angle=90.0)
print(mesh.number_of_vertices(), mesh.number_of_faces(), len(elements))

# custom polyline inputs
cross_section: Polyline = Polyline([
    Point(0,    0,   0), Point(500,  0,  0),
    Point(1000, 0,   0), Point(1500, 0,  0), Point(2000, 0, 0),
])
profile: Polyline = Polyline([
    Point(0, 0,    0), Point(0, 500,  50),
    Point(0, 1000, 150), Point(0, 1500, 300), Point(0, 2000, 500),
])
mesh2: Mesh
elements2: list[WoodElement]
mesh2, elements2 = translation_shell_elements(
    cross_section, profile, thickness=15.0, chamfer=2.0, chamfer_angle=90.0)
print(mesh2.number_of_vertices(), mesh2.number_of_faces(), len(elements2))
