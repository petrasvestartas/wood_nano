from __future__ import annotations

from wood_nano import diamond_mesh_elements, joinery_solver_elements
from wood_nano.joinery_solver import SEARCH_FACE_TO_FACE, JoineryElement, JointResult

# joint_volume_ext length=-200 extends cut volume
_params: list[float] = [
    300, 0.5,  1,   # 0  ss_e_ip
    450, 0.64, 15,  # 1  ss_e_op  — family 1: type=15
    450, 0.5,  20,  # 2  ts_e_p
    300, 0.5,  30,  # 3  cr_c_ip
      6, 0.95, 40,  # 4  tt_e_p
    300, 0.5,  58,  # 5  ss_e_r
    300, 1.0,  60,  # 6  b
]

_, dm_elements = diamond_mesh_elements(u_div=8, v_div=4, thickness=10.0)
elems: list[JoineryElement]
joints: list[JointResult]
elems, joints = joinery_solver_elements(
    [el.bottom for el in dm_elements],
    [el.top    for el in dm_elements],
    search_type=SEARCH_FACE_TO_FACE,
    joint_params=_params,
    joint_volume_ext=[0.0, 0.0, -200.0],
)
print(f"diamond_mesh: {len(dm_elements)} elements, {len(joints)} joints")
