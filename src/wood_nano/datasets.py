from __future__ import annotations

import json
from pathlib import Path

from . import _datasets

# Directory where JSON dataset files live (produced by convert_xml_to_json.py).
DATASETS_DIR: Path = Path(__file__).parent.parent.parent / "examples_compas_wood" / "datasets"


def load_dataset(name: str) -> tuple[list, list, dict]:
    """Load a named JSON dataset → (bottom_polylines, top_polylines, params).

    bottom/top: list of polylines, each polyline is list[[x, y, z]].
    params: dict with keys search_type, joint_params, joint_volume_ext,
            per_element_insertion_vectors, per_element_joint_types, adjacency.
    """
    path = DATASETS_DIR / f"{name}.json"
    bottom, top = _datasets.load_dataset(str(path))
    data = json.loads(path.read_text())
    raw_iv = data.get("per_element_insertion_vectors")
    # JSON stores per-element vectors as [[x,y,z],...]; flatten to [x,y,z,x,y,z,...] per element.
    flat_iv = (
        [[c for xyz in el_iv for c in xyz] for el_iv in raw_iv]
        if raw_iv else None
    )
    params = {
        "search_type": data.get("search_type", 0),
        "joint_params": data.get("joint_params"),
        "joint_volume_ext": data.get("joint_volume_ext"),
        "per_element_insertion_vectors": flat_iv,
        "per_element_joint_types": data.get("per_element_joint_types"),
        "adjacency": data.get("adjacency"),
    }
    return bottom, top, params
