from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

XML_DIR = Path(__file__).parent.parent / "examples_rhino" / "plugin" / "shared" / "datasets"
JSON_DIR = Path(__file__).parent / "datasets"
JSON_DIR.mkdir(exist_ok=True)


def _p(*family_overrides: tuple) -> list[float]:
    """Build 21-element joint_params list from (family, div, shift, type) tuples."""
    params = [0.0] * 21
    for fam, div, shift, typ in family_overrides:
        params[fam * 3], params[fam * 3 + 1], params[fam * 3 + 2] = div, shift, typ
    return params


# Parameters sourced from wood_test.cpp for each dataset.
# search_type: 0=FACE_TO_FACE, 1=CROSS_JOINT, 2=BOTH
# joint_params: null → C++ defaults; list of 21 floats → explicit override
# joint_volume_ext: null → none; list of 3 or 12 floats
# per_element_joint_types: null or nested int list (needed for joint-linking cases)
# adjacency: null or flat int list
_PARAMS: dict[str, dict] = {
    # ── joint-linking / vidychapel ──────────────────────────────────────────
    "type_plates_name_joint_linking_vidychapel_corner": {
        "search_type": 0,
        "joint_params": _p((1, 150, 0, 0)),
        "joint_volume_ext": [0, 0, -10],
        "per_element_joint_types": None,
        "adjacency": None,
    },
    "type_plates_name_joint_linking_vidychapel_one_layer": {
        "search_type": 0,
        "joint_params": _p((1, 50, 0, 10)),
        "joint_volume_ext": [0, 0, -15],
        "per_element_joint_types": None,
        "adjacency": None,
    },
    "type_plates_name_joint_linking_vidychapel_one_axis_two_layers": {
        "search_type": 0,
        "joint_params": _p((1, 50, 0, 0)),
        "joint_volume_ext": [0, 0, -200, 0, 0, -200, 0, 0, -20, 0, 0, -20],
        "per_element_insertion_vectors": [
            [[0, 0, 0]] * 8,
            [[0, 0, 0]] * 8,
            [[0, 0, 0]] * 8,
            [[0, 0, 0]] * 8,
            [[0, 0, 0]] * 8,
            [[0, 0, 0]] * 8,
            [[0, 133.378166, 0]] + [[0, 0, 0]] * 7,
            [[0, 133.378166, 0]] + [[0, 0, 0]] * 7,
            [[0, 0, 0]] * 8,
            [[0, 133.378166, 0]] + [[0, 0, 0]] * 7,
            [[0, 133.378166, 0]] + [[0, 0, 0]] * 7,
            [[0, 0, 0]] * 8,
            [[0, 133.378166, 0]] + [[0, 0, 0]] * 7,
            [[0, 133.378166, 0]] + [[0, 0, 0]] * 7,
            [[0, 0, 0]] * 8,
            [[0, 133.378166, 0]] + [[0, 0, 0]] * 7,
            [[0, 133.378166, 0]] + [[0, 0, 0]] * 7,
            [[0, 0, 0]] * 8,
        ],
        "per_element_joint_types": None,
        "adjacency": None,
    },
    "type_plates_name_joint_linking_vidychapel_full": {
        "search_type": 0,
        "joint_params": _p((1, 50, 0, 0)),
        "joint_volume_ext": [0, 0, -10],
        "per_element_insertion_vectors": [
            [[0, 133.378166, 0]] + [[0, 0, 0]] * 7 if i % 3 == 2
            else [[0, 0, 0]] * 8
            for i in range(26)
        ],
        "per_element_joint_types": None,
        "adjacency": None,
    },
    # ── hexbox ───────────────────────────────────────────────────────────────
    "type_plates_name_hexbox_and_corner": {
        "search_type": 0,
        "joint_params": _p((1, 450, 0.64, 10), (2, 450, 0.5, 20)),
        "joint_volume_ext": None,
    },
    # ── side-to-side inplane ─────────────────────────────────────────────────
    "type_plates_name_side_to_side_edge_inplane_2_butterflies": {
        "search_type": 0,
        "joint_params": _p((0, 150, 0, 0)),
        "joint_volume_ext": [0, 0, -10],
    },
    "type_plates_name_side_to_side_edge_inplane_hexshell": {
        "search_type": 0,
        "joint_params": _p((0, 40, 0, 1)),
        "joint_volume_ext": [-20, 0, -10],
    },
    "type_plates_name_side_to_side_edge_inplane_differentdirections": {
        "search_type": 0,
        "joint_params": _p((0, 40, 0, 1)),
        "joint_volume_ext": [-10, 0, -75],
    },
    "type_plates_name_side_to_side_edge_inplane_hilti": {
        "search_type": 0,
        "joint_params": _p((5, 500, 1.0, 55)),
        "joint_volume_ext": None,
    },
    "type_plates_name_side_to_side_edge_inplane_hilti_9_quads": {
        "search_type": 0,
        "joint_params": _p((5, 500, 1.0, 55)),
        "joint_volume_ext": None,
    },
    "type_plates_name_side_to_side_edge_inplane_hilti_square_shell": {
        "search_type": 0,
        "joint_params": _p((5, 500, 1.0, 55)),
        "joint_volume_ext": None,
    },
    # ── side-to-side inplane + outofplane corners ────────────────────────────
    "type_plates_name_side_to_side_edge_inplane_outofplane_simple_corners": {
        "search_type": 0,
        "joint_params": _p((0, 0, 0, 2), (1, 0, 0, 12)),
        "joint_volume_ext": [0, 0, -20],
    },
    "type_plates_name_side_to_side_edge_inplane_outofplane_simple_corners_combined": {
        "search_type": 0,
        "joint_params": _p((0, 0, 0, 2), (1, 0, 0, 12)),
        "joint_volume_ext": [0, 0, -20],
    },
    "type_plates_name_side_to_side_edge_inplane_outofplane_simple_corners_different_lengths": {
        "search_type": 0,
        "joint_params": _p((0, 140, 0.5, 1), (1, 140, 0.5, 10)),
        "joint_volume_ext": [0, 0, -20],
    },
    # ── side-to-side outofplane ──────────────────────────────────────────────
    "type_plates_name_side_to_side_edge_outofplane_folding": {
        "search_type": 0,
        "joint_params": _p((4, 12, 0.95, 0)),
        "joint_volume_ext": [0, 0, -20],
    },
    "type_plates_name_side_to_side_edge_outofplane_box": {
        "search_type": 0,
        "joint_params": _p((1, 0, 0, 17)),
        "joint_volume_ext": [0, 0, -100],
    },
    "type_plates_name_side_to_side_edge_outofplane_tetra": {
        "search_type": 0,
        "joint_params": _p((1, 0, 0.5, 17)),
        "joint_volume_ext": [0, 0, -100],
    },
    "type_plates_name_side_to_side_edge_outofplane_dodecahedron": {
        "search_type": 0,
        "joint_params": _p((1, 1000, 0.5, 14)),
        "joint_volume_ext": [0, 0, -250],
    },
    "type_plates_name_side_to_side_edge_outofplane_icosahedron": {
        "search_type": 0,
        "joint_params": _p((1, 1000, 0.5, 14)),
        "joint_volume_ext": [0, 0, -250],
    },
    "type_plates_name_side_to_side_edge_outofplane_octahedron": {
        "search_type": 0,
        "joint_params": _p((1, 1000, 0.5, 14)),
        "joint_volume_ext": [0, 0, -250],
    },
    "type_plates_name_side_to_side_edge_outofplane_inplane_and_top_to_top_hexboxes": {
        "search_type": 0,
        "joint_params": _p((0, 140, 0.5, 1), (1, 140, 0.5, 10), (2, 0, 0, 21), (4, 100, 150, 43)),
        "joint_volume_ext": [0, 0, -50],
    },
    # ── misc plates ──────────────────────────────────────────────────────────
    "type_plates_name_hex_block_rossiniere": {
        "search_type": 0,
        "joint_params": _p((0, 140, 0.5, 1), (1, 140, 0.5, 10)),
        "joint_volume_ext": [0, 0, -20],
    },
    "type_plates_name_top_to_top_pairs": {
        "search_type": 0,
        "joint_params": _p((4, 10, 0.95, 0)),
        "joint_volume_ext": [0, 0, -10],
    },
    # ── top-to-side ──────────────────────────────────────────────────────────
    "type_plates_name_top_to_side_pairs": {
        "search_type": 0,
        "joint_params": _p((2, 300, 0.5, 25)),
        "joint_volume_ext": [0, 0, -10],
    },
    "type_plates_name_top_to_side_box": {
        "search_type": 0,
        "joint_params": _p((2, 300, 0.5, 25)),
        "joint_volume_ext": None,
    },
    "type_plates_name_top_to_side_corners": {
        "search_type": 0,
        "joint_params": _p((1, 0, 0.66, 10), (2, 300, 0.5, 20)),
        "joint_volume_ext": None,
    },
    "type_plates_name_top_to_side_and_side_to_side_outofplane_annen_corner": {
        "search_type": 0,
        "joint_params": _p((1, 0, 0, 10), (2, 300, 0, 20)),
        "joint_volume_ext": None,
    },
    "type_plates_name_top_to_side_and_side_to_side_outofplane_annen_box": {
        "search_type": 0,
        "joint_params": _p((1, 200, 0, 10), (2, 300, 0, 20)),
        "joint_volume_ext": None,
    },
    "type_plates_name_top_to_side_and_side_to_side_outofplane_annen_box_pair": {
        "search_type": 0,
        "joint_params": _p((1, 200, 0, 10), (2, 300, 0, 20)),
        "joint_volume_ext": None,
    },
    "type_plates_name_top_to_side_and_side_to_side_outofplane_annen_grid_small": {
        "search_type": 0,
        "joint_params": _p((1, 200, 0, 10), (2, 300, 0, 20)),
        "joint_volume_ext": None,
    },
    # ── vda floor ────────────────────────────────────────────────────────────
    "type_plates_name_vda_floor_0": {
        "search_type": 0,
        "joint_params": _p((1, 8000, 0.66, 10), (4, 100, 45, 43)),
        "joint_volume_ext": None,
    },
    "type_plates_name_vda_floor_1": {
        "search_type": 0,
        "joint_params": _p((1, 200, 0.66, 10), (2, 50, 0.5, 21)),
        "joint_volume_ext": [0, 0, -10],
    },
    "type_plates_name_vda_floor_2": {
        "search_type": 0,
        "joint_params": _p((1, 200, 0.66, 10), (2, 50, 0.5, 21)),
        "joint_volume_ext": [0, 0, -10],
    },
    # ── cross joints ─────────────────────────────────────────────────────────
    "type_plates_name_cross_and_sides_corner": {
        "search_type": 2,
        "joint_params": _p((0, 0, 0, 3), (1, 0, 0.66, 12), (2, 500, 0.5, 25), (4, 400, 0, 0)),
        "joint_volume_ext": None,
    },
    "type_plates_name_cross_corners": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": [0, 2, 0],
    },
    "type_plates_name_cross_vda_corner": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": [0, 2, 0],
    },
    "type_plates_name_cross_vda_hexshell": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": None,
    },
    "type_plates_name_cross_vda_hexshell_reciprocal": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": None,
    },
    "type_plates_name_cross_vda_single_arch": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": None,
    },
    "type_plates_name_cross_vda_shell": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": None,
    },
    "type_plates_name_cross_square_reciprocal_two_sides": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": None,
    },
    "type_plates_name_cross_square_reciprocal_iseya": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": None,
    },
    "type_plates_name_cross_ibois_pavilion": {
        "search_type": 2,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": [0, 0, -20],
    },
    "type_plates_name_cross_brussels_sports_tower": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (3, 0, 0, 35), (4, 400, 0, 0)),
        "joint_volume_ext": None,
    },
    "type_plates_name_cross_brg_slab_0": {
        "search_type": 1,
        "joint_params": _p((0, 0, 0, 3), (2, 0, 0, 25), (4, 400, 0, 0)),
        "joint_volume_ext": None,
    },
    # ── beams ─────────────────────────────────────────────────────────────────
    "type_beams_name_phanomema_node": {
        "search_type": 0,
        "joint_params": _p((1, 150, 0, 0)),
        "joint_volume_ext": None,
    },
    # ── extra datasets (not in wood_test.cpp) — sensible defaults ─────────────
    "type_plates_name_top_to_side_test": {
        "search_type": 0,
        "joint_params": _p((2, 300, 0.5, 25)),
        "joint_volume_ext": None,
    },
}

_DEFAULT_PARAMS: dict = {"search_type": 0, "joint_params": None, "joint_volume_ext": None}

for xml_path in sorted(XML_DIR.glob("*.xml")):
    root = ET.parse(xml_path).getroot()
    polylines = []
    for pl_el in root.findall("Polyline"):
        coords = []
        for pt in pl_el.findall("point"):
            coords += [
                float(pt.findtext("x")),
                float(pt.findtext("y")),
                float(pt.findtext("z")),
            ]
        polylines.append(coords)

    p = _PARAMS.get(xml_path.stem, _DEFAULT_PARAMS)
    data = {
        "name": xml_path.stem,
        "search_type": p.get("search_type", 0),
        "joint_params": p.get("joint_params"),
        "joint_volume_ext": p.get("joint_volume_ext"),
        "per_element_insertion_vectors": p.get("per_element_insertion_vectors"),
        "per_element_joint_types": p.get("per_element_joint_types"),
        "adjacency": p.get("adjacency"),
        "polylines": polylines,
    }
    out = JSON_DIR / f"{xml_path.stem}.json"
    out.write_text(json.dumps(data, indent=2))
    print(f"  {xml_path.name} -> {out.name}  ({len(polylines)} polylines)")
