from compas.colors import Color
from compas.datastructures import Mesh
from compas_viewer import Viewer

from wood_nano_compas import translation_shell_elements
from wood_nano_compas.wood_element import WoodElementCompas

shell: Mesh
elements: list[WoodElementCompas]
shell, elements = translation_shell_elements()

viewer = Viewer()
for i, el in enumerate(elements):
    grp = viewer.scene.add_group(name=f"plate_{i}")
    grp.add(el.loft_mesh(), show_lines=False, facecolor=Color(0.8, 0.8, 0.8))
    grp.add(el.top, name="top")
    grp.add(el.bottom, name="bot")
viewer.show()
