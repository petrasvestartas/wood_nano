from __future__ import annotations

from session_py.mesh import Mesh
from session_py.point import Point
from session_py.polyline import Polyline

from wood_nano._reciprocal_beam import (
    make_default_reciprocal_beam,
    make_reciprocal_beam_from_mesh,
)
from wood_nano.wood_element import _to_mesh


def _pts_to_polyline(pts: list) -> Polyline:
    return Polyline([Point(float(p[0]), float(p[1]), float(p[2])) for p in pts])


def reciprocal_beam_elements(
    nx: int = 12,
    ny: int = 10,
    W: float = 12.0,
    D: float = 10.0,
    h: float = 3.0,
    angle: float = 0.35,
    scale: float = 1.4,
    beam_w: float = 0.10,
    extend_factor: float = 5.0,
    cut_offset_factor: float = 1.0,
) -> tuple:
    """Reciprocal beam frame on sinusoidal dome → dome + beams + side outlines.

    Parameters
    ----------
    nx, ny : int
        Grid dimensions of the dome mesh.
    W, D : float
        Dome width and depth.
    h : float
        Dome peak height.
    angle : float
        Reciprocal rotation angle (radians).
    scale : float
        Reciprocal scale factor.
    beam_w : float
        Beam cross-section width. Height = 2 × beam_w.
    extend_factor : float
        Extension past endpoints = extend_factor × beam_w.
    cut_offset_factor : float
        Cut-plane offset = cut_offset_factor × beam_w.

    Returns
    -------
    tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]
        (dome_mesh, beam_meshes, side0_outlines, side1_outlines)
    """
    rb = make_default_reciprocal_beam(
        nx, ny, W, D, h, angle, scale, beam_w,
        extend_factor, cut_offset_factor)

    dome  = _to_mesh(rb.dome_mesh)
    beams = [_to_mesh(m) for m in rb.beams]
    side0 = [_pts_to_polyline(pts) for pts in rb.side0]
    side1 = [_pts_to_polyline(pts) for pts in rb.side1]
    return dome, beams, side0, side1


def reciprocal_beam_elements_from_mesh(
    vertices,
    faces,
    angle: float = 0.35,
    scale: float = 1.4,
    beam_w: float = 0.10,
    extend_factor: float = 5.0,
    cut_offset_factor: float = 1.0,
) -> tuple:
    """Reciprocal beam frame on a user-supplied quad mesh.

    Parameters
    ----------
    vertices : list[list[float]]
        N×3 vertex coordinate list.
    faces : list[list[int]]
        Face vertex-index lists (quads or triangles).
    angle : float
        Reciprocal rotation angle (radians).
    scale : float
        Reciprocal scale factor (scales each beam line about its midpoint).
    beam_w : float
        Beam cross-section width. Height = 2 × beam_w.
    extend_factor : float
        Extension past endpoints = extend_factor × beam_w.
    cut_offset_factor : float
        Cut-plane offset = cut_offset_factor × beam_w.

    Returns
    -------
    tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]
        (base_mesh, beam_meshes, side0_outlines, side1_outlines)
    """
    rb = make_reciprocal_beam_from_mesh(
        vertices, faces,
        angle, scale, beam_w,
        extend_factor, cut_offset_factor)

    dome  = _to_mesh(rb.dome_mesh)
    beams = [_to_mesh(m) for m in rb.beams]
    side0 = [_pts_to_polyline(pts) for pts in rb.side0]
    side1 = [_pts_to_polyline(pts) for pts in rb.side1]
    return dome, beams, side0, side1
