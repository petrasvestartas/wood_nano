from compas.colors import Color
from compas_viewer import Viewer

from wood_nano_compas import diamond_mesh_elements
from wood_nano_compas.wood_element import WoodElementCompas

shell: Mesh
elements: list[WoodElementCompas]
shell, elements = diamond_mesh_elements(
    u_div=8, v_div=4,
    thickness=10.0, chamfer=1.0, chamfer_angle=180.0,
)

_grey = Color(0.8, 0.8, 0.8)
viewer = Viewer()
for i, el in enumerate(elements):
    grp = viewer.scene.add_group(name=f"plate_{i}")
    grp.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    grp.add(el.top, name="top")
    grp.add(el.bottom, name="bot")
viewer.show()
