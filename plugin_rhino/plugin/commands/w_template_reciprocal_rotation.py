#! python3
# venv: wood_env
# r: wood-nano
from typing import Any, Optional

import Rhino

from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import reciprocal_rotation_elements, reciprocal_rotation_elements_from_surface
from wood_nano.wood_element import unweld_mesh
from wood_nano.plate_topology import PlateTopology
from session_rhino.rhino_ui import extract_nurbs_surface

EXPLODE: bool = True  # True = each face separate; False = welded solid mesh

session: Session    = Session()
topo: PlateTopology = PlateTopology()


def _run(v: dict[str, Any], _: Any) -> None:
    # =========================================================================
    # RHINO UI — validate input; extract geometry from Rhino objects
    # =========================================================================
    if v["beam_w"] <= 0:
        Rhino.RhinoApp.WriteLine("beam_w must be positive.")
        return

    mesh_type: str                      = v["mesh_type"]
    srfs: list[Rhino.Geometry.Surface]  = v["surface"]
    beam_offsets: Optional[list[float]] = v["beam_offsets"] or None
    source_label: str

    if srfs:
        pts, ku, kv, du, dv, nu, nv = extract_nurbs_surface(srfs[0])
        source_label = f"[surface / {mesh_type}]"
    else:
        source_label = f"[dome / {mesh_type}]"

    # =========================================================================
    # WOOD-NANO — compute reciprocal frame elements
    # =========================================================================
    if srfs:
        dome, beams, side0, side1 = reciprocal_rotation_elements_from_surface(
            pts, ku, kv, du, dv, nu, nv,
            mesh_type=mesh_type,
            u_div=v["u_div"],
            v_div=v["v_div"],
            angle=v["angle"],
            beam_w=v["beam_w"],
            beam_h=v["beam_h"],
            cut_offset_factor=v["cut_offset"],
            beam_offsets=beam_offsets,
        )
    else:
        dome, beams, side0, side1 = reciprocal_rotation_elements(
            nx=v["u_div"],
            ny=v["v_div"],
            W=v["W"],
            D=v["D"],
            h=v["h"],
            mesh_type=mesh_type,
            angle=v["angle"],
            beam_w=v["beam_w"],
            beam_h=v["beam_h"],
            cut_offset_factor=v["cut_offset"],
            beam_offsets=beam_offsets,
        )

    # =========================================================================
    # RHINO UI — draw results
    # =========================================================================
    session.add(unweld_mesh(dome) if EXPLODE else dome)
    session.draw()

    topo.clear()
    for i, (m, b, t) in enumerate(zip(beams, side0, side1)):
        topo.add_plate(i, b, t, unweld_mesh(m) if EXPLODE else m)

    Rhino.RhinoDoc.ActiveDoc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        f"dome: {dome.number_of_faces()} faces  beams: {len(beams)}  {source_label}"
    )


process_input(
    {
        "surface":       ([], list[Rhino.Geometry.Surface]),  # empty = parametric dome
        "mesh_type":     (["quad", "hex", "diamond"], list[str]),
        "u_div":       (6,      int),
        "v_div":       (6,      int),
        "W":             (6000.0, float),
        "D":             (5000.0, float),
        "h":             (1500.0, float),
        "angle":         (0.2,  float),
        "beam_w":        (50.0,  float),
        "beam_h":        (200.0,  float),
        "cut_offset":    (2.0,    float),
        "beam_offsets":  ([], list[float]),  # per-direction Z offsets: 2 for quad/diamond, 3 for hex
    },
    callback=_run,
)
