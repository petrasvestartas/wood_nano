from compas.colors import Color
from compas.geometry import Frame, Polyline
from compas_viewer import Viewer

from wood_nano_compas import connectors_elements

f_pl: list[list[Polyline]]
f_fr: list[list[Frame | None]]
f_idx: list[list[str]]
e_pl: list[list[Polyline]]
e_fr: list[list[Frame | None]]
e_idx: list[list[str]]

f_pl, f_fr, f_idx, e_pl, e_fr, e_idx = connectors_elements(
    face_thickness=20.0,
    face_positions=(0.0,),
    edge_divisions=(2,),
    rect_width=200.0,
    rect_height=200.0,
    rect_thickness=20.0,
)
n_face = sum(len(row) for row in f_pl)
n_edge = sum(len(row) for row in e_pl)

viewer = Viewer()
for i, row in enumerate(f_pl):
    for j, pl in enumerate(row):
        viewer.scene.add(pl, name=f"face_{i}_{j}", linecolor=Color(0.3, 0.6, 0.9))
for i, row in enumerate(e_pl):
    for j, pl in enumerate(row):
        viewer.scene.add(pl, name=f"edge_{i}_{j}", linecolor=Color(0.9, 0.5, 0.1))
viewer.show()
