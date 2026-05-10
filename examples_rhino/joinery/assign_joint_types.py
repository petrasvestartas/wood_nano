#! python3
"""Assign joint types to plate edges using Rhino TextDot objects.

Workflow
--------
1. Place TextDot objects in the Rhino viewport near the midpoints of plate edges.
   Each TextDot's text must be a joint type integer, e.g. ``15`` for
   SIDE-TO-SIDE OUT-OF-PLANE.  Common type codes:

     3   SIDE-TO-SIDE IN-PLANE       (family 0, types 1-9)
    15   SIDE-TO-SIDE OUT-OF-PLANE   (family 1, types 10-19)
    20   TOP-TO-SIDE                 (family 2, types 20-29)
    30   CROSS-JOINT IN-PLANE        (family 3, types 30-39)
    40   TOP-TO-TOP                  (family 4, types 40-49)
    58   SIDE-TO-SIDE ROTATED        (family 5, types 50-59)
    60   BOUNDARY                    (family 6, types 60-69)

2. Run this script and select the TextDot objects.
3. Each dot is matched to the nearest plate edge midpoint within
   ``_MAX_SNAP_RADIUS`` mm.  The corresponding face slot in the plate's
   ``joint_types`` UserString is updated (face 0 = bottom cap, face 1 = top cap,
   faces 2..N+1 = side edges in polyline order).
4. Existing ``insertion_vector`` UserStrings are preserved unchanged.
5. Run ``joinery_solver.py`` to apply the assigned types in the C++ solver.

Notes
-----
- When two dots fall on the same edge, the last one processed wins.
- TextDots whose text is not a valid integer are skipped with a warning.
- Dots farther than ``_MAX_SNAP_RADIUS`` from any edge midpoint are skipped.
"""

import json

import Rhino
import Rhino.DocObjects
import Rhino.Geometry as rg
import scriptcontext as sc
import rhinoscriptsyntax as rs
from wood_nano.plate_topology import PlateTopology


_log = Rhino.RhinoApp.WriteLine
_MAX_SNAP_RADIUS = 500.0   # mm — dots farther than this are skipped


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
    return list(rh_pl)   # Rhino.Geometry.Polyline iterates as Point3d


def run():
    # 1. Select TextDot objects (filter 8192)
    guids = rs.GetObjects(
        "Select TextDot objects (text = joint type integer)",
        filter=8192,
        preselect=True,
    )
    if not guids:
        _log("assign_joint_types: cancelled — no TextDots selected.")
        return

    # 2. Parse TextDots → (jt_code, position) pairs
    dots = []
    for guid in guids:
        obj = sc.doc.Objects.FindId(guid)
        if obj is None:
            continue
        geom = obj.Geometry
        if not isinstance(geom, rg.TextDot):
            _log(f"  skipping non-TextDot object.")
            continue
        text = geom.Text.strip()
        try:
            jt_code = int(text)
        except ValueError:
            _log(f"  TextDot text '{text}' is not an integer — skipped.")
            continue
        pos = geom.Point   # rg.Point3d
        dots.append((jt_code, pos))

    if not dots:
        _log("assign_joint_types: no valid TextDots parsed.")
        return
    _log(f"assign_joint_types: {len(dots)} valid dot(s) parsed.")

    # 3. Build edge-midpoint cache from all plates in the document
    topo = PlateTopology()
    all_pids = topo.all_plate_ids()

    plate_edges  = {}   # pid -> [(mid_pt: rg.Point3d, edge_idx: int), ...]
    plate_n_sides = {}  # pid -> int

    for pid in all_pids:
        roles    = topo.find_plate_objects(pid)
        bot_guid = roles.get("bot")
        pts      = _get_bot_polyline_points(bot_guid)
        if pts is None or len(pts) < 3:
            continue

        # Determine number of edges from the retrieved polyline.
        # Rhino may return open or closed; either way the edge count = len(pts) - 1
        # when closed (first == last) or len(pts) when open.
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

    if not plate_edges:
        _log("assign_joint_types: no plate geometry found in the document.")
        return

    # 4. Match each dot to the nearest edge; accumulate updates per plate
    # updates[pid] = {face_slot: jt_code}
    updates = {}

    for jt_code, pos in dots:
        best_pid  = None
        best_edge = None
        best_dist = _MAX_SNAP_RADIUS + 1.0

        for pid, midpoints in plate_edges.items():
            for mid, edge_idx in midpoints:
                d = pos.DistanceTo(mid)
                if d < best_dist:
                    best_dist = d
                    best_pid  = pid
                    best_edge = edge_idx

        if best_pid is None or best_dist > _MAX_SNAP_RADIUS:
            _log(
                f"  dot jt={jt_code} at "
                f"({pos.X:.1f},{pos.Y:.1f},{pos.Z:.1f}): "
                f"no edge within {_MAX_SNAP_RADIUS}mm — skipped."
            )
            continue

        face_slot = best_edge + 2   # edge 0 → face 2, edge 1 → face 3, …
        if best_pid not in updates:
            updates[best_pid] = {}
        updates[best_pid][face_slot] = jt_code
        _log(
            f"  dot jt={jt_code} → plate {best_pid}, "
            f"edge {best_edge} (face slot {face_slot}), "
            f"dist={best_dist:.1f}mm."
        )

    if not updates:
        _log("assign_joint_types: no dots matched any plate edge.")
        return

    # 5. Write updated joint_types for each affected plate
    n_updated = 0
    for pid, slot_map in updates.items():
        existing_jt, _ = topo.get_plate_joinery(pid)
        n_sides = plate_n_sides.get(pid, 4)
        n_faces = n_sides + 2

        if existing_jt and len(existing_jt) == n_faces:
            jt = list(existing_jt)
        else:
            jt = [0] * n_faces   # initialise / reinitialise on length mismatch

        for face_slot, jt_code in slot_map.items():
            if face_slot < n_faces:
                jt[face_slot] = jt_code
            else:
                _log(
                    f"  plate {pid}: face_slot {face_slot} >= n_faces {n_faces} "
                    f"— ignored (plate geometry may have changed)."
                )

        jt_str = json.dumps([int(x) for x in jt])
        _write_plate_userstring(pid, "joint_types", jt_str)
        _log(f"  plate {pid}: joint_types = {jt}.")
        n_updated += 1

    sc.doc.Views.Redraw()
    _log(f"assign_joint_types: {n_updated} plate(s) updated.")


run()
