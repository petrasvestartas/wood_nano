from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from wood_nano import (
    joinery_solver_elements,
    reciprocal_rotation_elements,
)
from wood_nano.joinery_solver import (
    SEARCH_BOTH,
    SEARCH_CROSS_JOINT,
    SEARCH_FACE_TO_FACE,
    JoineryElement,
    JointResult,
)

_DATASET_DIR: Path = (
    Path(__file__).parent.parent.parent
    / "plugin_rhino" / "plugin" / "shared" / "datasets"
)


def load_xml_polylines(path: Path) -> tuple[list, list]:
    """Parse an input_polylines XML into bottom/top polyline pairs.

    Polylines are stored in pairs: [bottom_0, top_0, bottom_1, top_1, ...].
    Returns (bottom_polylines, top_polylines).
    """
    root = ET.parse(path).getroot()
    all_polylines: list[list[list[float]]] = []
    for pl_el in root.findall("Polyline"):
        pts = [
            [float(pt.findtext("x")), float(pt.findtext("y")), float(pt.findtext("z"))]
            for pt in pl_el.findall("point")
        ]
        all_polylines.append(pts)
    bottom = all_polylines[0::2]
    top    = all_polylines[1::2]
    return bottom, top


# =============================================================================
# 1. VDA TWO-LAYER JOINERY — cross_vda_single_arch
# =============================================================================
vda_arch_path = _DATASET_DIR / "type_plates_name_cross_vda_single_arch.xml"
vda_bottom, vda_top = load_xml_polylines(vda_arch_path)
print(f"vda_single_arch: {len(vda_bottom)} plates")

vda_elems: list[JoineryElement]
vda_joints: list[JointResult]
vda_elems, vda_joints = joinery_solver_elements(
    vda_bottom, vda_top,
    search_type=SEARCH_BOTH,
)
print(f"  → {len(vda_joints)} joints detected")

# =============================================================================
# 2. VDA FLOOR — two-layer floor structure
# =============================================================================
vda_floor_path = _DATASET_DIR / "type_plates_name_vda_floor_1.xml"
floor_bottom, floor_top = load_xml_polylines(vda_floor_path)
print(f"vda_floor_1: {len(floor_bottom)} plates")

floor_elems: list[JoineryElement]
floor_joints: list[JointResult]
floor_elems, floor_joints = joinery_solver_elements(
    floor_bottom, floor_top,
    search_type=SEARCH_FACE_TO_FACE,
)
print(f"  → {len(floor_joints)} joints detected")

# =============================================================================
# 3. BEAM CROSS HALF-LAP (conical variant) — reciprocal rotation frame
# =============================================================================
_beam_params: list[float] = [
    300, 0.5,  3,   # 0  ss_e_ip
    450, 0.64, 15,  # 1  ss_e_op
    450, 0.5,  20,  # 2  ts_e_p
    300, 0.5,  30,  # 3  cr_c_ip — cross half-lap, type 30
      6, 0.95, 40,  # 4  tt_e_p
    300, 0.5,  58,  # 5  ss_e_r
    300, 1.0,  60,  # 6  b
]

_, beam_meshes, beam_s0, beam_s1 = reciprocal_rotation_elements(
    nx=6, ny=6,
    W=6000.0, D=5000.0, h=1500.0,
    mesh_type="quad",
    angle=0.35, scale=1.4,
    beam_w=100.0, beam_h=200.0,
)
beam_elems: list[JoineryElement]
beam_joints: list[JointResult]
beam_elems, beam_joints = joinery_solver_elements(
    beam_s0, beam_s1,
    search_type=SEARCH_CROSS_JOINT,
    joint_params=_beam_params,
)
print(f"beam cross half-lap: {len(beam_meshes)} beams, {len(beam_joints)} joints")
