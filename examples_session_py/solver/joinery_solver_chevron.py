from __future__ import annotations

from wood_nano import chevron_elements, joinery_solver_elements
from wood_nano.joinery_solver import SEARCH_FACE_TO_FACE, JoineryElement, JointResult

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
elems: list[JoineryElement]
joints: list[JointResult]
elems, joints = joinery_solver_elements(
    [el.bottom for el in ch_elements],
    [el.top    for el in ch_elements],
    search_type=SEARCH_FACE_TO_FACE,
    per_element_insertion_vectors=ch_joint_data["insertion_vectors"],
    per_element_joint_types=ch_joint_data["joints_per_face"],
    three_valence=ch_joint_data["three_valence"],
    adjacency=ch_joint_data["adjacency"],
)
print(f"chevron: {len(ch_elements)} elements, {len(joints)} joints")
