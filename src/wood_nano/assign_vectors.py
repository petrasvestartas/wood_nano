from __future__ import annotations

from . import _assign_vectors


def assign_insertion_vectors(
    bot_polylines: list[list[list[float]]],
    line_starts: list[list[float]],
    line_ends: list[list[float]],
    snap_radius: float,
) -> list[tuple[int, int, float, float, float]]:
    """Match drawn lines to plate edges and compute insertion vectors.

    Parameters
    ----------
    bot_polylines : list[list[[x,y,z]]]
        Bottom outline for each plate (one list of [x,y,z] per plate).
    line_starts, line_ends : list[[x,y,z]]
        Start and end points of drawn lines (same length).
    snap_radius : float
        Maximum distance from line endpoint to edge for a match.

    Returns
    -------
    list[tuple[int, int, float, float, float]]
        ``(plate_idx, face_slot, iv_x, iv_y, iv_z)`` — one entry per matched
        (plate, edge) pair.  ``face_slot = edge_idx + 2``.
    """
    return _assign_vectors.assign_insertion_vectors(
        bot_polylines, line_starts, line_ends, float(snap_radius)
    )


def match_points_to_plate_edges(
    bot_polylines: list[list[list[float]]],
    query_points: list[list[float]],
    snap_radius: float,
) -> list[tuple[int, int, int]]:
    """Find all (query_point, plate_edge) pairs within snap_radius.

    Parameters
    ----------
    bot_polylines : list[list[[x,y,z]]]
        Bottom outline for each plate.
    query_points : list[[x,y,z]]
        Query positions (e.g. TextDot positions).
    snap_radius : float
        Maximum distance for a match.

    Returns
    -------
    list[tuple[int, int, int]]
        ``(query_idx, plate_idx, edge_idx)`` for every match.
    """
    return _assign_vectors.match_points_to_plate_edges(
        bot_polylines, query_points, float(snap_radius)
    )
