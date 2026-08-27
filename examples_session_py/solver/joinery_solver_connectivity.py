from __future__ import annotations

from wood_nano import (
    joinery_solver_elements,
    translation_shell_elements,
)
from wood_nano.joinery_solver import (
    SEARCH_FACE_TO_FACE,
    JoineryElement,
    JointResult,
)


def joint_family(joint_type: int) -> str:
    """Map a joint type code to its family name and face configuration."""
    if  1 <= joint_type <=  9: return "side-to-side in-plane     (side↔side)"
    if 10 <= joint_type <= 19: return "side-to-side out-of-plane  (side↔side)"
    if 20 <= joint_type <= 29: return "top-to-side                (top↔side)"
    if 30 <= joint_type <= 39: return "cross-joint in-plane       (cross)"
    if 40 <= joint_type <= 49: return "top-to-top                 (top↔top)"
    if 50 <= joint_type <= 59: return "side-to-side rotated       (side↔side)"
    if 60 <= joint_type <= 69: return "boundary                   (edge)"
    return "unknown"


# Run the joinery solver on a translation shell (type 1, division 50)
_params: list[float] = [
    50,  0.5, 1,   # 0  ss_e_ip  — type 1, division 50
    450, 0.64, 15, # 1  ss_e_op
    450, 0.5,  20, # 2  ts_e_p
    300, 0.5,  30, # 3  cr_c_ip
      6, 0.95, 40, # 4  tt_e_p
    300, 0.5,  58, # 5  ss_e_r
    300, 1.0,  60, # 6  b
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

# Print connectivity table
# jt.area is a session_py.Polyline; get_points() returns the point list
print(f"{'idx':>4}  {'el_a':>5}  {'el_b':>5}  {'type':>5}  {'area_pts':>8}  family")
print("-" * 72)
for idx, jt in enumerate(joints):
    el_a, el_b = jt.element_ids
    area_pts = len(jt.area.get_points())
    print(
        f"{idx:>4}  {el_a:>5}  {el_b:>5}  {jt.joint_type:>5}  "
        f"{area_pts:>8}  {joint_family(jt.joint_type)}"
    )

print(f"\n{len(elems)} elements, {len(joints)} joints total")
