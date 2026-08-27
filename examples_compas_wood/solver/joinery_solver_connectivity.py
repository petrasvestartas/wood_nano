from __future__ import annotations

from compas.colors import Color
from compas_viewer import Viewer

from wood_nano_compas import (
    SEARCH_FACE_TO_FACE,
    joinery_solver_elements,
    translation_shell_elements,
)
from wood_nano_compas.wood_element import JoineryElementCompas, JointResultCompas


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
elems: list[JoineryElementCompas]
joints: list[JointResultCompas]
elems, joints = joinery_solver_elements(
    [el.bottom for el in ts_elements],
    [el.top    for el in ts_elements],
    search_type=SEARCH_FACE_TO_FACE,
    joint_params=_params,
)

# Print connectivity table
print(f"{'idx':>4}  {'el_a':>5}  {'el_b':>5}  {'type':>5}  {'area_pts':>8}  family")
print("-" * 72)
for idx, jt in enumerate(joints):
    el_a, el_b = jt.element_ids
    print(
        f"{idx:>4}  {el_a:>5}  {el_b:>5}  {jt.joint_type:>5}  "
        f"{len(jt.area.points):>8}  {joint_family(jt.joint_type)}"
    )

print(f"\n{len(elems)} elements, {len(joints)} joints total")

_grey = Color(0.8, 0.8, 0.8)
viewer = Viewer()
for i, el in enumerate(elems):
    grp = viewer.scene.add_group(name=f"el_{i}")
    grp.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    for k, pl in enumerate(el.top_outlines):
        grp.add(pl, name=f"top_{k}")
    for k, pl in enumerate(el.bottom_outlines):
        grp.add(pl, name=f"bot_{k}")
for idx, jt in enumerate(joints):
    el_a, el_b = jt.element_ids
    grp = viewer.scene.add_group(name=f"joint_{el_a}_{el_b}_t{jt.joint_type}")
    grp.add(jt.area, name="area")
    for v, vol in enumerate(jt.volumes):
        grp.add(vol, name=f"vol_{v}", linecolor=Color(0.9, 0.2, 0.2))
    for l, ln in enumerate(jt.lines):
        grp.add(ln, name=f"line_{l}", linecolor=Color(0.0, 0.7, 0.3))
viewer.show()
