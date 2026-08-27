
import math

from compas.datastructures import Mesh
from compas.geometry import Polyline

from wood_nano._reciprocal_rotation import (
    make_default_reciprocal_rotation_typed,
    make_reciprocal_rotation_from_mesh,
    make_reciprocal_rotation_from_surface,
)
from wood_nano_compas.convert import mesh_from_cpp, polyline_from_cpp


def _translate_pts(pts: list, dx: float, dy: float, dz: float) -> list:
    return [[p[0] + dx, p[1] + dy, p[2] + dz] for p in pts]


def _translate_mesh_dict(d: dict, dx: float, dy: float, dz: float) -> dict:
    return {**d, "vertices": _translate_pts(list(d["vertices"]), dx, dy, dz)}


def _apply_beam_offsets_raw(
    beam_dicts: list,
    side0_raw: list,
    side1_raw: list,
    beam_dirs: list,
    beam_ups: list,
    beam_offsets: list[float],
) -> tuple[list, list, list]:
    if not beam_offsets or all(o == 0.0 for o in beam_offsets):
        return beam_dicts, side0_raw, side1_raw

    n_dirs = len(beam_offsets)
    bin_width = math.pi / n_dirs
    new_beams = list(beam_dicts)
    new_s0 = list(side0_raw)
    new_s1 = list(side1_raw)

    for i, bm in enumerate(beam_dicts):
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
        new_beams[i] = _translate_mesh_dict(bm, dx, dy, dz)
        if i < len(side0_raw):
            new_s0[i] = _translate_pts(list(side0_raw[i]), dx, dy, dz)
        if i < len(side1_raw):
            new_s1[i] = _translate_pts(list(side1_raw[i]), dx, dy, dz)

    return new_beams, new_s0, new_s1


def _unpack(rb, beam_offsets: list[float] | None):
    beam_dicts = list(rb.beams)
    side0_raw  = [list(p) for p in rb.side0]
    side1_raw  = [list(p) for p in rb.side1]
    beam_dirs  = list(rb.beam_dirs)
    beam_ups   = list(rb.beam_ups)

    if beam_offsets:
        beam_dicts, side0_raw, side1_raw = _apply_beam_offsets_raw(
            beam_dicts, side0_raw, side1_raw, beam_dirs, beam_ups, beam_offsets)

    dome  = mesh_from_cpp(rb.dome_mesh)
    beams = [mesh_from_cpp(m) for m in beam_dicts]
    side0 = [polyline_from_cpp(p) for p in side0_raw]
    side1 = [polyline_from_cpp(p) for p in side1_raw]
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
) -> tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]:
    """Reciprocal rotation frame on a sinusoidal dome."""
    rb = make_default_reciprocal_rotation_typed(
        nx, ny, W, D, h, mesh_type,
        angle, scale, beam_w, beam_h,
        extend_factor, cut_offset_factor)
    return _unpack(rb, beam_offsets)


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
) -> tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]:
    """Reciprocal rotation frame on a NURBS surface."""
    rb = make_reciprocal_rotation_from_surface(
        pts, knots_u, knots_v, degree_u, degree_v, n_u, n_v,
        mesh_type, u_div, v_div,
        angle, scale, beam_w, beam_h,
        extend_factor, cut_offset_factor)
    return _unpack(rb, beam_offsets)


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
) -> tuple[Mesh, list[Mesh], list[Polyline], list[Polyline]]:
    """Reciprocal rotation frame on a user-supplied mesh."""
    rb = make_reciprocal_rotation_from_mesh(
        vertices, faces,
        angle, scale, beam_w, beam_h,
        extend_factor, cut_offset_factor)
    return _unpack(rb, beam_offsets)
