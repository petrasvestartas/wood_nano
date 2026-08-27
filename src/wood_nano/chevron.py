from __future__ import annotations

from pathlib import Path

from session_py.mesh import Mesh

from wood_nano._chevron import make_chevron_annen, make_chevron_nurbs, make_default_chevron
from wood_nano.wood_element import WoodElement, _to_mesh

_DATA_DIR = Path(__file__).parent / "data"


def annen_json_path() -> Path:
    """Return the path to the bundled annen_surfaces.json data file."""
    return _DATA_DIR / "annen_surfaces.json"


def _chevron_joint_data(ch) -> dict[str, list]:
    """Extract joinery metadata dict from a Chevron object."""
    return {
        "insertion_vectors": [list(iv) for iv in ch.insertion_vectors],
        "joints_per_face":   [list(jf) for jf in ch.joints_per_face],
        "three_valence":     [list(tv) for tv in ch.three_valence],
        "adjacency":         list(ch.adjacency),
    }


def chevron_elements(
    u_div: int = 4,
    v_division_dist: float = 900.0,
    shift: float = 0.5,
    scale: float = 0.05799,
    box_height: float = 760.0,
    top_plate_inlet: float = 80.0,
    plate_thickness: float = 40.0,
    edge_rotation: float = 1.0,
    edge_offset: float = 0.5,
    ortho_edge0: int = 1,
    ortho_edge1: int = 1,
    ortho_edge2: int = 1,
    ortho_edge3: int = 1,
) -> tuple[Mesh, list[WoodElement], list[Mesh], dict[str, list]]:
    ch = make_default_chevron(
        u_div, v_division_dist, shift, scale,
        box_height, top_plate_inlet, plate_thickness,
        edge_rotation, edge_offset,
        ortho_edge0, ortho_edge1, ortho_edge2, ortho_edge3)
    return _to_mesh(ch.mesh), [WoodElement(e) for e in ch.elements], [_to_mesh(m) for m in ch.loft_meshes], _chevron_joint_data(ch)


def chevron_elements_nurbs(
    pts: list[list[float]],
    knots_u: list[float],
    knots_v: list[float],
    degree_u: int,
    degree_v: int,
    n_u: int,
    n_v: int,
    u_div: int = 4,
    v_division_dist: float = 900.0,
    shift: float = 0.5,
    scale: float = 0.05799,
    box_height: float = 760.0,
    top_plate_inlet: float = 80.0,
    plate_thickness: float = 40.0,
    edge_rotation: float = 1.0,
    edge_offset: float = 0.5,
    ortho_edge0: int = 1,
    ortho_edge1: int = 1,
    ortho_edge2: int = 1,
    ortho_edge3: int = 1,
) -> tuple[Mesh, list[WoodElement], list[Mesh], dict[str, list]]:
    ch = make_chevron_nurbs(
        pts, knots_u, knots_v, degree_u, degree_v, n_u, n_v,
        u_div, v_division_dist, shift, scale,
        box_height, top_plate_inlet, plate_thickness,
        edge_rotation, edge_offset,
        ortho_edge0, ortho_edge1, ortho_edge2, ortho_edge3)
    return _to_mesh(ch.mesh), [WoodElement(e) for e in ch.elements], [_to_mesh(m) for m in ch.loft_meshes], _chevron_joint_data(ch)


def chevron_elements_annen(
    json_path: str | None = None,
    surface_idx: int = 0,
    u_div: int = 4,
    v_division_dist: float = 900.0,
    shift: float = 0.5,
    scale: float = 0.05799,
    box_height: float = 760.0,
    top_plate_inlet: float = 80.0,
    plate_thickness: float = 40.0,
    edge_rotation: float = 1.0,
    edge_offset: float = 0.5,
    ortho_edge0: int = 1,
    ortho_edge1: int = 1,
    ortho_edge2: int = 1,
    ortho_edge3: int = 1,
) -> tuple[Mesh, list[WoodElement], list[Mesh], dict[str, list]]:
    resolved = str(json_path) if json_path is not None else str(annen_json_path())
    ch = make_chevron_annen(
        resolved, surface_idx,
        u_div, v_division_dist, shift, scale,
        box_height, top_plate_inlet, plate_thickness,
        edge_rotation, edge_offset,
        ortho_edge0, ortho_edge1, ortho_edge2, ortho_edge3)
    return _to_mesh(ch.mesh), [WoodElement(e) for e in ch.elements], [_to_mesh(m) for m in ch.loft_meshes], _chevron_joint_data(ch)
