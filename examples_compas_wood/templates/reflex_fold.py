from compas.colors import Color
from compas.datastructures import Mesh
from compas_viewer import Viewer

from wood_nano_compas import reflex_fold_elements
from wood_nano_compas.wood_element import WoodElementCompas

# default fold geometry
shell: Mesh
elements: list[WoodElementCompas]
shell, elements = reflex_fold_elements(thickness=10.0, chamfer=20.0, chamfer_angle=90.0)

_grey = Color(0.8, 0.8, 0.8)
viewer = Viewer()
for i, el in enumerate(elements):
    grp = viewer.scene.add_group(name=f"plate_{i}")
    grp.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    grp.add(el.top, name="top")
    grp.add(el.bottom, name="bot")
viewer.show()
