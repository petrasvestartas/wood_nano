#! python3
# venv: wood_env
# r: wood-nano
from typing import Any, Optional

import Rhino

from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import connectors_elements
from wood_nano.loft import loft
from wood_nano.wood_element import unweld_mesh
from session_rhino.rhino_polyline import to_rhino as _pl_to_rhino
from wood_nano.plate_topology import PlateTopology
from session_rhino.rhino_ui import extract_mesh, loft_mesh_to_rhino

EXPLODE: bool = True  # True = each face separate; False = welded solid mesh

session: Session    = Session()
topo: PlateTopology = PlateTopology()


def _run(v: dict[str, Any], _: Any) -> None:
    # =========================================================================
    # RHINO UI — extract mesh and insertion lines from Rhino objects
    # =========================================================================
    doc = Rhino.RhinoDoc.ActiveDoc

    meshes: list[Rhino.Geometry.Mesh]    = v["mesh"]
    face_thick: float                    = v["face_thickness"]
    face_pos: list[float]                = v["face_positions"]
    edge_div: list[int]                  = v["edge_divisions"]
    edge_div_len: list[float]            = v["edge_division_len"]
    rh_lines: list[Rhino.Geometry.Line]  = v["insertion_lines"]
    rw: float                            = v["rect_width"]
    rh: float                            = v["rect_height"]
    rt: float                            = v["rect_thickness"]
    mesh_arg: Optional[tuple]
    label: str

    if meshes:
        mesh_arg = extract_mesh(meshes[0])
        label    = "[user mesh]"
    else:
        mesh_arg = None
        label    = "[default]"

    ils: list[list[list[float]]] = [
        [[ln.From.X, ln.From.Y, ln.From.Z], [ln.To.X, ln.To.Y, ln.To.Z]]
        for ln in rh_lines
    ]

    # =========================================================================
    # WOOD-NANO — compute connector elements
    # =========================================================================
    f_pl, f_planes, f_idx, e_pl, e_planes, e_idx = connectors_elements(
        mesh=mesh_arg,
        face_thickness=face_thick,
        face_positions=face_pos,
        edge_divisions=edge_div,
        edge_division_len=edge_div_len,
        insertion_lines=ils,
        rect_width=rw,
        rect_height=rh,
        rect_thickness=rt,
    )

    # =========================================================================
    # RHINO UI — loft plate meshes and register plates in topology
    # =========================================================================
    topo.clear()
    face_mesh_count: int = 0
    face_id: int = 0
    for face_row in f_pl:
        for j in range(0, len(face_row) - 1, 2):
            bot, top = face_row[j], face_row[j + 1]
            if len(bot.get_points()) < 2:
                continue
            _loft = loft([bot], [top])
            rh_mesh = loft_mesh_to_rhino(unweld_mesh(_loft) if EXPLODE else _loft)
            topo.add_plate_rh(face_id, _pl_to_rhino(bot), _pl_to_rhino(top), rh_mesh,
                              plate_type="face")
            if rh_mesh:
                face_mesh_count += 1
            face_id += 1

    edge_id: int = face_id  # globally unique plate_id
    for edge_row in e_pl:
        for j in range(0, len(edge_row) - 1, 2):
            bot, top = edge_row[j], edge_row[j + 1]
            if len(bot.get_points()) < 2 or len(top.get_points()) < 2:
                continue
            _loft = loft([bot], [top])
            rh_mesh = loft_mesh_to_rhino(unweld_mesh(_loft) if EXPLODE else _loft)
            topo.add_plate_rh(edge_id, _pl_to_rhino(bot), _pl_to_rhino(top), rh_mesh,
                              plate_type="edge")
            edge_id += 1

    session.draw()
    doc.Views.Redraw()

    Rhino.RhinoApp.WriteLine(
        f"faces: {len(f_pl)}  face plates: {face_id}"
        f"  edge connectors: {edge_id - face_id}"
        f"  face meshes: {face_mesh_count}"
        f"  {label}"
    )


process_input(
    {
        "mesh":             ([], list[Rhino.Geometry.Mesh]),
        "face_thickness":   (20.0,  float),
        "face_positions":   ([0.0], list[float]),  # multiple values = multiple panel layers
        "edge_divisions":   ([2],   list[int]),    # connectors per edge (ignored if edge_division_len set)
        "edge_division_len":([], list[float]),     # connector spacing by length; overrides edge_divisions
        "insertion_lines":  ([], list[Rhino.Geometry.Line]),
        "rect_width":       (200.0,  float),
        "rect_height":      (300.0,  float),
        "rect_thickness":   (20.0,   float),
    },
    callback=_run,
)
