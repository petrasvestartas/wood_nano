#! python3
# venv: wood_env
# r: wood-nano
# Joint type codes: 3=ss_ip  15=ss_op  20=top-to-side  30=cr_ip  40=tt  58=ss_r  60=boundary
from typing import Any, Optional

import json

import Rhino
from wood_nano.plate_topology import PlateTopology
from wood_nano.assign_vectors import match_points_to_plate_edges
from session_rhino.rhino_ui import write_plate_userstring, get_polyline_points


_DEFAULT_SNAP_RADIUS: float = 0.1


def run() -> None:
    # =========================================================================
    # RHINO UI — collect snap radius, select plate objects and TextDots
    # =========================================================================
    gn = Rhino.Input.Custom.GetNumber()
    gn.SetCommandPrompt("Snap tolerance (model units) — TextDot must be within this distance of an edge")
    gn.SetDefaultNumber(_DEFAULT_SNAP_RADIUS)
    gn.SetLowerLimit(1e-6, False)
    if gn.Get() != Rhino.Input.GetResult.Number:
        Rhino.RhinoApp.WriteLine("assign_joint_types: cancelled.")
        return
    snap_radius: float = gn.Number()

    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select plate objects (bot/top curves or meshes from a template run)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.AnyObject
    go.EnablePreSelect(True, True)
    go.GetMultiple(1, 0)
    plate_guids: Optional[list] = [go.Object(i).ObjectId for i in range(go.ObjectCount)] if go.CommandResult() == Rhino.Commands.Result.Success else None
    if not plate_guids:
        Rhino.RhinoApp.WriteLine("assign_joint_types: cancelled — no plate objects selected.")
        return

    topo = PlateTopology()
    plate_map: dict[int, dict[str, Any]] = topo.collect_plates_from_selection(plate_guids)
    if not plate_map:
        Rhino.RhinoApp.WriteLine("assign_joint_types: no tagged plate objects in selection.")
        return
    Rhino.RhinoApp.WriteLine(f"assign_joint_types: {len(plate_map)} plate(s) found.")

    plate_ids: list[int]              = sorted(plate_map.keys())
    bot_polylines: list[list[list[float]]] = []
    plate_nedges: list[int]           = []
    for pid in plate_ids:
        pts = get_polyline_points(plate_map[pid].get("bot"))
        if pts and len(pts) >= 3:
            n_edges: int = len(pts) - 1 if pts[0].DistanceTo(pts[-1]) < 1e-6 else len(pts)
            bot_polylines.append([[p.X, p.Y, p.Z] for p in pts])
        else:
            n_edges = 4
            bot_polylines.append([])
        plate_nedges.append(n_edges)

    go2 = Rhino.Input.Custom.GetObject()
    go2.SetCommandPrompt("Select TextDot objects (text = joint type integer)")
    go2.GeometryFilter = Rhino.DocObjects.ObjectType.TextDot
    go2.EnablePreSelect(False, True)
    go2.GetMultiple(1, 0)
    dot_guids: Optional[list] = [go2.Object(i).ObjectId for i in range(go2.ObjectCount)] if go2.CommandResult() == Rhino.Commands.Result.Success else None
    if not dot_guids:
        Rhino.RhinoApp.WriteLine("assign_joint_types: cancelled — no TextDots selected.")
        return

    dots: list[tuple[int, list[float]]] = []
    for guid in dot_guids:
        obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
        if obj is None:
            continue
        geom = obj.Geometry
        if not isinstance(geom, Rhino.Geometry.TextDot):
            continue
        try:
            jt_code: int = int(geom.Text.strip())
        except ValueError:
            Rhino.RhinoApp.WriteLine(f"  TextDot text '{geom.Text.strip()}' is not an integer — skipped.")
            continue
        p = geom.Point
        dots.append((jt_code, [p.X, p.Y, p.Z]))

    if not dots:
        Rhino.RhinoApp.WriteLine("assign_joint_types: no valid TextDots parsed.")
        return
    Rhino.RhinoApp.WriteLine(f"assign_joint_types: {len(dots)} valid dot(s) parsed.")

    # =========================================================================
    # WOOD-NANO — match TextDot positions to plate edges
    # =========================================================================
    matches: list[tuple[int, int, int]] = match_points_to_plate_edges(
        bot_polylines, [d[1] for d in dots], snap_radius
    )

    # =========================================================================
    # RHINO UI — write joint type assignments back to plate UserStrings
    # =========================================================================
    if not matches:
        Rhino.RhinoApp.WriteLine("assign_joint_types: no dots matched any plate edge.")
        return

    updates: dict[int, dict[int, int]] = {}  # plate_idx → {face_slot: jt_code}  (last match wins per slot)
    for dot_idx, plate_idx, edge_idx in matches:
        updates.setdefault(plate_idx, {})[edge_idx + 2] = dots[dot_idx][0]

    n_updated: int = 0
    for plate_idx, slot_map in updates.items():
        pid: int    = plate_ids[plate_idx]
        n_faces: int = plate_nedges[plate_idx] + 2
        existing_jt, _ = topo.get_plate_joinery(pid)
        jt: list[int] = list(existing_jt) if existing_jt and len(existing_jt) == n_faces else [-1] * n_faces
        for face_slot, jt_code in slot_map.items():
            if face_slot < n_faces:
                jt[face_slot] = jt_code
        write_plate_userstring(plate_map, pid, "joint_types",
                               json.dumps([int(x) for x in jt]))
        Rhino.RhinoApp.WriteLine(f"  plate {pid}: joint_types = {jt}.")
        n_updated += 1

    Rhino.RhinoDoc.ActiveDoc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(f"assign_joint_types: {n_updated} plate(s) updated.")


run()
