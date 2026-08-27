from __future__ import annotations

from wood_nano import joinery_solver_elements, reciprocal_rotation_elements
from wood_nano.joinery_solver import SEARCH_CROSS_JOINT, JoineryElement, JointResult

# beam_offsets=[0.0, 150.0]: direction-group 1 lifted 150 mm for visible layer separation
_, rr_beams, rr_side0, rr_side1 = reciprocal_rotation_elements(
    nx=6, ny=6,
    W=6000.0, D=5000.0, h=1500.0,
    mesh_type="quad",
    angle=0.35, scale=1.4,
    beam_w=100.0, beam_h=200.0,
    beam_offsets=[0.0, 150.0],
)
elems: list[JoineryElement]
joints: list[JointResult]
elems, joints = joinery_solver_elements(
    rr_side0, rr_side1,
    search_type=SEARCH_CROSS_JOINT,
)
print(f"reciprocal_rotation: {len(rr_beams)} beams, {len(joints)} joints")
