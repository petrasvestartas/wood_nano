#! python3
# venv: wood_env
# r: wood-nano
from typing import Any, Optional

import System
import Rhino
import rhinoscriptsyntax as rs
from wood_nano.plate_topology import PlateTopology
from wood_nano.joinery_solver import (
    joinery_solver_elements,
    SEARCH_CROSS_JOINT,
    SEARCH_FACE_TO_FACE,
    SEARCH_BOTH,
)
from session_rhino.rhino_forms import NamedValuesForm
from session_rhino.rhino_ui import (
    loft_mesh_to_rhino,
    ensure_layer,
    guid_to_session_polyline,
    pl_coords_to_pt3d,
)


# =============================================================================
# RHINO UI HELPERS — joint parameter form, layer/object management
# =============================================================================

# mirrors wood_globals.cpp reset_defaults
_JPT_DEFAULTS: list[float] = [
    300, 0.5,  3,    # 0  ss_e_ip  — SIDE-TO-SIDE IN-PLANE       (types 1-9)
    450, 0.64, 15,   # 1  ss_e_op  — SIDE-TO-SIDE OUT-OF-PLANE   (types 10-19)
    450, 0.5,  20,   # 2  ts_e_p   — TOP-TO-SIDE                 (types 20-29)
    300, 0.5,  30,   # 3  cr_c_ip  — CROSS-JOINT IN-PLANE        (types 30-39)
      6, 0.95, 40,   # 4  tt_e_p   — TOP-TO-TOP                  (types 40-49)
    300, 0.5,  58,   # 5  ss_e_r   — SIDE-TO-SIDE ROTATED        (types 50-59)
    300, 1.0,  60,   # 6  b        — BOUNDARY                    (types 60-69)
]

_FAMILY_LABELS: list[str] = [
    "SIDE-TO-SIDE IN-PLANE (1-9)",
    "SIDE-TO-SIDE OUT-OF-PLANE (10-19)",
    "TOP-TO-SIDE (20-29)",
    "CROSS-JOINT IN-PLANE (30-39)",
    "TOP-TO-TOP (40-49)",
    "SIDE-TO-SIDE ROTATED (50-59)",
    "BOUNDARY (60-69)",
]

_joint_params: list[float]     = []   # empty = use C++ reset_defaults values
_joint_volume_ext: list[float] = []   # empty = use C++ default {0,0,0}

_JVE_DEFAULTS: list[float] = [0.0, 0.0, 0.0]


def _show_params_form() -> Optional[list[float]]:
    current: list[float] = _joint_params if len(_joint_params) == 21 else _JPT_DEFAULTS
    jve: list[float]     = _joint_volume_ext if len(_joint_volume_ext) == 3 else _JVE_DEFAULTS
    names: list[str]  = []
    values: list[Any] = []
    for fi, label in enumerate(_FAMILY_LABELS):
        names  += [label,              "  division_length", "  shift (0-1)", "  type_id"]
        values += ["-",                current[fi*3],       current[fi*3+1], current[fi*3+2]]
    names  += ["JOINT VOLUME EXTENSION", "  width",  "  height", "  length"]
    values += ["-",                       jve[0],     jve[1],     jve[2]]
    form = NamedValuesForm(names, values, title="Joint Parameters", width=420, height=660)
    if not form.show():
        return None
    result: list[float] = []
    for fi in range(7):
        base: int = fi * 4 + 1   # skip the section header row
        try:
            result += [
                float(form.attributes[base][1]),
                float(form.attributes[base + 1][1]),
                float(form.attributes[base + 2][1]),
            ]
        except (ValueError, IndexError, TypeError):
            Rhino.RhinoApp.WriteLine("Joint parameters: invalid value — keeping previous settings.")
            return None
    if len(result) != 21:
        return None
    jve_base: int = 7 * 4  # base row = 7 families × 4 rows each
    try:
        new_jve: list[float] = [
            float(form.attributes[jve_base + 1][1]),
            float(form.attributes[jve_base + 2][1]),
            float(form.attributes[jve_base + 3][1]),
        ]
        _joint_volume_ext[:] = new_jve
    except (ValueError, IndexError, TypeError):
        Rhino.RhinoApp.WriteLine("Joint volume extension: invalid value — keeping previous settings.")
    return result


DRAW_MESHES: bool = True

_draw_meshes: bool = False


_LAYER_DEFS: list[tuple] = [
    ("JoinerySolver",                  None,              (100, 100, 100), True),
    ("JoinerySolver::PlatesMesh",      "JoinerySolver",   ( 0,  0,  0), True),
    ("JoinerySolver::CutOutlines",     "JoinerySolver",   (  0, 120, 220), True),
    ("JoinerySolver::JointArea",       "JoinerySolver",   (  0, 200,   0), False),
    ("JoinerySolver::JointVolumes",    "JoinerySolver",   (220,  50,  50), False),
    ("JoinerySolver::JointLines",      "JoinerySolver",   (255, 200,   0), False),
]

_joinery_guids: list[System.Guid]  = []
_joinery_group_indices: list[int]  = []


def _clear_joinery() -> None:
    for g in _joinery_guids:
        Rhino.RhinoDoc.ActiveDoc.Objects.Delete(g, True)
    _joinery_guids[:] = []
    for gi in _joinery_group_indices:
        Rhino.RhinoDoc.ActiveDoc.Groups.Delete(gi)
    _joinery_group_indices[:] = []


def _add(rhino_geometry: Any, layer_idx: int) -> System.Guid:
    attr = Rhino.DocObjects.ObjectAttributes()
    attr.LayerIndex = layer_idx
    if isinstance(rhino_geometry, Rhino.Geometry.Mesh):
        g = Rhino.RhinoDoc.ActiveDoc.Objects.AddMesh(rhino_geometry, attr)
    elif isinstance(rhino_geometry, Rhino.Geometry.Polyline):
        g = Rhino.RhinoDoc.ActiveDoc.Objects.AddPolyline(rhino_geometry, attr)
    else:
        return System.Guid.Empty
    if g != System.Guid.Empty:
        _joinery_guids.append(g)
    return g


def _make_group(name: str, guids: list[System.Guid]) -> None:
    valid: list[System.Guid] = [g for g in guids if g != System.Guid.Empty]
    if len(valid) < 2:
        return
    gi: int = Rhino.RhinoDoc.ActiveDoc.Groups.Add(name, valid)
    if gi >= 0:
        _joinery_group_indices.append(gi)


def run() -> None:
    # =========================================================================
    # RHINO UI — select plate objects and extract polylines from document
    # =========================================================================
    guids: Optional[list[System.Guid]] = rs.GetObjects(
        "Select plate objects (bot/top curves or meshes from a template run)",
        filter=0,
        preselect=True,
    )
    if not guids:
        Rhino.RhinoApp.WriteLine("Joinery solver: cancelled — no objects selected.")
        return

    topo = PlateTopology()
    plate_map: dict[int, dict[str, Any]] = topo.collect_plates_from_selection(guids)

    if not plate_map:
        Rhino.RhinoApp.WriteLine(
            "Joinery solver: no tagged plate objects in selection. "
            "Run a template script first to generate tagged plates."
        )
        return

    Rhino.RhinoApp.WriteLine(f"Joinery solver: {len(plate_map)} plates found in selection.")

    bottom_pls: list      = []
    top_pls: list         = []
    bottom_hole_pls: list = []
    top_hole_pls: list    = []
    accepted_pids: list[int] = []   # PIDs that pass all filters — used to sync metadata

    for pid in sorted(plate_map.keys()):
        roles  = plate_map[pid]
        bot_pl = guid_to_session_polyline(roles.get("bot"))
        top_pl = guid_to_session_polyline(roles.get("top"))

        if bot_pl is None or top_pl is None:
            missing: str = "bot" if bot_pl is None else "top"
            Rhino.RhinoApp.WriteLine(f"  plate {pid}: missing {missing} curve — skipped.")
            continue

        bottom_pls.append(bot_pl)
        top_pls.append(top_pl)
        accepted_pids.append(pid)

        h_bots_guids, h_tops_guids = topo.find_plate_holes(pid)
        hole_bots = [guid_to_session_polyline(g) for g in h_bots_guids]
        hole_tops = [guid_to_session_polyline(g) for g in h_tops_guids]
        valid_holes_b = [h for h in hole_bots if h is not None]
        valid_holes_t = [h for h in hole_tops if h is not None]
        if valid_holes_b:
            Rhino.RhinoApp.WriteLine(f"  plate {pid}: {len(valid_holes_b)} hole(s) found.")
        bottom_hole_pls.append(valid_holes_b)
        top_hole_pls.append(valid_holes_t)

    if not bottom_pls:
        Rhino.RhinoApp.WriteLine("Joinery solver: no complete plate pairs found.")
        return

    Rhino.RhinoApp.WriteLine(f"Joinery solver: {len(bottom_pls)} complete plate pairs ready.")

    # =========================================================================
    # RHINO UI — read joinery metadata stored on plate objects by earlier commands
    # =========================================================================
    # C++ constraint: per_element_insertion_vectors uses std::array<double,18>
    # and per_element_joint_types uses std::array<int,6> — every non-empty
    # inner sequence MUST be exactly 18 / 6 elements long.
    per_element_iv: list = []
    per_element_jt: list = []
    for pid in accepted_pids:
        bot_guid = plate_map[pid].get("bot")
        jt, iv = topo.get_plate_joinery(pid, bot_guid=bot_guid)
        per_element_jt.append(jt)
        per_element_iv.append(iv)

    three_valence_data, adjacency_data = topo.get_chevron_global_joinery()

    # Remap stored plate_ids → accepted indices (skipped plates shift indices).
    pid_to_idx: dict[int, int] = {pid: idx for idx, pid in enumerate(accepted_pids)}
    if adjacency_data:
        adjacency_data = [
            [pid_to_idx[a], pid_to_idx[b]]
            for a, b in adjacency_data
            if a in pid_to_idx and b in pid_to_idx
        ]
    if three_valence_data:
        three_valence_data = [
            [pid_to_idx[x] for x in tv]
            for tv in three_valence_data
            if all(x in pid_to_idx for x in tv)
        ]

    has_explicit_jt: bool = False
    for jt_row in per_element_jt:
        if jt_row and any(x >= 0 for x in jt_row):
            has_explicit_jt = True
            break

    has_nonzero_iv: bool = False
    for iv_row in per_element_iv:
        if iv_row and any(abs(x) > 1e-6 for x in iv_row):
            has_nonzero_iv = True
            break

    has_explicit_data: bool = (has_explicit_jt
                               or has_nonzero_iv
                               or bool(three_valence_data)
                               or bool(adjacency_data))
    if has_explicit_data:
        n_jt: int = sum(1 for jt_row in per_element_jt if jt_row and any(x >= 0 for x in jt_row))
        n_iv: int = sum(1 for iv_row in per_element_iv if iv_row and any(abs(x) > 1e-6 for x in iv_row))
        Rhino.RhinoApp.WriteLine(
            f"  explicit joinery data: {n_jt} joint-type sets, "
            f"{n_iv} insertion vectors, "
            f"{len(three_valence_data)} three_valence groups, "
            f"{len(adjacency_data)} adjacency pairs."
        )
        for i in range(len(per_element_iv)):
            iv_i = per_element_iv[i]
            if not iv_i or len(iv_i) % 3 != 0:
                per_element_iv[i] = []
        # Pass jt=None when only iv is set — all-zero joints_types.txt blocks joint creation.
        if has_explicit_jt:
            for i in range(len(per_element_jt)):
                jt_i = per_element_jt[i]
                if jt_i and any(x >= 0 for x in jt_i):
                    per_element_jt[i] = [max(0, x) for x in jt_i]
                else:
                    per_element_jt[i] = []
        else:
            per_element_jt = []

    # =========================================================================
    # RHINO UI — interactive search-type and parameter selection loop
    # =========================================================================
    global _draw_meshes
    _SEARCH_OPTIONS: list[str] = ["face_to_face", "cross_joint", "both"]
    choice: Optional[str]
    while True:
        mesh_toggle: str    = "meshes_on" if _draw_meshes else "meshes_off"
        choice = rs.GetString(
            "Search type",
            defaultString="face_to_face",
            strings=_SEARCH_OPTIONS + ["parameters", mesh_toggle],
        )
        if choice is None:
            Rhino.RhinoApp.WriteLine("Joinery solver: cancelled.")
            return
        if choice.lower() == "parameters":
            new_params: Optional[list[float]] = _show_params_form()
            if new_params:
                _joint_params[:] = new_params
                Rhino.RhinoApp.WriteLine("Joint parameters updated.")
            continue   # loop back to search type prompt
        if choice.lower() in ("meshes_on", "meshes_off"):
            _draw_meshes = not _draw_meshes
            Rhino.RhinoApp.WriteLine(f"Joinery solver: draw meshes {'enabled' if _draw_meshes else 'disabled'}.")
            continue   # loop back to search type prompt
        break

    choice = choice.lower()
    if choice not in _SEARCH_OPTIONS:
        choice = "face_to_face"
    search_type: int = _SEARCH_OPTIONS.index(choice)
    Rhino.RhinoApp.WriteLine(f"Joinery solver: running search_type={search_type} ({choice}) ...")

    # =========================================================================
    # WOOD-NANO — run joinery solver
    # =========================================================================
    import time as _time
    has_holes: bool = any(h for h in bottom_hole_pls)
    _t0: float = _time.time()
    try:
        elements, joints = joinery_solver_elements(
            bottom_pls, top_pls, search_type,
            joint_params=_joint_params if _joint_params else None,
            joint_volume_ext=_joint_volume_ext if _joint_volume_ext else None,
            per_element_insertion_vectors=per_element_iv        if (has_nonzero_iv or bool(adjacency_data) or bool(three_valence_data)) else None,
            per_element_joint_types      =per_element_jt or None if has_explicit_data else None,
            three_valence                =three_valence_data if has_explicit_data else None,
            adjacency                    =adjacency_data     if has_explicit_data else None,
            bottom_hole_polylines=bottom_hole_pls if has_holes else None,
            top_hole_polylines   =top_hole_pls    if has_holes else None,
        )
    except Exception as exc:
        import traceback as _tb
        Rhino.RhinoApp.WriteLine(f"[ERROR] Python exception: {type(exc).__name__}: {exc}")
        Rhino.RhinoApp.WriteLine(_tb.format_exc())
        return
    Rhino.RhinoApp.WriteLine(
        f"Joinery solver: {len(elements)} elements processed, "
        f"{len(joints)} joints detected. C++ took {_time.time()-_t0:.2f}s"
    )

    # =========================================================================
    # RHINO UI — create layers and add result geometry to document
    # =========================================================================
    _t1: float = _time.time()
    _clear_joinery()

    layers: dict[str, int] = {}
    for full, parent, rgb, visible in _LAYER_DEFS:
        layers[full] = ensure_layer(full, parent, rgb, visible)

    Rhino.RhinoDoc.ActiveDoc.Layers.SetCurrentLayerIndex(layers["JoinerySolver"], True)

    l_mesh: int    = layers["JoinerySolver::PlatesMesh"]
    l_outline: int = layers["JoinerySolver::CutOutlines"]
    l_area: int    = layers["JoinerySolver::JointArea"]
    l_volume: int  = layers["JoinerySolver::JointVolumes"]
    l_line: int    = layers["JoinerySolver::JointLines"]

    n_meshes: int   = 0
    n_outlines: int = 0
    for ei, el in enumerate(elements):
        elem_guids: list[System.Guid] = []

        if _draw_meshes:
            rh_mesh = loft_mesh_to_rhino(el.loft_mesh())
            if rh_mesh and rh_mesh.Vertices.Count > 0:
                elem_guids.append(_add(rh_mesh, l_mesh))
                n_meshes += 1

        for pl in el.top_outlines + el.bottom_outlines:
            pts = pl_coords_to_pt3d(pl)
            if len(pts) >= 2:
                pts.append(pts[0])
                elem_guids.append(_add(Rhino.Geometry.Polyline(pts), l_outline))
                n_outlines += 1

        _make_group(f"joinery_elem_{ei}", elem_guids)

    n_volumes: int = 0
    n_lines: int   = 0
    for ji, jt in enumerate(joints):
        joint_guids: list[System.Guid] = []

        pts = pl_coords_to_pt3d(jt.area)
        if len(pts) >= 2:
            pts.append(pts[0])
            joint_guids.append(_add(Rhino.Geometry.Polyline(pts), l_area))

        for vol in jt.volumes:
            pts = pl_coords_to_pt3d(vol)
            if len(pts) >= 2:
                pts.append(pts[0])
                joint_guids.append(_add(Rhino.Geometry.Polyline(pts), l_volume))
                n_volumes += 1

        for ln in jt.lines:
            pts = pl_coords_to_pt3d(ln)
            if len(pts) >= 2:
                joint_guids.append(_add(Rhino.Geometry.Polyline(pts), l_line))
                n_lines += 1

        _make_group(f"joinery_joint_{ji}", joint_guids)

    Rhino.RhinoDoc.ActiveDoc.Views.Redraw()

    Rhino.RhinoApp.WriteLine(
        f"Joinery solver done: {n_meshes} lofted plate meshes, "
        f"{n_outlines} cut outlines, "
        f"{len(joints)} joint areas, "
        f"{n_volumes} cut volumes, "
        f"{n_lines} joint lines. "
        f"Draw took {_time.time()-_t1:.2f}s"
    )


run()
