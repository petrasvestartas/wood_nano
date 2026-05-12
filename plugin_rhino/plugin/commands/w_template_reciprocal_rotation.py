#! python3
# venv: wood_env
# r: wood-nano
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import reciprocal_rotation_elements, reciprocal_rotation_elements_from_surface
from wood_nano.wood_element import unweld_mesh
from wood_nano.plate_topology import PlateTopology
from rhino_ui import extract_nurbs_surface

session = Session()
topo    = PlateTopology()


def _run(v, _):
    if v["beam_w"] <= 0:
        Rhino.RhinoApp.WriteLine("beam_w must be positive.")
        return

    mesh_type    = v["mesh_type"]
    srfs         = v["surface"]
    beam_offsets = v["beam_offsets"] or None

    if srfs:
        pts, ku, kv, du, dv, nu, nv = extract_nurbs_surface(srfs[0])
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
        source_label = f"[surface / {mesh_type}]"
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
        source_label = f"[dome / {mesh_type}]"

    session.add(unweld_mesh(dome))
    session.draw()

    topo.clear()
    for i, (m, b, t) in enumerate(zip(beams, side0, side1)):
        topo.add_plate(i, b, t, unweld_mesh(m))

    sc.doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        f"dome: {dome.number_of_faces()} faces  beams: {len(beams)}  {source_label}"
    )


process_input(
    {
        "surface":       ([], list[rg.Surface]),  # optional NURBS surface; empty = parametric dome
        # Subdivision (applies to both surface and default dome)
        "mesh_type":     (["quad", "hex", "diamond"], list[str]),
        "u_div":       (6,      int),   # mesh resolution (nx for default dome, u_div for surface)
        "v_div":       (6,      int),
        # Default dome size (ignored when a surface is provided)
        "W":             (6000.0, float),
        "D":             (5000.0, float),
        "h":             (1500.0, float),
        # Reciprocal frame parameters
        "angle":         (0.2,  float),
        "beam_w":        (50.0,  float),
        "beam_h":        (200.0,  float),
        "cut_offset":    (2.0,    float),
        # Per-direction Z offsets: 2 values (quad/diamond u,v) or 3 values (hex)
        "beam_offsets":  ([], list[float]),
    },
    callback=_run,
)
