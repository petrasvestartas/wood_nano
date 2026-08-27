from session_py.mesh import Mesh
from wood_nano import diamond_mesh_elements
from wood_nano.wood_element import WoodElement

shell: Mesh
elements: list[WoodElement]
shell, elements = diamond_mesh_elements(
    u_div=5, v_div=2,
    thickness=-15.0, chamfer=30.0, chamfer_angle=180.0,
)
print(shell.number_of_vertices(), shell.number_of_faces(), len(elements))
