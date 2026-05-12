#! python3
# venv: wood_env
# r: wood-nano
"""Assign joint types to plate edges using Rhino TextDot objects.

Workflow
--------
1. Run and select the plate objects (bot/top curves or meshes from a template run).
   Press Enter when done.
2. Place TextDot objects in the Rhino viewport near the midpoints of plate edges.
   Each TextDot's text must be a joint type integer, e.g. ``15`` for
   SIDE-TO-SIDE OUT-OF-PLANE.  Common type codes:

     3   SIDE-TO-SIDE IN-PLANE       (family 0, types 1-9)
    15   SIDE-TO-SIDE OUT-OF-PLANE   (family 1, types 10-19)
    20   TOP-TO-SIDE                 (family 2, types 20-29)
    30   CROSS-JOINT IN-PLANE        (family 3, types 30-39)
    40   TOP-TO-TOP                  (family 4, types 40-49)
    58   SIDE-TO-SIDE ROTATED        (family 5, types 50-59)
    60   BOUNDARY                    (family 6, types 60-69)

3. Select the TextDot objects.
4. Each dot's position is matched to ALL selected-plate edge midpoints within
   ``snap_radius`` mm.  Every matched plate/edge pair is updated — so a dot
   placed on a shared edge between two plates updates both.
5. Existing ``insertion_vector`` UserStrings are preserved unchanged.
6. Run ``w_solver_joinery_solver`` — the stored types feed the C++ solver when combined
   with insertion-vector data (chevron workflow or full manual assignment).

Sentinel value
--------------
Unassigned face slots are stored as ``-1``, meaning "use global defaults".
The joinery solver converts -1 → 0 before passing to C++ (0 = no explicit type).
Face layout: slot 0 = bottom cap, slot 1 = top cap, slots 2..N+1 = N side edges.

Notes
-----
- nanobind transfers joint type data in-memory directly to C++ (no temp files).
- C++ binding uses ``std::array<int,6>`` per element; joinery_solver.py pads/truncates
  to 6 ints before passing. All side edges (not just first 4) are addressable.
- When two dots fall on the same face slot of the same plate, the last one wins.
- TextDots whose text is not a valid integer are skipped with a warning.
"""

import json
import math

import Rhino
import Rhino.DocObjects
import Rhino.Geometry as rg
import scriptcontext as sc
import rhinoscriptsyntax as rs
from wood_nano.plate_topology import PlateTopology
from rhino_ui import write_plate_userstring


_log = Rhino.RhinoApp.WriteLine
_DEFAULT_SNAP_RADIUS = 0.1  # model units — default snap tolerance (user-editable at run time)
_N_FACES = 6                # C++ fixed array size


def _dist_point_to_segment(pt, a, b):
    """Return minimum distance from pt to segment a–b."""
    abx = b.X - a.X; aby = b.Y - a.Y; abz = b.Z - a.Z
    apx = pt.X - a.X; apy = pt.Y - a.Y; apz = pt.Z - a.Z
    ab2 = abx*abx + aby*aby + abz*abz
    if ab2 < 1e-20:
        return math.sqrt(apx*apx + apy*apy + apz*apz)
    t = max(0.0, min(1.0, (apx*abx + apy*aby + apz*abz) / ab2))
    dx = apx - t*abx; dy = apy - t*aby; dz = apz - t*abz
    return math.sqrt(dx*dx + dy*dy + dz*dz)


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
    # 0. Ask for snap tolerance
    snap_radius = rs.GetReal(
        "Snap tolerance (model units) — TextDot must be within this distance of an edge",
        number=_DEFAULT_SNAP_RADIUS,
        minimum=1e-6,
    )
    if snap_radius is None:
        _log("assign_joint_types: cancelled.")
        return

    # 1. Select plate objects
    plate_guids = rs.GetObjects(
        "Select plate objects (bot/top curves or meshes from a template run)",
        filter=0,
        preselect=True,
    )
    if not plate_guids:
        _log("assign_joint_types: cancelled — no plate objects selected.")
        return

    topo = PlateTopology()
    plate_map = topo.collect_plates_from_selection(plate_guids)
    if not plate_map:
        _log(
            "assign_joint_types: no tagged plate objects in selection. "
            "Run a template script first to generate tagged plates."
        )
        return
    _log(f"assign_joint_types: {len(plate_map)} plate(s) found.")

    # 2. Build edge-segment cache for the selected plates only.
    #    Matching uses closest point on segment so vertex-placed dots work too.
    plate_edges  = {}   # pid -> [(a: Point3d, b: Point3d, edge_idx: int), ...]
    plate_nedges = {}   # pid -> int  (number of side edges)

    for pid, roles in plate_map.items():
        pts = _get_bot_polyline_points(roles.get("bot"))
        if pts is None or len(pts) < 3:
            continue

        if len(pts) >= 2 and pts[0].DistanceTo(pts[-1]) < 1e-6:
            n_edges = len(pts) - 1
        else:
            n_edges = len(pts)

        segs = []
        for i in range(n_edges):
            j = (i + 1) % len(pts)
            segs.append((pts[i], pts[j], i))

        plate_edges[pid]  = segs
        plate_nedges[pid] = n_edges

    # 3. Select TextDot objects (filter 8192)
    dot_guids = rs.GetObjects(
        "Select TextDot objects (text = joint type integer)",
        filter=8192,
        preselect=False,
    )
    if not dot_guids:
        _log("assign_joint_types: cancelled — no TextDots selected.")
        return

    # 4. Parse TextDots → (jt_code, position) pairs
    dots = []
    for guid in dot_guids:
        obj = sc.doc.Objects.FindId(guid)
        if obj is None:
            continue
        geom = obj.Geometry
        if not isinstance(geom, rg.TextDot):
            _log("  skipping non-TextDot object.")
            continue
        text = geom.Text.strip()
        try:
            jt_code = int(text)
        except ValueError:
            _log(f"  TextDot text '{text}' is not an integer — skipped.")
            continue
        dots.append((jt_code, geom.Point))

    if not dots:
        _log("assign_joint_types: no valid TextDots parsed.")
        return
    _log(f"assign_joint_types: {len(dots)} valid dot(s) parsed.")

    # 5. Match each dot to ALL plate edges within snap radius.
    #    A dot on a shared edge updates every plate that borders it.
    # updates[pid] = {face_slot: jt_code}
    updates = {}

    for jt_code, pos in dots:
        matched = []
        for pid, segs in plate_edges.items():
            for a, b, edge_idx in segs:
                d = _dist_point_to_segment(pos, a, b)
                if d <= snap_radius:
                    matched.append((d, pid, edge_idx))

        if not matched:
            _log(
                f"  dot jt={jt_code} at "
                f"({pos.X:.1f},{pos.Y:.1f},{pos.Z:.1f}): "
                f"no edge within {snap_radius}mm — skipped."
            )
            continue

        for d, pid, edge_idx in matched:
            face_slot = edge_idx + 2
            if pid not in updates:
                updates[pid] = {}
            updates[pid][face_slot] = jt_code
            _log(
                f"  dot jt={jt_code} → plate {pid}, "
                f"edge {edge_idx} (face slot {face_slot}), "
                f"dist={d:.1f}mm."
            )

    if not updates:
        _log("assign_joint_types: no dots matched any plate edge.")
        return

    # 6. Write updated joint_types for each affected plate.
    #    Length = n_side_edges + 2 (bot cap + top cap + side faces).
    #    -1 = unset (use global defaults).
    n_updated = 0
    for pid, slot_map in updates.items():
        existing_jt, _ = topo.get_plate_joinery(pid)
        n_edges = plate_nedges.get(pid, 4)
        n_faces = n_edges + 2

        # Use existing valid data if length matches; otherwise initialise with -1.
        if existing_jt and len(existing_jt) == n_faces:
            jt = list(existing_jt)
        else:
            jt = [-1] * n_faces

        for face_slot, jt_code in slot_map.items():
            if face_slot < n_faces:
                jt[face_slot] = jt_code
            else:
                _log(f"  plate {pid}: face_slot {face_slot} >= n_faces {n_faces} — skipped.")

        jt_str = json.dumps([int(x) for x in jt])
        _write_plate_userstring(plate_map, pid, "joint_types", jt_str)
        _log(f"  plate {pid}: joint_types = {jt}.")
        n_updated += 1

    sc.doc.Views.Redraw()
    _log(f"assign_joint_types: {n_updated} plate(s) updated.")


run()
