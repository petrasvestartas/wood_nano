#! python3
"""Assign per-edge insertion directions to plates using Rhino line objects.

Workflow
--------
1. Run and select the plate objects (bot/top curves or meshes from a template run).
   Press Enter when done.
2. Draw a line **along the joint edge** (parallel to the edge, not perpendicular):
     - **Start or end point** — must be within the snap tolerance of the target
       edge (on either the bottom or top polyline of the plate).
     - **Line direction** — draw along the edge/joint the way you want the joint
       to run.  The script automatically rotates this 90° around the plate normal
       to produce the insertion vector (cross(plate_normal, line_dir)).  This
       means you never have to think in insertion-vector terms — just draw along
       the visible joint line.
3. Each line's endpoints are matched to ALL selected-plate edges within the snap
   tolerance.  A line on a shared edge updates both neighbouring plates.
4. Existing ``joint_types`` UserStrings are preserved unchanged.
5. Run ``joinery_solver.py`` — insertion vectors are used in the C++ solver when
   combined with joint-type data (chevron workflow or full manual assignment).

Sentinel value
--------------
Face slots not assigned by a line are stored as ``0.0`` (three zero components).
Face layout: slot 0 = bottom cap, slot 1 = top cap, slots 2-5 = 4 side edges.

Notes
-----
- C++ requires exactly 18 floats per plate (``std::array<double,18>``, quad-plate model).
- Only the first 4 side edges (face slots 2-5) are addressable in the current C++.
- When two lines hit the same face slot of the same plate, the last one wins.
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
_DEFAULT_SNAP_RADIUS = 0.1  # model units — default snap tolerance (user-editable at run time)


def _cross(a, b):
    return (a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])


def _normalize(v):
    L = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    return (v[0]/L, v[1]/L, v[2]/L) if L > 1e-12 else v


def _face_normal(pts):
    """Newell normal from a list of rg.Point3d (open or closed ring)."""
    n = len(pts)
    nx = ny = nz = 0.0
    for i in range(n):
        j = (i + 1) % n
        ax, ay, az = pts[i].X, pts[i].Y, pts[i].Z
        bx, by, bz = pts[j].X, pts[j].Y, pts[j].Z
        nx += (ay - by) * (az + bz)
        ny += (az - bz) * (ax + bx)
        nz += (ax - bx) * (ay + by)
    L = math.sqrt(nx*nx + ny*ny + nz*nz)
    return (nx/L, ny/L, nz/L) if L > 1e-12 else None


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


def _write_plate_userstring(plate_map, plate_id, key, value_str):
    """Write one UserString to bot/top objects of a plate.

    Operates only on the GUIDs collected during selection (plate_map) so that
    other copies of the same layout with identical plate_id values are not
    accidentally updated.
    """
    roles = plate_map.get(plate_id, {})
    for role in ("bot", "top"):
        guid = roles.get(role)
        if guid is None:
            continue
        obj = sc.doc.Objects.FindId(guid)
        if obj is None:
            continue
        obj.Attributes.SetUserString(key, value_str)
        obj.CommitChanges()


def _get_polyline_points(guid):
    """Return list[rg.Point3d] from a curve GUID, or None on failure."""
    if guid is None:
        return None
    obj = sc.doc.Objects.FindId(guid)
    if obj is None:
        return None
    ok, rh_pl = obj.Geometry.TryGetPolyline()
    if not ok or rh_pl is None:
        return None
    return list(rh_pl)


def run():
    # 0. Ask for snap tolerance
    snap_radius = rs.GetReal(
        f"Snap tolerance (model units) — line endpoint must be within this distance of an edge",
        number=_DEFAULT_SNAP_RADIUS,
        minimum=1e-6,
    )
    if snap_radius is None:
        _log("assign_insertion_direction: cancelled.")
        return

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

    # 2. Build edge-segment cache and face normals for the selected plates.
    #    Both bot and top polylines are included so a line endpoint placed on
    #    either face of a plate (top or bottom surface edge) is matched.
    #    Matching uses closest point on segment so vertex-snapped lines work too.
    plate_edges   = {}   # pid -> [(a: Point3d, b: Point3d, edge_idx: int), ...]
    plate_normals = {}   # pid -> (nx, ny, nz)  — from bot polyline

    for pid, roles in plate_map.items():
        segs = []
        for role in ("bot", "top"):
            pts = _get_polyline_points(roles.get(role))
            if pts is None or len(pts) < 3:
                continue
            if role == "bot":
                n = _face_normal(pts)
                if n:
                    plate_normals[pid] = n
            n_edges = len(pts) - 1 if pts[0].DistanceTo(pts[-1]) < 1e-6 else len(pts)
            for i in range(n_edges):
                j = (i + 1) % len(pts)
                segs.append((pts[i], pts[j], i))
        if segs:
            plate_edges[pid] = segs

    # 3. Select line objects
    line_guids = rs.GetObjects(
        "Select lines (start point near edge, direction = insertion vector)",
        filter=4,
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
            _log("  skipping non-linear curve — only straight lines are accepted.")
            continue
        start = crv.PointAtStart
        end   = crv.PointAtEnd
        dx, dy, dz = end.X - start.X, end.Y - start.Y, end.Z - start.Z
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-10:
            _log("  skipping zero-length line.")
            continue
        lines.append((start, end, (dx / length, dy / length, dz / length)))

    if not lines:
        _log("assign_insertion_direction: no valid lines parsed.")
        return
    _log(f"assign_insertion_direction: {len(lines)} valid line(s) parsed.")

    # 5. Match each line's endpoints (start AND end) to plate edges within snap
    #    radius.  Both endpoints are checked so a line straddling a shared edge
    #    (start near one plate's edge, end near the neighbour's edge) can assign
    #    both in one step.  With a tight tolerance (default 0.1 units) false
    #    matches are avoided — place endpoints precisely on or very close to the
    #    target edge.  A match near a shared edge updates every plate that borders it.
    # updates[pid] = {face_slot: (dx, dy, dz)}
    updates = {}

    for start, end, unit_dir in lines:
        matched = {}   # (pid, edge_idx) -> best dist
        for pid, segs in plate_edges.items():
            for a, b, edge_idx in segs:
                d = min(_dist_point_to_segment(start, a, b),
                        _dist_point_to_segment(end,   a, b))
                if d <= snap_radius:
                    key = (pid, edge_idx)
                    if key not in matched or d < matched[key]:
                        matched[key] = d

        if not matched:
            _log(
                f"  line ({start.X:.1f},{start.Y:.1f},{start.Z:.1f})"
                f"→({end.X:.1f},{end.Y:.1f},{end.Z:.1f}): "
                f"no edge within {snap_radius} units — skipped."
            )
            continue

        for (pid, edge_idx), d in matched.items():
            face_slot = edge_idx + 2
            # Rotate the drawn direction 90° around the plate normal so the
            # user can draw along the joint edge (intuitive) and the insertion
            # vector (perpendicular-in-plane) is computed automatically.
            normal = plate_normals.get(pid)
            if normal:
                iv_dir = _normalize(_cross(normal, unit_dir))
            else:
                iv_dir = unit_dir
            if pid not in updates:
                updates[pid] = {}
            updates[pid][face_slot] = iv_dir
            _log(
                f"  line → plate {pid}, edge {edge_idx} "
                f"(face slot {face_slot}), dist={d:.3f}, "
                f"insertion=({iv_dir[0]:.3f},{iv_dir[1]:.3f},{iv_dir[2]:.3f})."
            )

    if not updates:
        _log("assign_insertion_direction: no lines matched any plate edge.")
        return

    # 6. Write updated insertion_vector for each affected plate.
    #    Always exactly 18 floats (C++ std::array<double,18>).
    n_updated = 0
    for pid, slot_map in updates.items():
        _, existing_iv = topo.get_plate_joinery(pid)

        # Determine face count from the bot polyline of this plate.
        roles = plate_map.get(pid, {})
        bot_pts = _get_polyline_points(roles.get("bot"))
        if bot_pts and len(bot_pts) >= 2:
            n_edges_plate = len(bot_pts) - 1 if bot_pts[0].DistanceTo(bot_pts[-1]) < 1e-6 else len(bot_pts)
        else:
            n_edges_plate = max((s - 2 for s in slot_map), default=3) + 1
        n_faces_plate = n_edges_plate + 2
        n_floats = n_faces_plate * 3

        if existing_iv and len(existing_iv) == n_floats:
            iv = list(existing_iv)
        else:
            iv = [0.0] * n_floats

        for face_slot, (dx, dy, dz) in slot_map.items():
            iv[face_slot * 3]     = dx
            iv[face_slot * 3 + 1] = dy
            iv[face_slot * 3 + 2] = dz

        iv_str = json.dumps([float(v) for v in iv])
        _write_plate_userstring(plate_map, pid, "insertion_vector", iv_str)
        _log(f"  plate {pid}: insertion_vector updated for {len(slot_map)} face slot(s).")
        n_updated += 1

    sc.doc.Views.Redraw()
    _log(f"assign_insertion_direction: {n_updated} plate(s) updated.")


run()
