#! python3
# venv: wood_env
# r: wood-nano
from typing import Any, Optional

import json

import Rhino
from wood_nano.plate_topology import PlateTopology
from wood_nano.assign_vectors import assign_insertion_vectors
from session_rhino.rhino_ui import write_plate_userstring, get_polyline_points


_DEFAULT_SNAP_RADIUS: float = 0.1


def run() -> None:
    # =========================================================================
    # RHINO UI — collect snap radius, select plate objects and lines
    # =========================================================================
    gn = Rhino.Input.Custom.GetNumber()
    gn.SetCommandPrompt("Snap tolerance (model units) — line endpoint must be within this distance of an edge")
    gn.SetDefaultNumber(_DEFAULT_SNAP_RADIUS)
    gn.SetLowerLimit(1e-6, False)
    if gn.Get() != Rhino.Input.GetResult.Number:
        Rhino.RhinoApp.WriteLine("assign_insertion_direction: cancelled.")
        return
    snap_radius: float = gn.Number()

    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select plate objects (bot/top curves or meshes from a template run)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.AnyObject
    go.EnablePreSelect(True, True)
    go.GetMultiple(1, 0)
    plate_guids: Optional[list] = [go.Object(i).ObjectId for i in range(go.ObjectCount)] if go.CommandResult() == Rhino.Commands.Result.Success else None
    if not plate_guids:
        Rhino.RhinoApp.WriteLine("assign_insertion_direction: cancelled — no plate objects selected.")
        return

    topo = PlateTopology()
    plate_map: dict[int, dict[str, Any]] = topo.collect_plates_from_selection(plate_guids)
    if not plate_map:
        Rhino.RhinoApp.WriteLine("assign_insertion_direction: no tagged plate objects in selection.")
        return
    Rhino.RhinoApp.WriteLine(f"assign_insertion_direction: {len(plate_map)} plate(s) found.")

    plate_ids: list[int] = sorted(plate_map.keys())
    bot_polylines: list[list[list[float]]] = []
    for pid in plate_ids:
        pts = get_polyline_points(plate_map[pid].get("bot"))
        bot_polylines.append([[p.X, p.Y, p.Z] for p in pts] if pts else [])

    go2 = Rhino.Input.Custom.GetObject()
    go2.SetCommandPrompt("Select lines (start point near edge, direction = insertion vector)")
    go2.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
    go2.EnablePreSelect(False, True)
    go2.GetMultiple(1, 0)
    line_guids: Optional[list] = [go2.Object(i).ObjectId for i in range(go2.ObjectCount)] if go2.CommandResult() == Rhino.Commands.Result.Success else None
    if not line_guids:
        Rhino.RhinoApp.WriteLine("assign_insertion_direction: cancelled — no lines selected.")
        return

    starts: list[list[float]] = []
    ends: list[list[float]]   = []
    for guid in line_guids:
        obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
        if obj is None:
            continue
        crv = obj.Geometry
        if not crv.IsLinear():
            Rhino.RhinoApp.WriteLine("  skipping non-linear curve.")
            continue
        s, e = crv.PointAtStart, crv.PointAtEnd
        if s.DistanceTo(e) < 1e-10:
            Rhino.RhinoApp.WriteLine("  skipping zero-length line.")
            continue
        starts.append([s.X, s.Y, s.Z])
        ends.append([e.X, e.Y, e.Z])

    if not starts:
        Rhino.RhinoApp.WriteLine("assign_insertion_direction: no valid lines parsed.")
        return
    Rhino.RhinoApp.WriteLine(f"assign_insertion_direction: {len(starts)} valid line(s) parsed.")

    # =========================================================================
    # WOOD-NANO — match lines to plate edges; compute insertion vectors
    # =========================================================================
    iv_assignments: list[tuple[int, int, float, float, float]] = assign_insertion_vectors(
        bot_polylines, starts, ends, snap_radius
    )

    # =========================================================================
    # RHINO UI — write insertion vectors back to plate UserStrings
    # =========================================================================
    if not iv_assignments:
        Rhino.RhinoApp.WriteLine("assign_insertion_direction: no lines matched any plate edge.")
        return

    updates: dict[int, dict[int, tuple[float, float, float]]] = {}
    for plate_idx, face_slot, ix, iy, iz in iv_assignments:
        updates.setdefault(plate_idx, {})[face_slot] = (ix, iy, iz)

    n_updated: int = 0
    for plate_idx, slot_map in updates.items():
        pid: int = plate_ids[plate_idx]
        _, existing_iv = topo.get_plate_joinery(pid)

        pts = get_polyline_points(plate_map[pid].get("bot"))
        if pts and len(pts) >= 2:
            n_edges: int = len(pts) - 1 if pts[0].DistanceTo(pts[-1]) < 1e-6 else len(pts)
        else:
            n_edges = max((s - 2 for s in slot_map), default=3) + 1
        n_floats: int = (n_edges + 2) * 3

        iv: list[float] = list(existing_iv) if existing_iv and len(existing_iv) == n_floats else [0.0] * n_floats
        for face_slot, (dx, dy, dz) in slot_map.items():
            iv[face_slot * 3]     = dx
            iv[face_slot * 3 + 1] = dy
            iv[face_slot * 3 + 2] = dz

        write_plate_userstring(plate_map, pid, "insertion_vector",
                               json.dumps([float(x) for x in iv]))
        Rhino.RhinoApp.WriteLine(f"  plate {pid}: insertion_vector updated ({len(slot_map)} slot(s)).")
        n_updated += 1

    Rhino.RhinoDoc.ActiveDoc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(f"assign_insertion_direction: {n_updated} plate(s) updated.")


run()
