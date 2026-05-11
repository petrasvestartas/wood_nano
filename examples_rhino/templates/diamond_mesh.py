#! python3
import System
import scriptcontext as sc
import Rhino
import Rhino.Geometry as rg
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import (
    diamond_mesh_elements,
    diamond_mesh_elements_from_surface,
)
from wood_nano.wood_element import unweld_mesh
from wood_nano.plate_topology import PlateTopology

session    = Session()
topo       = PlateTopology()
_srf_guids = []


def _expand_knots(mults, vals):
    knots = []
    for m, v in zip(mults, vals):
        knots.extend([v] * m)
    return knots[1:-1]


def _extract_surface(rhino_srf):
    ns = rhino_srf.ToNurbsSurface()
    n_u, n_v = ns.Points.CountU, ns.Points.CountV
    pts = []
    for i in range(n_u):
        for j in range(n_v):
            _, p = ns.Points.GetPoint(i, j)
            pts.append([p.X, p.Y, p.Z])
    knots_u = [ns.KnotsU[i] for i in range(ns.KnotsU.Count)]
    knots_v = [ns.KnotsV[j] for j in range(ns.KnotsV.Count)]
    return pts, knots_u, knots_v, ns.Degree(0), ns.Degree(1), n_u, n_v


def _run(v, _):
    global _srf_guids, _first_run

    doc = sc.doc
    for g in _srf_guids:
        doc.Objects.Delete(g, True)
    _srf_guids.clear()

    u_div       = v["u_div"]
    v_div       = v["v_div"]
    thickness   = v["thickness"]
    chamfer     = v["chamfer"]
    chamfer_ang = v["chamfer_angle"]

    if v["surface"]:
        pts, ku, kv, du, dv, nu, nv = _extract_surface(v["surface"][0])
        shell, elements = diamond_mesh_elements_from_surface(
            pts, ku, kv, du, dv, nu, nv,
            u_div=u_div, v_div=v_div,
            thickness=thickness, chamfer=chamfer, chamfer_angle=chamfer_ang,
        )
        label = "[user surface]"
    else:
        shell, elements = diamond_mesh_elements(
            u_div=u_div, v_div=v_div,
            thickness=thickness, chamfer=chamfer, chamfer_angle=chamfer_ang,
        )
        label = "[default]"

    session.add(shell)
    session.draw()

    topo.clear()
    for i, el in enumerate(elements):
        topo.add_plate(i, el.bottom, el.top, unweld_mesh(el.loft_mesh()))

    Rhino.RhinoApp.WriteLine(
        f"shell: {shell.number_of_faces()} faces  plates: {len(elements)}  {label}"
    )


process_input(
    {
        "surface":       ([], list[rg.Surface]),
        "u_div":         (5,      int),
        "v_div":         (2,      int),
        "thickness":     (-15.0,  float),
        "chamfer":       (30.0,   float),
        "chamfer_angle": (180.0,  float),
    },
    callback=_run,
)
