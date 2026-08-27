from __future__ import annotations

from compas.colors import Color
from compas_viewer import Viewer

from wood_nano_compas import (
    SEARCH_CROSS_JOINT,
    joinery_solver_elements,
    reciprocal_rotation_elements,
)
from wood_nano_compas.wood_element import JoineryElementCompas, JointResultCompas

# beam_offsets=[0.0, 150.0]: direction-group 1 lifted 150 mm for visible layer separation
_, rr_beams, rr_side0, rr_side1 = reciprocal_rotation_elements(
    nx=6, ny=6,
    W=6000.0, D=5000.0, h=1500.0,
    mesh_type="quad",
    angle=0.35, scale=1.4,
    beam_w=100.0, beam_h=200.0,
    beam_offsets=[0.0, 100.0],
)
elems: list[JoineryElementCompas]
joints: list[JointResultCompas]
elems, joints = joinery_solver_elements(
    rr_side0, rr_side1,
    search_type=SEARCH_CROSS_JOINT,
)

# For beams, el.loft_mesh() only lofts the two input side polylines — a flat panel.
# Use rr_beams (pre-built volumetric beam meshes) for display instead.
# top_outlines/bottom_outlines are the cut side-face outlines with joint notches.
_grey = Color(0.8, 0.8, 0.8)
viewer = Viewer()
for i, (bm, el) in enumerate(zip(rr_beams, elems)):
    grp = viewer.scene.add_group(name=f"rr_{i}")
    grp.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    for k, pl in enumerate(el.top_outlines):
        grp.add(pl, name=f"top_{k}")
    for k, pl in enumerate(el.bottom_outlines):
        grp.add(pl, name=f"bot_{k}")
for j, jt in enumerate(joints):
    grp = viewer.scene.add_group(name=f"rr_joint_{j}")
    grp.add(jt.area, name="area")
    for v, vol in enumerate(jt.volumes):
        grp.add(vol, name=f"vol_{v}", linecolor=Color(0.9, 0.2, 0.2))
    for l, ln in enumerate(jt.lines):
        grp.add(ln, name=f"line_{l}", linecolor=Color(0.0, 0.7, 0.3))
viewer.show()
