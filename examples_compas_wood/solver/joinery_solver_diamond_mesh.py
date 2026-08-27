from __future__ import annotations

from compas.colors import Color
from compas_viewer import Viewer

from wood_nano_compas import (
    SEARCH_FACE_TO_FACE,
    diamond_mesh_elements,
    joinery_solver_elements,
)
from wood_nano_compas.wood_element import JoineryElementCompas, JointResultCompas

# family 1: type=15 (ss_e_op); joint_volume_ext length=-200 extends cut volume
_params: list[float] = [
    300, 0.5,  1,   # 0  ss_e_ip
    450, 0.64, 15,  # 1  ss_e_op  — SIDE-TO-SIDE OUT-OF-PLANE
    450, 0.5,  20,  # 2  ts_e_p
    300, 0.5,  30,  # 3  cr_c_ip
      6, 0.95, 40,  # 4  tt_e_p
    300, 0.5,  58,  # 5  ss_e_r
    300, 1.0,  60,  # 6  b
]

_, dm_elements = diamond_mesh_elements(u_div=6, v_div=2, thickness=10.0)
elems: list[JoineryElementCompas]
joints: list[JointResultCompas]
elems, joints = joinery_solver_elements(
    [el.bottom for el in dm_elements],
    [el.top    for el in dm_elements],
    search_type=SEARCH_FACE_TO_FACE,
    joint_params=_params,
    joint_volume_ext=[0.0, 0.0, -200.0],
)

viewer = Viewer()
for i, el in enumerate(elems):
    grp = viewer.scene.add_group(name=f"dm_{i}")
    grp.add(el.loft_mesh(), show_lines=False)
    for k, pl in enumerate(el.top_outlines):
        grp.add(pl, name=f"top_{k}")
    for k, pl in enumerate(el.bottom_outlines):
        grp.add(pl, name=f"bot_{k}")
for j, jt in enumerate(joints):
    viewer.scene.add(jt.area, name=f"dm_area_{j}")
    for v, vol in enumerate(jt.volumes):
        viewer.scene.add(vol, name=f"dm_vol_{j}_{v}", linecolor=Color(0.9, 0.2, 0.2))
    for l, ln in enumerate(jt.lines):
        viewer.scene.add(ln, name=f"dm_line_{j}_{l}", linecolor=Color(0.0, 0.7, 0.3))
viewer.show()
