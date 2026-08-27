from __future__ import annotations

from compas.colors import Color
from compas_viewer import Viewer

from wood_nano_compas import (
    SEARCH_FACE_TO_FACE,
    chevron_elements,
    joinery_solver_elements,
)
from wood_nano_compas.wood_element import JoineryElementCompas, JointResultCompas

# chevron_elements() returns joint_data with:
#   insertion_vectors : per-element insertion direction (18 floats each)
#   joints_per_face   : per-element joint type per face (6 ints each)
#   three_valence     : 3-valence node groups for the chevron topology
#   adjacency         : adjacent plate pairs
_, ch_elements, _, ch_joint_data = chevron_elements(
    u_div=4,
    v_division_dist=900.0,
    box_height=760.0,
    plate_thickness=40.0,
)
elems: list[JoineryElementCompas]
joints: list[JointResultCompas]
elems, joints = joinery_solver_elements(
    [el.bottom for el in ch_elements],
    [el.top    for el in ch_elements],
    search_type=SEARCH_FACE_TO_FACE,
    per_element_insertion_vectors=ch_joint_data["insertion_vectors"],
    per_element_joint_types=ch_joint_data["joints_per_face"],
    three_valence=ch_joint_data["three_valence"],
    adjacency=ch_joint_data["adjacency"],
)

_grey = Color(0.8, 0.8, 0.8)
viewer = Viewer()
for i, el in enumerate(elems):
    grp = viewer.scene.add_group(name=f"ch_{i}")
    grp.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    for k, pl in enumerate(el.top_outlines):
        grp.add(pl, name=f"top_{k}")
    for k, pl in enumerate(el.bottom_outlines):
        grp.add(pl, name=f"bot_{k}")
for j, jt in enumerate(joints):
    grp = viewer.scene.add_group(name=f"ch_joint_{j}")
    grp.add(jt.area, name="area")
    for v, vol in enumerate(jt.volumes):
        grp.add(vol, name=f"vol_{v}", linecolor=Color(0.9, 0.2, 0.2))
    for l, ln in enumerate(jt.lines):
        grp.add(ln, name=f"line_{l}", linecolor=Color(0.0, 0.7, 0.3))
viewer.show()
