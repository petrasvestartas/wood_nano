
from pathlib import Path

from compas.datastructures import Mesh

from wood_nano._diamond_mesh import (
    make_default_diamond_mesh,
    make_diamond_mesh_annen,
    make_diamond_mesh_from_surface,
)
from wood_nano_compas.convert import mesh_from_cpp
from wood_nano_compas.wood_element import WoodElementCompas

_DATA_DIR = Path(__file__).parent.parent / "wood_nano" / "data"


def diamond_mesh_elements(
    u_div: int = 8,
    v_div: int = 4,
    thickness: float = 10.0,
    chamfer: float = 1.0,
    chamfer_angle: float = 180.0,
) -> tuple[Mesh, list[WoodElementCompas]]:
    """Diamond-pattern triangular mesh + plate elements from the built-in arch surface."""
    dm = make_default_diamond_mesh(u_div, v_div, thickness, chamfer, chamfer_angle)
    return mesh_from_cpp(dm.mesh), [WoodElementCompas(e) for e in dm.elements]


def diamond_mesh_elements_annen(
    json_path: str | None = None,
    surface_idx: int = 0,
    u_div: int = 8,
    v_div: int = 4,
    thickness: float = 10.0,
    chamfer: float = 1.0,
    chamfer_angle: float = 180.0,
) -> tuple[Mesh, list[WoodElementCompas]]:
    """Diamond-pattern triangular mesh + plate elements from an Annen NURBS surface."""
    resolved = str(json_path) if json_path is not None else str(_DATA_DIR / "annen_surfaces.json")
    dm = make_diamond_mesh_annen(resolved, surface_idx, u_div, v_div, thickness, chamfer, chamfer_angle)
    return mesh_from_cpp(dm.mesh), [WoodElementCompas(e) for e in dm.elements]


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
) -> tuple[Mesh, list[WoodElementCompas]]:
    """Diamond-pattern triangular mesh + plate elements from a user-supplied NURBS surface."""
    dm = make_diamond_mesh_from_surface(
        pts, knots_u, knots_v, degree_u, degree_v, n_u, n_v,
        u_div, v_div, thickness, chamfer, chamfer_angle)
    return mesh_from_cpp(dm.mesh), [WoodElementCompas(e) for e in dm.elements]
