from compas.colors import Color
from compas.datastructures import Mesh
from compas.geometry import Point, Polyline
from compas_viewer import Viewer

from wood_nano_compas import translation_shell_elements
from wood_nano_compas.wood_element import WoodElementCompas

# default arch
shell: Mesh
elements: list[WoodElementCompas]
shell, elements = translation_shell_elements(thickness=15.0, chamfer=2.0, chamfer_angle=90.0)

# custom polyline inputs
cross_section: Polyline = Polyline([
    Point(0,    0,   0), Point(500,  0,  0),
    Point(1000, 0,   0), Point(1500, 0,  0), Point(2000, 0, 0),
])
profile: Polyline = Polyline([
    Point(0, 0,    0), Point(0, 500,  50),
    Point(0, 1000, 150), Point(0, 1500, 300), Point(0, 2000, 500),
])
shell2: Mesh
elements2: list[WoodElementCompas]
shell2, elements2 = translation_shell_elements(
    cross_section, profile, thickness=15.0, chamfer=2.0, chamfer_angle=90.0)

_grey = Color(0.8, 0.8, 0.8)
viewer = Viewer()
grp1 = viewer.scene.add_group(name="quarter_0")
for i, el in enumerate(elements):
    pg = grp1.add_group(name=f"plate_{i}")
    pg.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    pg.add(el.top, name="top")
    pg.add(el.bottom, name="bot")
grp2 = viewer.scene.add_group(name="quarter_1")
for i, el in enumerate(elements2):
    pg = grp2.add_group(name=f"plate_{i}")
    pg.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    pg.add(el.top, name="top")
    pg.add(el.bottom, name="bot")
viewer.show()
