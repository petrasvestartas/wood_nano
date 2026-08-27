from __future__ import annotations

from typing import Any

from session_py.mesh import Mesh
from session_py.point import Point
from session_py.polyline import Polyline

from wood_nano import _reciprocal_rotation
from wood_nano._reciprocal_rotation import (
    make_default_reciprocal_rotation,
    make_default_reciprocal_rotation_typed,
    make_reciprocal_rotation_from_mesh,
    make_reciprocal_rotation_from_surface,
)
from wood_nano.wood_element import _to_mesh, unweld_mesh as _unweld_mesh


def _pts_to_polyline(pts: list[list[float]]) -> Polyline:
    return Polyline([Point(float(p[0]), float(p[1]), float(p[2])) for p in pts])


def _unpack(
    rb: Any,
    beam_offsets: list[float] | None = None,
    unweld_beams: bool = True,
) -> tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]:
    # Offsets are applied by C++ on the still-C++ meshes, so the CDT
    # triangulation and face_holes of offset beams survive (the old Python
    # rebuild dropped both), and the geometry rule holds: this layer only
    # converts formats.
    if beam_offsets:
        _reciprocal_rotation.apply_beam_offsets(rb, [float(o) for o in beam_offsets])
    dome  = _to_mesh(rb.dome_mesh)
    side0 = [_pts_to_polyline(p) for p in rb.side0]
    side1 = [_pts_to_polyline(p) for p in rb.side1]
    beams = [_to_mesh(m) for m in rb.beams]
    if unweld_beams:
        beams = [_unweld_mesh(b) for b in beams]
    return dome, beams, side0, side1


def reciprocal_rotation_elements(
    nx: int = 12,
    ny: int = 10,
    W: float = 12000.0,
    D: float = 10000.0,
    h: float = 3000.0,
    mesh_type: str = "quad",
    angle: float = 0.35,
    scale: float = 1.4,
    beam_w: float = 100.0,
    beam_h: float = 0.0,
    extend_factor: float = 5.0,
    cut_offset_factor: float = 1.0,
    beam_offsets: list[float] | None = None,
    unweld_beams: bool = True,
) -> tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]:
    """Reciprocal rotation frame on a sinusoidal dome (rotation-based nexorade).

    Parameters
    ----------
    nx, ny : int
        Grid resolution of the dome mesh.
    W, D : float
        Dome width and depth.
    h : float
        Dome peak height.
    mesh_type : str
        Subdivision pattern: "quad" | "hex" | "diamond".
    angle, scale, beam_w, beam_h, extend_factor, cut_offset_factor :
        Reciprocal frame parameters. beam_h=0 defaults to beam_w*2.
    beam_offsets : list[float] | None
        Per-direction offsets along each beam's local height (normal) axis:
        2 values for quad/diamond (u/v), 3 values for hex.
        None or all-zero = no translation.
    unweld_beams : bool
        If True, return beams with per-face vertex copies (flat shading).

    Returns
    -------
    tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]
        (dome_mesh, beam_meshes, side0_outlines, side1_outlines)
    """
    rb = make_default_reciprocal_rotation_typed(
        nx, ny, W, D, h, mesh_type,
        angle, scale, beam_w, beam_h,
        extend_factor, cut_offset_factor)
    return _unpack(rb, beam_offsets=beam_offsets, unweld_beams=unweld_beams)


def reciprocal_rotation_elements_from_surface(
    pts: list[list[float]],
    knots_u: list[float],
    knots_v: list[float],
    degree_u: int,
    degree_v: int,
    n_u: int,
    n_v: int,
    mesh_type: str = "quad",
    u_div: int = 12,
    v_div: int = 10,
    angle: float = 0.35,
    scale: float = 1.4,
    beam_w: float = 100.0,
    beam_h: float = 0.0,
    extend_factor: float = 5.0,
    cut_offset_factor: float = 1.0,
    beam_offsets: list[float] | None = None,
    unweld_beams: bool = True,
) -> tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]:
    """Reciprocal rotation frame on a NURBS surface.

    Parameters
    ----------
    pts : list[list[float]]
        Control points in row-major order (n_u × n_v).
    knots_u, knots_v : list[float]
        OpenNURBS knot vectors (first/last entry already stripped).
    degree_u, degree_v : int
        Surface degree in each direction.
    n_u, n_v : int
        Control-point count in each direction.
    mesh_type : str
        Subdivision method: "quad" | "hex" | "diamond".
    u_div, v_div : int
        Mesh resolution along each surface direction.
    angle, scale, beam_w, beam_h, extend_factor, cut_offset_factor :
        Reciprocal frame parameters. beam_h=0 defaults to beam_w*2.
    beam_offsets : list[float] | None
        Per-direction offsets along each beam's local height (normal) axis.
    unweld_beams : bool
        If True, return beams with per-face vertex copies (flat shading).

    Returns
    -------
    tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]
        (base_mesh, beam_meshes, side0_outlines, side1_outlines)
    """
    rb = make_reciprocal_rotation_from_surface(
        pts, knots_u, knots_v,
        degree_u, degree_v, n_u, n_v,
        mesh_type, u_div, v_div,
        angle, scale, beam_w, beam_h,
        extend_factor, cut_offset_factor)
    return _unpack(rb, beam_offsets=beam_offsets, unweld_beams=unweld_beams)


def reciprocal_rotation_elements_from_mesh(
    vertices: list[list[float]],
    faces: list[list[int]],
    angle: float = 0.35,
    scale: float = 1.4,
    beam_w: float = 100.0,
    beam_h: float = 0.0,
    extend_factor: float = 5.0,
    cut_offset_factor: float = 1.0,
    beam_offsets: list[float] | None = None,
    unweld_beams: bool = True,
) -> tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]:
    """Reciprocal rotation frame on a user-supplied mesh.

    Parameters
    ----------
    vertices : list[list[float]]
        N×3 vertex coordinate list.
    faces : list[list[int]]
        Face vertex-index lists (quads or triangles).
    angle, scale, beam_w, extend_factor, cut_offset_factor :
        Reciprocal frame parameters.
    beam_offsets : list[float] | None
        Per-direction offsets along each beam's local height (normal) axis.
    unweld_beams : bool
        If True, return beams with per-face vertex copies (flat shading).

    Returns
    -------
    tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]
        (base_mesh, beam_meshes, side0_outlines, side1_outlines)
    """
    rb = make_reciprocal_rotation_from_mesh(
        vertices, faces,
        angle, scale, beam_w, beam_h,
        extend_factor, cut_offset_factor)
    return _unpack(rb, beam_offsets=beam_offsets, unweld_beams=unweld_beams)
