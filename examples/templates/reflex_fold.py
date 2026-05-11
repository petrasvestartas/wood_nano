from session_py.point import Point
from session_py.polyline import Polyline

from wood_nano import reflex_fold_elements

# Default fold (built-in cross-section and profile, origin-aligned)
mesh, elements = reflex_fold_elements(thickness=10.0, chamfer_bot=20.0, chamfer_top=20.0, chamfer_angle=45.0)
print("default  vertices:", mesh.number_of_vertices(), " faces:", mesh.number_of_faces())
print("default  elements:", len(elements))

# Custom: session_py.Polyline inputs
cross_section = Polyline([
    Point(   0, 0,   0),
    Point( 500, 0, 200),
    Point(1000, 0, 300),
    Point(1500, 0, 200),
    Point(2000, 0,   0),
])
profile = Polyline([
    Point(0,    0, 0),
    Point(0,  -90, 0),
    Point(0, -180, 0),
    Point(0, -270, 0),
    Point(0, -360, 0),
])
mesh2, elements2 = reflex_fold_elements(
    cross_section, profile,
    thickness=10.0, chamfer_bot=20.0, chamfer_top=20.0, chamfer_angle=45.0)
print("custom   vertices:", mesh2.number_of_vertices(), " faces:", mesh2.number_of_faces())
print("custom   elements:", len(elements2))
