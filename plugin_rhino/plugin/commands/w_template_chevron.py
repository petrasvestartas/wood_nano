#! python3
# venv: wood_env
# r: wood-nano
from typing import Any, Optional

import json
import System

import Rhino
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import annen_json_path, chevron_elements, chevron_elements_annen, chevron_elements_nurbs
from wood_nano.wood_element import unweld_mesh
from wood_nano.plate_topology import PlateTopology
from session_rhino.rhino_ui import expand_knots, extract_nurbs_surface

EXPLODE: bool = False  # True = each face separate; False = welded solid mesh

# Path to the 23 Annen building NURBS surfaces bundled with the package.
# surface_idx -1 → built-in flat 3000×5000 surface.
# surface_idx 0..22 → Annen surface from this JSON.
ANNEN_JSON: str = str(annen_json_path())

session: Session                    = Session()
topo: PlateTopology                 = PlateTopology()
_srf_guids: list[System.Guid]       = []
_annen_data: Optional[list[dict]]   = None


# =============================================================================
# RHINO UI HELPERS — Annen JSON loader and Rhino surface preview builder
# =============================================================================

def _load_annen() -> Optional[list[dict]]:
    global _annen_data
    if _annen_data is None:
        try:
            with open(ANNEN_JSON) as f:
                _annen_data = json.load(f)
        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Cannot load annen_surfaces.json: {e}")
    return _annen_data


def _build_rhino_surface(s: dict) -> Optional[Rhino.Geometry.NurbsSurface]:
    rsrf = Rhino.Geometry.NurbsSurface.Create(
        3, False, s["degree_u"] + 1, s["degree_v"] + 1, s["n_u"], s["n_v"]
    )
    for i, k in enumerate(expand_knots(s["u_mults"], s["u_nurbsknots"])):
        rsrf.KnotsU[i] = k
    for i, k in enumerate(expand_knots(s["v_mults"], s["v_nurbsknots"])):
        rsrf.KnotsV[i] = k
    for i in range(s["n_u"]):
        for j in range(s["n_v"]):
            rsrf.Points.SetPoint(i, j, Rhino.Geometry.Point3d(*s["points"][i][j]))
    return rsrf


def _run(v: dict[str, Any], _: Any) -> None:
    global _srf_guids

    # =========================================================================
    # RHINO UI — clear previous preview surface; extract input geometry
    # =========================================================================
    doc = Rhino.RhinoDoc.ActiveDoc
    for g in _srf_guids:
        doc.Objects.Delete(g, True)
    _srf_guids.clear()

    surface_idx: int = v["surface_idx"]
    kw: dict[str, Any] = dict(
        u_div=v["u_div"],
        v_division_dist=v["v_division_dist"],
        box_height=v["box_height"],
        top_plate_inlet=v["top_plate_inlet"],
        plate_thickness=v["plate_thickness"],
        edge_rotation=v["edge_rotation"],
        edge_offset=v["edge_offset"],
        ortho_edge0=v["ortho_edge0"],
        ortho_edge1=v["ortho_edge1"],
        ortho_edge2=v["ortho_edge2"],
        ortho_edge3=v["ortho_edge3"],
    )
    label: str

    if v["surface"]:
        pts, ku, kv, du, dv, nu, nv = extract_nurbs_surface(v["surface"][0])
        label = "[user surface]"
    elif surface_idx >= 0:
        data: Optional[list[dict]] = _load_annen()
        if data is None:
            return
        if surface_idx >= len(data):
            Rhino.RhinoApp.WriteLine(
                f"surface_idx must be 0..{len(data) - 1}  (got {surface_idx})"
            )
            return
        rsrf = _build_rhino_surface(data[surface_idx])
        if rsrf and rsrf.IsValid:
            g: System.Guid = doc.Objects.AddSurface(rsrf)
            if g != System.Guid.Empty:
                _srf_guids.append(g)
        label = f"[Annen #{surface_idx}]"
    else:
        label = "[default]"

    # =========================================================================
    # WOOD-NANO — compute chevron elements and joint data
    # =========================================================================
    if v["surface"]:
        shell, elements, loft_meshes, joint_data = chevron_elements_nurbs(
            pts, ku, kv, du, dv, nu, nv, **kw)
    elif surface_idx >= 0:
        shell, elements, loft_meshes, joint_data = chevron_elements_annen(
            ANNEN_JSON, surface_idx, **kw)
    else:
        shell, elements, loft_meshes, joint_data = chevron_elements(**kw)

    # =========================================================================
    # RHINO UI — draw results and store joinery metadata on plate objects
    # =========================================================================
    session.add(shell)
    session.draw()

    topo.clear()
    for i, (el, m) in enumerate(zip(elements, loft_meshes)):
        topo.add_plate(i, el.bottom, el.top, unweld_mesh(m) if EXPLODE else m)
        if joint_data and i < len(joint_data["joints_per_face"]):
            topo.tag_plate_joinery(
                i,
                joint_data["joints_per_face"][i],
                joint_data["insertion_vectors"][i],
            )

    if joint_data:
        topo.set_chevron_global_joinery(
            joint_data["three_valence"],
            joint_data["adjacency"],
        )

    doc.Views.Redraw()
    n_jt: int = sum(1 for jf in joint_data["joints_per_face"] if any(x > 0 for x in jf)) if joint_data else 0
    n_tv: int = len(joint_data["three_valence"]) if joint_data else 0
    n_adj: int = len(joint_data["adjacency"]) if joint_data else 0
    Rhino.RhinoApp.WriteLine(
        f"shell: {shell.number_of_faces()} faces  plates: {len(elements)}  {label}  "
        f"joinery: {n_jt} typed, {n_tv} three_valence, {n_adj} adjacency pairs stored"
    )


process_input(
    {
        "surface":         ([], list[Rhino.Geometry.Surface]),  # overrides surface_idx when set
        "surface_idx":     (-1,    int),   # -1 = built-in flat; 0..22 = Annen surface
        "u_div":     (4,     int),
        "v_division_dist": (900.0, float),
        "box_height":      (760.0, float),
        "top_plate_inlet": (120.0,  float),
        "plate_thickness": (40.0,  float),
        "edge_rotation":   (1.0,   float),
        "edge_offset":     (0.5,   float),
        "ortho_edge0":     (1,  int),
        "ortho_edge1":     (1,  int),
        "ortho_edge2":     (1,  int),
        "ortho_edge3":     (1,  int),
    },
    callback=_run,
)
