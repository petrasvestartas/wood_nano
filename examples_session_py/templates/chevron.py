from session_py.mesh import Mesh
from wood_nano import chevron_elements
from wood_nano.wood_element import WoodElement

shell: Mesh
elements: list[WoodElement]
loft_meshes: list[Mesh]
joint_data: dict[str, list]
shell, elements, loft_meshes, joint_data = chevron_elements(
    u_div=4,
    v_division_dist=900.0,
    box_height=760.0,
    plate_thickness=40.0,
    edge_rotation=1.0,
    edge_offset=0.5,
)
print(shell.number_of_vertices(), shell.number_of_faces(), len(elements))
print(len(joint_data["three_valence"]), len(joint_data["adjacency"]))
