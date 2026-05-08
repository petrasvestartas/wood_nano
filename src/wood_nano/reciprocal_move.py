from __future__ import annotations

import math

from session_py.mesh import Mesh
from session_py.point import Point
from session_py.polyline import Polyline

from wood_nano._reciprocal_move import (
    make_default_reciprocal_move_typed,
    make_reciprocal_move_from_mesh,
    make_reciprocal_move_from_surface,
)
from wood_nano.wood_element import _to_mesh, unweld_mesh as _unweld_mesh


def _pts_to_polyline(pts: list) -> Polyline:
    return Polyline([Point(float(p[0]), float(p[1]), float(p[2])) for p in pts])


def _translate_mesh(mesh: Mesh, dx: float, dy: float, dz: float) -> Mesh:
    v_keys = sorted(mesh.vertex.keys())
    key_to_idx = {k: idx for idx, k in enumerate(v_keys)}
    new_pts = [Point(float(mesh.vertex[k][0]) + dx,
                     float(mesh.vertex[k][1]) + dy,
                     float(mesh.vertex[k][2]) + dz) for k in v_keys]
    f_keys = sorted(mesh.face.keys())
    new_faces = [[key_to_idx[vk] for vk in mesh.face[fk]] for fk in f_keys]
    return Mesh.from_vertices_and_faces(new_pts, new_faces)


def _translate_polyline(pl: Polyline, dx: float, dy: float, dz: float) -> Polyline:
    return Polyline([Point(float(p[0]) + dx, float(p[1]) + dy, float(p[2]) + dz)
                     for p in pl.get_points()])


def _apply_beam_offsets(beams, side0, side1, beam_dirs, beam_ups, beam_offsets):
    """Translate each beam along its up (face-normal) direction by a per-group offset.

    Parameters
    ----------
    beam_dirs : list of [dx, dy, dz]   — unit axis direction per beam
    beam_ups  : list of [ux, uy, uz]   — unit face-normal per beam
    beam_offsets : list[float]         — scalar per direction group
    """
    if not beam_offsets or all(o == 0.0 for o in beam_offsets):
        return beams, side0, side1

    n_dirs = len(beam_offsets)
    bin_width = math.pi / n_dirs

    new_beams = list(beams)
    new_s0    = list(side0)
    new_s1    = list(side1)

    for i, bm in enumerate(beams):
        if i >= len(beam_dirs) or i >= len(beam_ups):
            continue
        bdx, bdy = beam_dirs[i][0], beam_dirs[i][1]
        angle = math.atan2(bdy, bdx) % math.pi
        dir_idx = int((angle + bin_width * 0.5) / bin_width) % n_dirs
        offset = beam_offsets[dir_idx]
        if offset == 0.0:
            continue
        ux, uy, uz = beam_ups[i][0], beam_ups[i][1], beam_ups[i][2]
        if uz < 0.0:
            ux, uy, uz = -ux, -uy, -uz
        dx, dy, dz = ux * offset, uy * offset, uz * offset
        new_beams[i] = _translate_mesh(bm, dx, dy, dz)
        if i < len(side0):
            new_s0[i] = _translate_polyline(side0[i], dx, dy, dz)
        if i < len(side1):
            new_s1[i] = _translate_polyline(side1[i], dx, dy, dz)

    return new_beams, new_s0, new_s1


def _unpack(rm, beam_offsets=None, unweld_beams: bool = True) -> tuple:
    dome      = _to_mesh(rm.dome_mesh)
    side0     = [_pts_to_polyline(p) for p in rm.side0]
    side1     = [_pts_to_polyline(p) for p in rm.side1]
    beams     = [_to_mesh(m) for m in rm.beams]
    beam_dirs = list(rm.beam_dirs)
    beam_ups  = list(rm.beam_ups)
    if beam_offsets:
        beams, side0, side1 = _apply_beam_offsets(
            beams, side0, side1, beam_dirs, beam_ups, beam_offsets)
    if unweld_beams:
        beams = [_unweld_mesh(b) for b in beams]
    return dome, beams, side0, side1


def reciprocal_move_elements(
    nx: int = 12,
    ny: int = 10,
    W: float = 12000.0,
    D: float = 10000.0,
    h: float = 3000.0,
    mesh_type: str = "quad",
    angle: float = 50.0,
    beam_w: float = 100.0,
    beam_h: float = 0.0,
    extend_factor: float = 5.0,
    cut_offset_factor: float = 1.0,
    beam_offsets: list | None = None,
    unweld_beams: bool = True,
) -> tuple:
    """Translation-based reciprocal frame on a sinusoidal dome.

    Each mesh edge is translated in its face plane by a bisector direction,
    then trimmed against neighboring edges. The result interlocks without
    cut planes (Rizzuto/Larsen nexorade via translation).

    Parameters
    ----------
    nx, ny : int
        Grid resolution of the dome mesh.
    W, D, h : float
        Dome width, depth, and peak height.
    mesh_type : str
        Subdivision pattern: "quad" | "hex" | "diamond".
    angle : float
        Translation distance in model units (e.g. mm). Larger = more offset.
        Typical range: 0.3–0.7 × beam_w.
    beam_w : float
        Beam cross-section width.
    beam_h : float
        Beam cross-section height (0 → 2 × beam_w).
    extend_factor : float
        Initial extension multiplier before trimming (× beam_w).
    beam_offsets : list[float] | None
        Per-direction height offsets (along face normal):
        2 values for quad/diamond, 3 for hex. None = no offset.
    unweld_beams : bool
        If True, return beams with per-face vertex copies (flat shading).

    Returns
    -------
    tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]
        (dome_mesh, beam_meshes, side0_outlines, side1_outlines)
    """
    rm = make_default_reciprocal_move_typed(
        nx, ny, W, D, h, mesh_type,
        angle, beam_w, beam_h,
        extend_factor, cut_offset_factor)
    return _unpack(rm, beam_offsets=beam_offsets, unweld_beams=unweld_beams)


def reciprocal_move_elements_from_surface(
    pts,
    knots_u,
    knots_v,
    degree_u: int,
    degree_v: int,
    n_u: int,
    n_v: int,
    mesh_type: str = "quad",
    u_count: int = 12,
    v_count: int = 10,
    angle: float = 50.0,
    beam_w: float = 100.0,
    beam_h: float = 0.0,
    extend_factor: float = 5.0,
    cut_offset_factor: float = 1.0,
    beam_offsets: list | None = None,
    unweld_beams: bool = True,
) -> tuple:
    """Translation-based reciprocal frame on a NURBS surface.

    Parameters
    ----------
    pts : list[list[float]]
        Control points in row-major order (n_u × n_v).
    knots_u, knots_v : list[float]
        OpenNURBS knot vectors.
    degree_u, degree_v : int
        Surface degree.
    n_u, n_v : int
        Control-point count.
    mesh_type : str
        "quad" | "hex" | "diamond".
    u_count, v_count : int
        Mesh resolution.
    angle : float
        Translation distance in model units.
    beam_w, beam_h, extend_factor :
        Beam cross-section and extension parameters.
    beam_offsets : list[float] | None
        Per-direction height offsets.
    unweld_beams : bool
        Flat-shading vertex copies.

    Returns
    -------
    tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]
        (base_mesh, beam_meshes, side0_outlines, side1_outlines)
    """
    rm = make_reciprocal_move_from_surface(
        pts, knots_u, knots_v,
        degree_u, degree_v, n_u, n_v,
        mesh_type, u_count, v_count,
        angle, beam_w, beam_h,
        extend_factor, cut_offset_factor)
    return _unpack(rm, beam_offsets=beam_offsets, unweld_beams=unweld_beams)


def reciprocal_move_elements_from_mesh(
    vertices,
    faces,
    angle: float = 50.0,
    beam_w: float = 100.0,
    beam_h: float = 0.0,
    extend_factor: float = 5.0,
    cut_offset_factor: float = 1.0,
    beam_offsets: list | None = None,
    unweld_beams: bool = True,
) -> tuple:
    """Translation-based reciprocal frame on a user-supplied mesh.

    Parameters
    ----------
    vertices : list[list[float]]
        N×3 vertex coordinate list.
    faces : list[list[int]]
        Face vertex-index lists.
    angle : float
        Translation distance in model units.
    beam_w, beam_h, extend_factor :
        Beam cross-section and extension parameters.
    beam_offsets : list[float] | None
        Per-direction height offsets.
    unweld_beams : bool
        Flat-shading vertex copies.

    Returns
    -------
    tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]
        (base_mesh, beam_meshes, side0_outlines, side1_outlines)
    """
    rm = make_reciprocal_move_from_mesh(
        vertices, faces,
        angle, beam_w, beam_h,
        extend_factor, cut_offset_factor)
    return _unpack(rm, beam_offsets=beam_offsets, unweld_beams=unweld_beams)
