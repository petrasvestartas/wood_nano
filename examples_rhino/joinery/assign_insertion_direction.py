#! python3
"""Assign per-edge insertion directions to plates using Rhino line objects.

Workflow
--------
1. Run and select the plate objects (bot/top curves or meshes from a template run).
   Press Enter when done.
2. Select line objects — one line per plate edge that needs an explicit direction:
     - **Start point** — placed near the midpoint of the target edge; used to
       detect which plate and which edge the line belongs to.
     - **Direction** (start → end) — becomes the insertion Vec3 for that edge's
       face slot in the joinery solver.
3. Each line's start point is matched to the nearest edge midpoint of the
   previously selected plates, within ``_MAX_SNAP_RADIUS`` mm.  The normalised
   direction is stored in the ``insertion_vector`` UserString at the corresponding
   face slot (face 0 = bottom cap, face 1 = top cap, faces 2..N+1 = side edges).
4. Existing ``joint_types`` UserStrings are preserved unchanged.
5. Run ``joinery_solver.py`` — it reads the updated vectors and passes them to
   the C++ solver.

Notes
-----
- Two lines hitting the same edge: last one wins.
- Lines whose start point is farther than ``_MAX_SNAP_RADIUS`` from every selected
  plate edge midpoint are skipped with a warning.
- Only linear curves are accepted; non-linear curves are skipped.
"""

import json
import math

import Rhino
import Rhino.DocObjects
import Rhino.Geometry as rg
import scriptcontext as sc
import rhinoscriptsyntax as rs
from wood_nano.plate_topology import PlateTopology


_log = Rhino.RhinoApp.WriteLine
_MAX_SNAP_RADIUS = 500.0   # mm


def _write_plate_userstring(plate_id, key, value_str):
    """Write one UserString to bot/top objects of a plate without touching others."""
    pid_str = str(int(plate_id))
    for obj in sc.doc.Objects.GetObjectList(Rhino.DocObjects.ObjectType.AnyObject):
        if obj.Attributes.GetUserString("plate_id") != pid_str:
            continue
        if obj.Attributes.GetUserString("plate_role") in ("bot", "top"):
            obj.Attributes.SetUserString(key, value_str)
            obj.CommitChanges()


def _get_bot_polyline_points(bot_guid):
    """Return list[rg.Point3d] from a bot curve GUID, or None on failure."""
    if bot_guid is None:
        return None
    obj = sc.doc.Objects.FindId(bot_guid)
    if obj is None:
        return None
    ok, rh_pl = obj.Geometry.TryGetPolyline()
    if not ok or rh_pl is None:
        return None
    return list(rh_pl)


def run():
    # 1. Select plate objects
    plate_guids = rs.GetObjects(
        "Select plate objects (bot/top curves or meshes from a template run)",
        filter=0,
        preselect=True,
    )
    if not plate_guids:
        _log("assign_insertion_direction: cancelled — no plate objects selected.")
        return

    topo = PlateTopology()
    plate_map = topo.collect_plates_from_selection(plate_guids)
    if not plate_map:
        _log(
            "assign_insertion_direction: no tagged plate objects in selection. "
            "Run a template script first to generate tagged plates."
        )
        return
    _log(f"assign_insertion_direction: {len(plate_map)} plate(s) found.")

    # 2. Build edge-midpoint cache from the selected plates only
    plate_edges   = {}   # pid -> [(mid_pt: rg.Point3d, edge_idx: int), ...]
    plate_n_sides = {}   # pid -> int

    for pid, roles in plate_map.items():
        pts = _get_bot_polyline_points(roles.get("bot"))
        if pts is None or len(pts) < 3:
            continue

        if len(pts) >= 2 and pts[0].DistanceTo(pts[-1]) < 1e-6:
            n_edges = len(pts) - 1   # closed: last point duplicates first
        else:
            n_edges = len(pts)       # open: implicit closing edge

        midpoints = []
        for i in range(n_edges):
            j   = (i + 1) % len(pts)
            mid = rg.Point3d(
                (pts[i].X + pts[j].X) * 0.5,
                (pts[i].Y + pts[j].Y) * 0.5,
                (pts[i].Z + pts[j].Z) * 0.5,
            )
            midpoints.append((mid, i))

        plate_edges[pid]   = midpoints
        plate_n_sides[pid] = n_edges

    # 3. Select line objects
    line_guids = rs.GetObjects(
        "Select lines (start point near edge, direction = insertion vector)",
        filter=4,          # curves
        preselect=False,
    )
    if not line_guids:
        _log("assign_insertion_direction: cancelled — no lines selected.")
        return

    # 4. Parse lines → (start: rg.Point3d, unit_dir: tuple) pairs
    lines = []
    for guid in line_guids:
        obj = sc.doc.Objects.FindId(guid)
        if obj is None:
            continue
        crv = obj.Geometry
        if not crv.IsLinear():
            _log(f"  skipping non-linear curve — only straight lines are accepted.")
            continue
        start = crv.PointAtStart
        end   = crv.PointAtEnd
        dx    = end.X - start.X
        dy    = end.Y - start.Y
        dz    = end.Z - start.Z
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-10:
            _log(f"  skipping zero-length line.")
            continue
        lines.append((start, (dx / length, dy / length, dz / length)))

    if not lines:
        _log("assign_insertion_direction: no valid lines parsed.")
        return
    _log(f"assign_insertion_direction: {len(lines)} valid line(s) parsed.")

    # 5. Match each line's start point to the nearest selected-plate edge
    # updates[pid] = {face_slot: (dx, dy, dz)}
    updates = {}

    for start, unit_dir in lines:
        best_pid  = None
        best_edge = None
        best_dist = _MAX_SNAP_RADIUS + 1.0

        for pid, midpoints in plate_edges.items():
            for mid, edge_idx in midpoints:
                d = start.DistanceTo(mid)
                if d < best_dist:
                    best_dist = d
                    best_pid  = pid
                    best_edge = edge_idx

        if best_pid is None or best_dist > _MAX_SNAP_RADIUS:
            _log(
                f"  line start ({start.X:.1f},{start.Y:.1f},{start.Z:.1f}): "
                f"no edge within {_MAX_SNAP_RADIUS}mm — skipped."
            )
            continue

        face_slot = best_edge + 2   # edge 0 → face 2, edge 1 → face 3, …
        if best_pid not in updates:
            updates[best_pid] = {}
        updates[best_pid][face_slot] = unit_dir
        _log(
            f"  line → plate {best_pid}, edge {best_edge} "
            f"(face slot {face_slot}), dist={best_dist:.1f}mm, "
            f"dir=({unit_dir[0]:.3f},{unit_dir[1]:.3f},{unit_dir[2]:.3f})."
        )

    if not updates:
        _log("assign_insertion_direction: no lines matched any plate edge.")
        return

    # 6. Write updated insertion_vector for each affected plate
    n_updated = 0
    for pid, slot_map in updates.items():
        _, existing_iv = topo.get_plate_joinery(pid)
        n_sides = plate_n_sides.get(pid, 4)
        n_faces = n_sides + 2

        if existing_iv and len(existing_iv) == n_faces * 3:
            iv = list(existing_iv)
        else:
            iv = [0.0] * (n_faces * 3)

        for face_slot, (dx, dy, dz) in slot_map.items():
            if face_slot < n_faces:
                iv[face_slot * 3]     = dx
                iv[face_slot * 3 + 1] = dy
                iv[face_slot * 3 + 2] = dz
            else:
                _log(
                    f"  plate {pid}: face_slot {face_slot} >= n_faces {n_faces} "
                    f"— ignored (plate geometry may have changed)."
                )

        iv_str = json.dumps([float(v) for v in iv])
        _write_plate_userstring(pid, "insertion_vector", iv_str)
        _log(f"  plate {pid}: insertion_vector updated for {len(slot_map)} face slot(s).")
        n_updated += 1

    sc.doc.Views.Redraw()
    _log(f"assign_insertion_direction: {n_updated} plate(s) updated.")


run()
