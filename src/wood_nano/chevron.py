from __future__ import annotations

from wood_nano._chevron import make_chevron_annen, make_default_chevron
from wood_nano.wood_element import WoodElement, _to_mesh


def chevron_elements(
    u_divisions: int = 4,
    v_division_dist: float = 900.0,
    shift: float = 0.5,
    scale: float = 0.05799,
    box_height: float = 760.0,
    top_plate_inlet: float = 80.0,
    plate_thickness: float = 40.0,
    edge_rotation: float = 1.0,
    edge_offset: float = 0.5,
) -> tuple:
    """Chevron shell from built-in flat surface → shell mesh + plate elements.

    Parameters
    ----------
    u_divisions : int
        Number of strips across the short surface axis.
    v_division_dist : float
        Target panel height along the long axis (mm).
    shift : float
        Fraction of v-step for the zigzag peak offset. Default 0.5.
    scale : float
        Growth factor per row (adaptive row spacing). Default 0.05799.
    box_height : float
        Total plate box height (mm).
    top_plate_inlet : float
        Inset of the top/bottom face plates from the box edge (mm).
    plate_thickness : float
        Plate thickness (mm). Must not be zero.
    edge_rotation : float
        Degrees of rotation applied to chevron joint edges.
    edge_offset : float
        Fraction of plate_thickness for translating even chevron edges.

    Returns
    -------
    tuple[session_py.Mesh, list[WoodElement]]
        Shell mesh and 4×n_faces plate elements.
    """
    ch = make_default_chevron(
        u_divisions, v_division_dist, shift, scale,
        box_height, top_plate_inlet, plate_thickness,
        edge_rotation, edge_offset)
    return _to_mesh(ch.mesh), [WoodElement(e) for e in ch.elements]


def chevron_elements_annen(
    json_path: str,
    surface_idx: int = 0,
    u_divisions: int = 4,
    v_division_dist: float = 900.0,
    shift: float = 0.5,
    scale: float = 0.05799,
    box_height: float = 760.0,
    top_plate_inlet: float = 80.0,
    plate_thickness: float = 40.0,
    edge_rotation: float = 1.0,
    edge_offset: float = 0.5,
) -> tuple:
    """Chevron shell from one of the 23 Annen building NURBS surfaces.

    Parameters
    ----------
    json_path : str
        Path to ``annen_surfaces.json``.
    surface_idx : int
        Index into the JSON array (0–22).

    Returns
    -------
    tuple[session_py.Mesh, list[WoodElement]]
        Shell mesh and 4×n_faces plate elements.
    """
    ch = make_chevron_annen(
        json_path, surface_idx,
        u_divisions, v_division_dist, shift, scale,
        box_height, top_plate_inlet, plate_thickness,
        edge_rotation, edge_offset)
    return _to_mesh(ch.mesh), [WoodElement(e) for e in ch.elements]
