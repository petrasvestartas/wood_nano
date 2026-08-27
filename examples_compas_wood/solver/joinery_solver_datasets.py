from __future__ import annotations

import sys

from compas.colors import Color
from compas_viewer import Viewer

from wood_nano import load_dataset
from wood_nano_compas import joinery_solver_elements

# Usage: uv run python examples_compas_wood/solver/joinery_solver_datasets.py <dataset_name>
# Example: uv run python examples_compas_wood/solver/joinery_solver_datasets.py type_plates_name_cross_vda_hexshell

name = sys.argv[1] if len(sys.argv) > 1 else "type_plates_name_hexbox_and_corner"

bottom, top, p = load_dataset(name)
print(f"{name}: {len(bottom)} plates")

elems, joints = joinery_solver_elements(
    bottom, top,
    search_type=p["search_type"],
    joint_params=p["joint_params"],
    joint_volume_ext=p["joint_volume_ext"],
    per_element_insertion_vectors=p["per_element_insertion_vectors"],
    per_element_joint_types=p["per_element_joint_types"],
    adjacency=p["adjacency"],
)
print(f"  -> {len(joints)} joints detected")

_grey = Color(0.8, 0.8, 0.8)
viewer = Viewer()
for i, el in enumerate(elems):
    grp = viewer.scene.add_group(name=f"el_{i}")
    grp.add(el.loft_mesh(), show_lines=False, facecolor=_grey)
    for k, pl in enumerate(el.top_outlines):
        grp.add(pl, name=f"top_{k}")
    for k, pl in enumerate(el.bottom_outlines):
        grp.add(pl, name=f"bot_{k}")
for j, jt in enumerate(joints):
    grp = viewer.scene.add_group(name=f"joint_{j}")
    grp.add(jt.area, name="area")
    for v, vol in enumerate(jt.volumes):
        grp.add(vol, name=f"vol_{v}", linecolor=Color(0.9, 0.2, 0.2))
    for ln_i, ln in enumerate(jt.lines):
        grp.add(ln, name=f"line_{ln_i}", linecolor=Color(0.0, 0.7, 0.3))
viewer.show()
