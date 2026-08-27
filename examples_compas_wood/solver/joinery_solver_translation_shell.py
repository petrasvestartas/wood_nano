from __future__ import annotations

from compas.colors import Color
from compas_viewer import Viewer

from wood_nano_compas import (
    SEARCH_FACE_TO_FACE,
    joinery_solver_elements,
    translation_shell_elements,
)
from wood_nano_compas.wood_element import JoineryElementCompas, JointResultCompas

# family 0: division=50, type=1 (ss_e_ip)
_params: list[float] = [
    50,  0.5,  1,   # 0  ss_e_ip  — SIDE-TO-SIDE IN-PLANE
    450, 0.64, 15,  # 1  ss_e_op
    450, 0.5,  20,  # 2  ts_e_p
    300, 0.5,  30,  # 3  cr_c_ip
      6, 0.95, 40,  # 4  tt_e_p
    300, 0.5,  58,  # 5  ss_e_r
    300, 1.0,  60,  # 6  b
]

_, ts_elements = translation_shell_elements()
elems: list[JoineryElementCompas]
joints: list[JointResultCompas]
elems, joints = joinery_solver_elements(
    [el.bottom for el in ts_elements],
    [el.top    for el in ts_elements],
    search_type=SEARCH_FACE_TO_FACE,
    joint_params=_params,
)

_grey = Color(0.8, 0.8, 0.8)
viewer = Viewer()
for i, el in enumerate(elems):
    grp = viewer.scene.add_group(name=f"ts_{i}")
    grp.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    for k, pl in enumerate(el.top_outlines):
        grp.add(pl, name=f"top_{k}")
    for k, pl in enumerate(el.bottom_outlines):
        grp.add(pl, name=f"bot_{k}")
for j, jt in enumerate(joints):
    grp = viewer.scene.add_group(name=f"ts_joint_{j}")
    grp.add(jt.area, name="area")
    for v, vol in enumerate(jt.volumes):
        grp.add(vol, name=f"vol_{v}", linecolor=Color(0.9, 0.2, 0.2))
    for l, ln in enumerate(jt.lines):
        grp.add(ln, name=f"line_{l}", linecolor=Color(0.0, 0.7, 0.3))
viewer.show()
