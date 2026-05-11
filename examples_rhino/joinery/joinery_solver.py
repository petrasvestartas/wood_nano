#! python3
"""Joinery solver — plate-topology-aware Rhino interface.

Workflow
--------
1. Run any plate-generator template (e.g. ``reciprocal_rotation.py``,
   ``diamond_mesh.py``, ``translation_shell.py``).  Each template calls
   ``topo.add_plate()`` which tags every plate object with UserStrings
   (``plate_id`` / ``plate_role`` = "bot" | "top" | "mesh") that survive
   save/open in the .3dm file.

2. Run this script.  It prompts you to select plate objects (any mix of
   bot/top curves or meshes from a template run).  Selecting just one object
   per plate is enough; the script expands the selection to full plate sets
   automatically via ``PlateTopology.collect_plates_from_selection``.

3. Choose a search type (or open the optional Parameters dialog first):
     face_to_face  — coplanar overlapping plates (translation_shell etc.)
     cross_joint   — scissor-crossing beams
     both          — try face_to_face first, then cross_joint
     parameters    — open Eto dialog to edit joint family parameters, then re-prompt

4. The C++ joinery pipeline runs and draws:
   - Lofted plate meshes (one per plate, with merged cut notches if any joints
     were found).
   - Merged cut outlines for top and bottom faces (empty when no joints are
     detected for an element).
   - Joint area polylines (shows where joints were detected).
"""

import ast
import System.Drawing
import Eto.Drawing
import Eto.Forms
import Rhino
import Rhino.Geometry as rg
import Rhino.DocObjects as rdo
import Rhino.UI
import scriptcontext as sc
import rhinoscriptsyntax as rs
from session_py.point import Point as PyPoint  # noqa: F401 (used by _guid_to_session_polyline)
from session_py.polyline import Polyline as PyPolyline
from wood_nano.plate_topology import PlateTopology
from wood_nano.joinery_solver import (
    joinery_solver_elements,
    SEARCH_CROSS_JOINT,
    SEARCH_FACE_TO_FACE,
    SEARCH_BOTH,
)


# ── Eto parameters dialog (adapted from wood_rui/forms.py) ───────────────────

class NamedValuesForm(Eto.Forms.Dialog[bool]):
    """Two-column Eto GridView dialog: read-only Name column, editable Value column."""

    def __init__(self, names, values, title="Named Values", width=420, height=560):
        super().__init__()
        self.attributes = list(zip(names, values))
        self.names  = names
        self.values = [str(v) for v in values]

        self.Title       = title
        self.Padding     = Eto.Drawing.Padding(0)
        self.Resizable   = True
        self.MinimumSize = Eto.Drawing.Size(width // 2, height // 2)
        self.ClientSize  = Eto.Drawing.Size(width, height)

        self.table = table = Eto.Forms.GridView()
        table.ShowHeader = True

        col_name = Eto.Forms.GridColumn()
        col_name.HeaderText = "Name"
        col_name.Editable   = False
        col_name.DataCell   = Eto.Forms.TextBoxCell(0)
        table.Columns.Add(col_name)

        col_val = Eto.Forms.GridColumn()
        col_val.HeaderText = "Value"
        col_val.Editable   = True
        col_val.DataCell   = Eto.Forms.TextBoxCell(1)
        table.Columns.Add(col_val)

        collection = []
        for name, value in zip(self.names, self.values):
            item = Eto.Forms.GridItem()
            item.Values = (name, value)
            collection.append(item)
        table.DataStore = collection

        layout = Eto.Forms.DynamicLayout()
        layout.BeginVertical(Eto.Drawing.Padding(0), Eto.Drawing.Size(0, 0), True, True)
        layout.AddRow(table)
        layout.EndVertical()
        layout.BeginVertical(Eto.Drawing.Padding(12, 18, 12, 24), Eto.Drawing.Size(6, 0), False, False)
        layout.AddRow(None, self._make_ok(), self._make_cancel())
        layout.EndVertical()
        self.Content = layout

    def _make_ok(self):
        self.DefaultButton = Eto.Forms.Button()
        self.DefaultButton.Text = "OK"
        self.DefaultButton.Click += self._on_ok
        return self.DefaultButton

    def _make_cancel(self):
        self.AbortButton = Eto.Forms.Button()
        self.AbortButton.Text = "Cancel"
        self.AbortButton.Click += self._on_cancel
        return self.AbortButton

    def _on_ok(self, sender, event):
        try:
            self.attributes = []
            for row in self.table.DataStore:
                name  = row.GetValue(0)
                value = row.GetValue(1)
                if value not in ("-", "", " "):
                    try:
                        value = ast.literal_eval(value)
                    except (ValueError, SyntaxError):
                        pass
                self.attributes.append((name, value))
        except Exception as exc:
            print(exc)
            self.Close(False)
            return
        self.Close(True)

    def _on_cancel(self, sender, event):
        self.Close(False)

    def show(self):
        return self.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)


# ── Joint family defaults (mirrors wood_globals.cpp reset_defaults) ──────────
_JPT_DEFAULTS = [
    300, 0.5,  3,    # 0  ss_e_ip  — SIDE-TO-SIDE IN-PLANE       (types 1-9)
    450, 0.64, 15,   # 1  ss_e_op  — SIDE-TO-SIDE OUT-OF-PLANE   (types 10-19)
    450, 0.5,  20,   # 2  ts_e_p   — TOP-TO-SIDE                 (types 20-29)
    300, 0.5,  30,   # 3  cr_c_ip  — CROSS-JOINT IN-PLANE        (types 30-39)
      6, 0.95, 40,   # 4  tt_e_p   — TOP-TO-TOP                  (types 40-49)
    300, 0.5,  58,   # 5  ss_e_r   — SIDE-TO-SIDE ROTATED        (types 50-59)
    300, 1.0,  60,   # 6  b        — BOUNDARY                    (types 60-69)
]

_FAMILY_LABELS = [
    "SIDE-TO-SIDE IN-PLANE (1-9)",
    "SIDE-TO-SIDE OUT-OF-PLANE (10-19)",
    "TOP-TO-SIDE (20-29)",
    "CROSS-JOINT IN-PLANE (30-39)",
    "TOP-TO-TOP (40-49)",
    "SIDE-TO-SIDE ROTATED (50-59)",
    "BOUNDARY (60-69)",
]

# Persists across script runs in this Rhino session (module-level mutable list).
_joint_params = []        # empty = use C++ reset_defaults values
_joint_volume_ext = []    # empty = use C++ default {0,0,0}

_JVE_DEFAULTS = [0.0, 0.0, 0.0]


def _show_params_form():
    """Open Eto parameters dialog.

    Updates module-level _joint_volume_ext as a side effect.
    Returns new 21-element joint_params list, or None on cancel.
    """
    current = _joint_params if len(_joint_params) == 21 else _JPT_DEFAULTS
    jve     = _joint_volume_ext if len(_joint_volume_ext) == 3 else _JVE_DEFAULTS
    names, values = [], []
    for fi, label in enumerate(_FAMILY_LABELS):
        names  += [label,              "  division_length", "  shift (0-1)", "  type_id"]
        values += ["-",                current[fi*3],       current[fi*3+1], current[fi*3+2]]
    # JOINT VOLUME EXTENSION section  (rows 28-31)
    names  += ["JOINT VOLUME EXTENSION", "  width",  "  height", "  length"]
    values += ["-",                       jve[0],     jve[1],     jve[2]]
    form = NamedValuesForm(names, values, title="Joint Parameters", width=420, height=660)
    if not form.show():
        return None
    result = []
    for fi in range(7):
        base = fi * 4 + 1   # skip the section header row
        try:
            result += [
                float(form.attributes[base][1]),
                float(form.attributes[base + 1][1]),
                float(form.attributes[base + 2][1]),
            ]
        except (ValueError, IndexError, TypeError):
            _log("Joint parameters: invalid value — keeping previous settings.")
            return None
    if len(result) != 21:
        return None
    # Parse JOINT VOLUME EXTENSION (base row = 7*4 = 28, values at +1, +2, +3)
    jve_base = 7 * 4
    try:
        new_jve = [
            float(form.attributes[jve_base + 1][1]),
            float(form.attributes[jve_base + 2][1]),
            float(form.attributes[jve_base + 3][1]),
        ]
        _joint_volume_ext[:] = new_jve
    except (ValueError, IndexError, TypeError):
        _log("Joint volume extension: invalid value — keeping previous settings.")
    return result

DRAW_MESHES = True

_draw_meshes = False   # session state, toggled by the "draw_meshes" option


def _loft_mesh_to_rhino(mesh):
    """Fast session_py Mesh → welded Rhino.Geometry.Mesh.

    Side faces: quads/tris added directly (welded, no ngons).
    Cap faces (CDT-triangulated): triangles added then wrapped in an ngon
    so Rhino hides the internal triangulation edges visually.
    """
    vkeys = sorted(mesh.vertex.keys())
    vkey_to_idx = {vk: i for i, vk in enumerate(vkeys)}
    rmesh = rg.Mesh()
    for vk in vkeys:
        v = mesh.vertex[vk]
        rmesh.Vertices.Add(v.x, v.y, v.z)
    tri = mesh.triangulation or {}
    holes = mesh.face_holes or {}
    for fk in sorted(mesh.face.keys()):
        stored = tri.get(fk)
        if stored:
            # CDT cap face: add triangles, then wrap in ngon to hide edges.
            hole_rings = holes.get(fk, [])
            all_vks = list(mesh.face[fk]) + [vk for ring in hole_rings for vk in ring]
            local = {vk: vkey_to_idx[vk] for vk in all_vks if vk in vkey_to_idx}
            fi_start = rmesh.Faces.Count
            for t in stored:
                a, b, c = local.get(t[0]), local.get(t[1]), local.get(t[2])
                if a is not None and b is not None and c is not None:
                    rmesh.Faces.AddFace(a, b, c)
            fi_end = rmesh.Faces.Count
            outer_idx = [vkey_to_idx[vk] for vk in mesh.face[fk] if vk in vkey_to_idx]
            if len(outer_idx) >= 3 and fi_end > fi_start:
                rmesh.Ngons.AddNgon(
                    rg.MeshNgon.Create(outer_idx, list(range(fi_start, fi_end)))
                )
        else:
            vks = mesh.face[fk]
            idx = [vkey_to_idx[vk] for vk in vks]
            if len(idx) == 3:
                rmesh.Faces.AddFace(idx[0], idx[1], idx[2])
            elif len(idx) == 4:
                rmesh.Faces.AddFace(idx[0], idx[1], idx[2], idx[3])
    rmesh.Normals.ComputeNormals()
    return rmesh

_log = Rhino.RhinoApp.WriteLine

# ── Layer definitions: (full_path, parent_path, RGB, visible) ────────────────
_LAYER_DEFS = [
    ("JoinerySolver",                  None,              (100, 100, 100), True),
    ("JoinerySolver::PlatesMesh",      "JoinerySolver",   ( 0,  0,  0), True),
    ("JoinerySolver::CutOutlines",     "JoinerySolver",   (  0, 120, 220), True),
    ("JoinerySolver::JointArea",       "JoinerySolver",   (  0, 200,   0), False),
    ("JoinerySolver::JointVolumes",    "JoinerySolver",   (220,  50,  50), False),
    ("JoinerySolver::JointLines",      "JoinerySolver",   (255, 200,   0), False),
]

def _ensure_layer(full_path, parent_path, rgb, visible):
    idx = sc.doc.Layers.FindByFullPath(full_path, Rhino.RhinoMath.UnsetIntIndex)
    if idx >= 0:
        return idx
    layer = rdo.Layer()
    layer.Name = full_path.split("::")[-1]
    layer.Color = System.Drawing.Color.FromArgb(*rgb)
    layer.IsVisible = visible
    if parent_path:
        pidx = sc.doc.Layers.FindByFullPath(parent_path, Rhino.RhinoMath.UnsetIntIndex)
        if pidx >= 0:
            layer.ParentLayerId = sc.doc.Layers[pidx].Id
    return sc.doc.Layers.Add(layer)

_joinery_guids        = []   # persists across script runs in this Rhino session
_joinery_group_indices = []  # group indices created by this script

def _clear_joinery():
    for g in _joinery_guids:
        sc.doc.Objects.Delete(g, True)
    _joinery_guids[:] = []
    for gi in _joinery_group_indices:
        sc.doc.Groups.Delete(gi)
    _joinery_group_indices[:] = []

def _add(rhino_geometry, layer_idx):
    """Add geometry to the document; returns the GUID or Guid.Empty."""
    attr = rdo.ObjectAttributes()
    attr.LayerIndex = layer_idx
    if isinstance(rhino_geometry, rg.Mesh):
        g = sc.doc.Objects.AddMesh(rhino_geometry, attr)
    elif isinstance(rhino_geometry, rg.Polyline):
        g = sc.doc.Objects.AddPolyline(rhino_geometry, attr)
    else:
        return System.Guid.Empty
    if g != System.Guid.Empty:
        _joinery_guids.append(g)
    return g

def _make_group(name, guids):
    """Create a named Rhino group from a list of GUIDs (skips empties)."""
    valid = [g for g in guids if g != System.Guid.Empty]
    if len(valid) < 2:
        return
    gi = sc.doc.Groups.Add(name, valid)
    if gi >= 0:
        _joinery_group_indices.append(gi)

def _pl_coords_to_pt3d(pl):
    """Convert session_py Polyline to list of Rhino Point3d, closing point stripped."""
    c = pl.coords
    pts = [rg.Point3d(c[i], c[i+1], c[i+2]) for i in range(0, len(c), 3)]
    if len(pts) >= 2:
        p0, pn = pts[0], pts[-1]
        if p0.DistanceTo(pn) < 1e-6:
            pts = pts[:-1]
    return pts


def _guid_to_session_polyline(guid):
    """Read a Rhino curve object by GUID and return a session_py Polyline.

    Rhino stores closed polylines as open PolylineCurves (consecutive duplicate
    points are stripped).  WoodElement needs a closed polyline (first == last)
    so that n_sides = len(pts) - 1 is correct.  Re-add the closing point here.
    """
    if guid is None:
        return None
    obj = sc.doc.Objects.FindId(guid)
    if obj is None:
        return None
    crv = obj.Geometry
    ok, rh_pl = crv.TryGetPolyline()
    if not ok or rh_pl is None:
        return None
    pts = [PyPoint(float(pt.X), float(pt.Y), float(pt.Z)) for pt in rh_pl]
    if len(pts) < 2:
        return None
    # Re-add closing point if the polyline was stored as closed but retrieved open.
    p0, pN = pts[0], pts[-1]
    if p0.x != pN.x or p0.y != pN.y or p0.z != pN.z:
        pts.append(PyPoint(p0.x, p0.y, p0.z))
    return PyPolyline(pts)


def run():
    # ── 1. Select objects ─────────────────────────────────────────────────
    guids = rs.GetObjects(
        "Select plate objects (bot/top curves or meshes from a template run)",
        filter=0,
        preselect=True,
    )
    if not guids:
        _log("Joinery solver: cancelled — no objects selected.")
        return

    # ── 2. Expand to full plate sets via UserString tags ──────────────────
    topo = PlateTopology()
    plate_map = topo.collect_plates_from_selection(guids)

    if not plate_map:
        _log(
            "Joinery solver: no tagged plate objects in selection. "
            "Run a template script first to generate tagged plates."
        )
        return

    _log(f"Joinery solver: {len(plate_map)} plates found in selection.")

    # ── 3. Reconstruct bottom/top polylines from the Rhino document ───────
    bottom_pls      = []
    top_pls         = []
    bottom_hole_pls = []
    top_hole_pls    = []
    accepted_pids   = []   # PIDs that pass all filters — used to sync metadata

    for pid in sorted(plate_map.keys()):
        roles  = plate_map[pid]
        bot_pl = _guid_to_session_polyline(roles.get("bot"))
        top_pl = _guid_to_session_polyline(roles.get("top"))

        if bot_pl is None or top_pl is None:
            missing = "bot" if bot_pl is None else "top"
            _log(f"  plate {pid}: missing {missing} curve — skipped.")
            continue

        bottom_pls.append(bot_pl)
        top_pls.append(top_pl)
        accepted_pids.append(pid)

        # Read hole polylines for this plate.
        h_bots_guids, h_tops_guids = topo.find_plate_holes(pid)
        hole_bots = [_guid_to_session_polyline(g) for g in h_bots_guids]
        hole_tops = [_guid_to_session_polyline(g) for g in h_tops_guids]
        valid_holes_b = [h for h in hole_bots if h is not None]
        valid_holes_t = [h for h in hole_tops if h is not None]
        if valid_holes_b:
            _log(f"  plate {pid}: {len(valid_holes_b)} hole(s) found.")
        bottom_hole_pls.append(valid_holes_b)
        top_hole_pls.append(valid_holes_t)

    if not bottom_pls:
        _log("Joinery solver: no complete plate pairs found.")
        return

    _log(f"Joinery solver: {len(bottom_pls)} complete plate pairs ready.")

    # ── 3b. Read explicit joinery metadata (joint_types, insertion_vectors,
    #        three_valence, adjacency) stored as UserStrings / doc strings.
    #        Written by the chevron template (auto) or by assign_insertion_direction /
    #        assign_joint_types (manual).  Absent for untagged templates → solver
    #        falls back to automatic BVH adjacency detection.
    #
    #        C++ constraint: per_element_insertion_vectors uses std::array<double,18>
    #        and per_element_joint_types uses std::array<int,6> — fixed-size arrays
    #        designed for 4-sided plates (4 sides + 2 caps = 6 faces, 6×3=18 floats).
    #        Every non-empty inner sequence MUST be exactly 18 / 6 elements long.
    per_element_iv = []
    per_element_jt = []
    for pid in accepted_pids:   # use accepted_pids — keeps metadata in sync with bottom/top_pls
        bot_guid = plate_map[pid].get("bot")
        jt, iv = topo.get_plate_joinery(pid, bot_guid=bot_guid)
        per_element_jt.append(jt)
        per_element_iv.append(iv)

    three_valence_data, adjacency_data = topo.get_chevron_global_joinery()

    # ── Remap adjacency/three_valence to the accepted plate indices ───────
    # adjacency and three_valence store original plate_id values (0..N-1 from
    # the chevron run).  The C++ solver receives element indices 0..M-1 that
    # correspond to accepted_pids.  If plates were skipped (missing curves or
    # too small), or if the doc strings are stale, raw indices would be out of
    # range → crash / memory explosion.
    pid_to_idx = {pid: idx for idx, pid in enumerate(accepted_pids)}
    if adjacency_data:
        adjacency_data = [
            [pid_to_idx[a], pid_to_idx[b]]
            for a, b in adjacency_data
            if a in pid_to_idx and b in pid_to_idx
        ]
    if three_valence_data:
        three_valence_data = [
            [pid_to_idx[v] for v in tv]
            for tv in three_valence_data
            if all(v in pid_to_idx for v in tv)
        ]

    # has_explicit_jt: at least one plate has a real joint-type assignment (value >= 0).
    has_explicit_jt = any(any(v >= 0 for v in jt) for jt in per_element_jt if jt)
    # has_nonzero_iv: at least one plate has a user-assigned insertion direction
    # (non-zero vector — distinguishes real assignment from stale zeros).
    has_nonzero_iv = any(iv and any(abs(v) > 1e-6 for v in iv) for iv in per_element_iv)
    has_explicit_data = (has_explicit_jt
                         or has_nonzero_iv
                         or bool(three_valence_data)
                         or bool(adjacency_data))
    if has_explicit_data:
        n_jt = sum(1 for jt in per_element_jt if jt and any(v >= 0 for v in jt))
        n_iv = sum(1 for iv in per_element_iv if iv and any(abs(v) > 1e-6 for v in iv))
        _log(
            f"  explicit joinery data: {n_jt} joint-type sets, "
            f"{n_iv} insertion vectors, "
            f"{len(three_valence_data)} three_valence groups, "
            f"{len(adjacency_data)} adjacency pairs."
        )
        # Ensure iv is a valid flat float list (multiple of 3).
        # Length encodes face count: n_faces = len/3. Empty = all auto.
        for i in range(len(per_element_iv)):
            iv_i = per_element_iv[i]
            if not iv_i or len(iv_i) % 3 != 0:
                per_element_iv[i] = []
        # Pad jt ONLY when there are actual jt assignments.
        # When iv is the only trigger (no TextDots), pass jt=None so the C++
        # receives empty joints_per_face → no joints_types.txt → auto type detection.
        # All-zero joints_types.txt would block all joint creation.
        if has_explicit_jt:
            for i in range(len(per_element_jt)):
                jt_i = per_element_jt[i]
                # Keep the full list for any plate with at least one real assignment.
                # Plates with no assignment (all -1 or empty) → [] so C++ uses auto detection.
                if jt_i and any(v >= 0 for v in jt_i):
                    per_element_jt[i] = [max(0, v) for v in jt_i]
                else:
                    per_element_jt[i] = []
        else:
            per_element_jt = []  # empty → C++ skips joints_types entirely

    # ── 4. Pick search type; optional [parameters] opens Eto dialog ──────
    global _draw_meshes
    _SEARCH_OPTIONS = ["face_to_face", "cross_joint", "both"]
    while True:
        mesh_toggle = "meshes_on" if _draw_meshes else "meshes_off"
        choice = rs.GetString(
            "Search type",
            defaultString="face_to_face",
            strings=_SEARCH_OPTIONS + ["parameters", mesh_toggle],
        )
        if choice is None:
            _log("Joinery solver: cancelled.")
            return
        if choice.lower() == "parameters":
            new_params = _show_params_form()
            if new_params:
                _joint_params[:] = new_params
                _log("Joint parameters updated.")
            continue   # loop back to search type prompt
        if choice.lower() in ("meshes_on", "meshes_off"):
            _draw_meshes = not _draw_meshes
            _log(f"Joinery solver: draw meshes {'enabled' if _draw_meshes else 'disabled'}.")
            continue   # loop back to search type prompt
        break

    choice = choice.lower()
    if choice not in _SEARCH_OPTIONS:
        choice = "face_to_face"
    search_type = _SEARCH_OPTIONS.index(choice)
    _log(f"Joinery solver: running search_type={search_type} ({choice}) ...")

    # ── Run C++ — wrapped so Python exceptions are visible ────────────────
    import time as _time
    has_holes = any(h for h in bottom_hole_pls)
    _t0 = _time.time()
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
        _log(f"[ERROR] Python exception: {type(exc).__name__}: {exc}")
        _log(_tb.format_exc())
        return
    _log(
        f"Joinery solver: {len(elements)} elements processed, "
        f"{len(joints)} joints detected. C++ took {_time.time()-_t0:.2f}s"
    )

    # ── 7. Build layers and draw results ─────────────────────────────────
    _t1 = _time.time()
    _clear_joinery()

    layers = {}
    for full, parent, rgb, visible in _LAYER_DEFS:
        layers[full] = _ensure_layer(full, parent, rgb, visible)

    sc.doc.Layers.SetCurrentLayerIndex(layers["JoinerySolver"], True)

    l_mesh    = layers["JoinerySolver::PlatesMesh"]
    l_outline = layers["JoinerySolver::CutOutlines"]
    l_area    = layers["JoinerySolver::JointArea"]
    l_volume  = layers["JoinerySolver::JointVolumes"]
    l_line    = layers["JoinerySolver::JointLines"]

    # ── Per-element: mesh + cut outlines → one group ──────────────────────
    n_meshes   = 0
    n_outlines = 0
    for ei, el in enumerate(elements):
        elem_guids = []

        # Lofted solid mesh.
        if _draw_meshes:
            rh_mesh = _loft_mesh_to_rhino(el.loft_mesh())
            if rh_mesh and rh_mesh.Vertices.Count > 0:
                elem_guids.append(_add(rh_mesh, l_mesh))
                n_meshes += 1

        # Merged cut outlines (top + bottom).
        for pl in el.top_outlines + el.bottom_outlines:
            pts = _pl_coords_to_pt3d(pl)
            if len(pts) >= 2:
                pts.append(pts[0])
                elem_guids.append(_add(rg.Polyline(pts), l_outline))
                n_outlines += 1

        _make_group(f"joinery_elem_{ei}", elem_guids)

    # ── Per-joint: area + volumes + lines → one group ─────────────────────
    n_volumes = 0
    n_lines   = 0
    for ji, jt in enumerate(joints):
        joint_guids = []

        # Joint area quad.
        pts = _pl_coords_to_pt3d(jt.area)
        if len(pts) >= 2:
            pts.append(pts[0])
            joint_guids.append(_add(rg.Polyline(pts), l_area))

        # Joint cut volumes.
        for vol in jt.volumes:
            pts = _pl_coords_to_pt3d(vol)
            if len(pts) >= 2:
                pts.append(pts[0])
                joint_guids.append(_add(rg.Polyline(pts), l_volume))
                n_volumes += 1

        # Joint centerlines.
        for ln in jt.lines:
            pts = _pl_coords_to_pt3d(ln)
            if len(pts) >= 2:
                joint_guids.append(_add(rg.Polyline(pts), l_line))
                n_lines += 1

        _make_group(f"joinery_joint_{ji}", joint_guids)

    sc.doc.Views.Redraw()

    _log(
        f"Joinery solver done: {n_meshes} lofted plate meshes, "
        f"{n_outlines} cut outlines, "
        f"{len(joints)} joint areas, "
        f"{n_volumes} cut volumes, "
        f"{n_lines} joint lines. "
        f"Draw took {_time.time()-_t1:.2f}s"
    )


run()
