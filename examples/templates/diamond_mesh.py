"""diamond_mesh — standalone Python example (no Rhino required).

Demonstrates the default parametric diamond-grid shell.
"""
from wood_nano import diamond_mesh_elements

# Default diamond mesh shell (5×2 grid, 15 mm chamfer)
shell, elements = diamond_mesh_elements(
    u_div=5, v_div=2,
    thickness=-15.0, chamfer=30.0, chamfer_angle=180.0,
)
print("shell    vertices:", shell.number_of_vertices(),
      " faces:", shell.number_of_faces())
print("elements:", len(elements))

# Each element has bottom/top polylines and a loft mesh
el = elements[0]
print("element[0] bottom pts:", el.bottom.point_count())
print("element[0] top    pts:", el.top.point_count())
