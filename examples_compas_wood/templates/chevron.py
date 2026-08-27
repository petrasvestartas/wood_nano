from compas.colors import Color
from compas.datastructures import Mesh
from compas_viewer import Viewer

from wood_nano_compas import chevron_elements
from wood_nano_compas.wood_element import WoodElementCompas

shell: Mesh
elements: list[WoodElementCompas]
loft_meshes: list[Mesh]
joint_data: dict

shell, elements, loft_meshes, joint_data = chevron_elements(
    u_div=4,
    v_division_dist=900.0,
    box_height=760.0,
    plate_thickness=40.0,
)

_grey = Color(0.8, 0.8, 0.8)
viewer = Viewer()
for i, el in enumerate(elements):
    grp = viewer.scene.add_group(name=f"plate_{i}")
    grp.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    grp.add(el.top, name="top")
    grp.add(el.bottom, name="bot")
viewer.show()
