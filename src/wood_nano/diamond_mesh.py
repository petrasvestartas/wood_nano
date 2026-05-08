from __future__ import annotations

from session_py.mesh import Mesh

from wood_nano._diamond_mesh import (
    make_default_diamond_mesh,
    make_diamond_mesh_annen,
    make_diamond_mesh_from_surface,
)
from wood_nano.wood_element import WoodElement, _to_mesh


def diamond_mesh_elements(
    u_div: int = 8,
    v_div: int = 4,
    thickness: float = 10.0,
    chamfer: float = 1.0,
    chamfer_angle: float = 180.0,
) -> tuple[Mesh, list[WoodElement]]:
    """Diamond-pattern triangular mesh + plate elements from the built-in arch surface.

    Parameters
    ----------
    u_div, v_div : int
        Subdivision counts along U and V.
    thickness : float
        Plate thickness (mm).
    chamfer : float
        Chamfer distance at sharp corners.
    chamfer_angle : float
        Corners with edge-vector angle < this (degrees) are chamfered.

    Returns
    -------
    tuple[Mesh, list[WoodElement]]
        Shell mesh and one WoodElement per triangular face.
    """
    dm = make_default_diamond_mesh(u_div, v_div, thickness, chamfer, chamfer_angle)
    return _to_mesh(dm.mesh), [WoodElement(e) for e in dm.elements]


def diamond_mesh_elements_annen(
    json_path: str,
    surface_idx: int = 0,
    u_div: int = 8,
    v_div: int = 4,
    thickness: float = 10.0,
    chamfer: float = 1.0,
    chamfer_angle: float = 180.0,
) -> tuple[Mesh, list[WoodElement]]:
    """Diamond-pattern triangular mesh + plate elements from an Annen NURBS surface.

    Parameters
    ----------
    json_path : str
        Path to the annen_surfaces.json file.
    surface_idx : int
        Surface index 0..22 in the Annen dataset.
    u_div, v_div : int
        Subdivision counts.
    thickness : float
        Plate thickness (mm).
    chamfer : float
        Chamfer distance at sharp corners.
    chamfer_angle : float
        Corners with edge-vector angle < this (degrees) are chamfered.

    Returns
    -------
    tuple[Mesh, list[WoodElement]]
        Shell mesh and one WoodElement per triangular face.
    """
    dm = make_diamond_mesh_annen(json_path, surface_idx, u_div, v_div,
                                  thickness, chamfer, chamfer_angle)
    return _to_mesh(dm.mesh), [WoodElement(e) for e in dm.elements]


def diamond_mesh_elements_from_surface(
    pts: list,
    knots_u: list,
    knots_v: list,
    degree_u: int,
    degree_v: int,
    n_u: int,
    n_v: int,
    u_div: int = 8,
    v_div: int = 4,
    thickness: float = 10.0,
    chamfer: float = 1.0,
    chamfer_angle: float = 180.0,
) -> tuple[Mesh, list[WoodElement]]:
    """Diamond-pattern triangular mesh + plate elements from a user-supplied NURBS surface.

    Parameters
    ----------
    pts : list of [x, y, z]
        Control points in row-major order (u varies slowest), length = n_u * n_v.
    knots_u, knots_v : list of float
        OpenNURBS knot vectors (first/last already stripped).
    degree_u, degree_v : int
        Polynomial degree in each direction.
    n_u, n_v : int
        Control point counts.
    u_div, v_div : int
        Subdivision counts.
    thickness : float
        Plate thickness (mm).
    chamfer : float
        Chamfer distance at sharp corners.
    chamfer_angle : float
        Corners with edge-vector angle < this (degrees) are chamfered.

    Returns
    -------
    tuple[Mesh, list[WoodElement]]
        Shell mesh and one WoodElement per triangular face.
    """
    dm = make_diamond_mesh_from_surface(
        pts, knots_u, knots_v, degree_u, degree_v, n_u, n_v,
        u_div, v_div, thickness, chamfer, chamfer_angle,
    )
    return _to_mesh(dm.mesh), [WoodElement(e) for e in dm.elements]
