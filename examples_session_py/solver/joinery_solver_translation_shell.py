from __future__ import annotations

from wood_nano import joinery_solver_elements, translation_shell_elements
from wood_nano.joinery_solver import SEARCH_FACE_TO_FACE, JoineryElement, JointResult

_params: list[float] = [
    50,  0.5,  1,   # 0  ss_e_ip  — family 0: division=50, type=1
    450, 0.64, 15,  # 1  ss_e_op
    450, 0.5,  20,  # 2  ts_e_p
    300, 0.5,  30,  # 3  cr_c_ip
      6, 0.95, 40,  # 4  tt_e_p
    300, 0.5,  58,  # 5  ss_e_r
    300, 1.0,  60,  # 6  b
]

_, ts_elements = translation_shell_elements()
elems: list[JoineryElement]
joints: list[JointResult]
elems, joints = joinery_solver_elements(
    [el.bottom for el in ts_elements],
    [el.top    for el in ts_elements],
    search_type=SEARCH_FACE_TO_FACE,
    joint_params=_params,
)
print(f"translation_shell: {len(ts_elements)} elements, {len(joints)} joints")
