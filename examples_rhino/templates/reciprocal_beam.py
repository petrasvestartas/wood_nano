#! python3
import Rhino
from session_rhino.rhino_command import process_input
from session_rhino.session import Session
from wood_nano import reciprocal_beam_elements, reciprocal_beam_elements_from_mesh

session = Session()

# Vertices/faces of a user-selected Rhino mesh, or None to use the parametric dome.
_mesh_verts = None
_mesh_faces = None


def _select_mesh():
    """Optionally select a quad mesh from the Rhino scene.

    Press Enter/Escape without selecting to use the parametric sinusoidal dome.
    """
    global _mesh_verts, _mesh_faces
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select a quad mesh (Enter/Escape = parametric dome)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Mesh
    go.AcceptNothing(True)
    go.Get()
    if go.CommandResult() != Rhino.Commands.Result.Success:
        _mesh_verts = None
        _mesh_faces = None
        Rhino.RhinoApp.WriteLine("No mesh selected — using parametric dome.")
        return
    m = go.Object(0).Mesh()
    if m is None:
        _mesh_verts = None
        _mesh_faces = None
        return
    _mesh_verts = [[v.X, v.Y, v.Z] for v in m.Vertices]
    _mesh_faces = [
        ([f.A, f.B, f.C, f.D] if f.IsQuad else [f.A, f.B, f.C])
        for f in m.Faces
    ]
    Rhino.RhinoApp.WriteLine(
        f"Mesh selected: {len(_mesh_verts)} vertices, {len(_mesh_faces)} faces."
    )


_select_mesh()


def _run(v, _):
    if v["beam_w"] <= 0:
        Rhino.RhinoApp.WriteLine("beam_w must be positive.")
        return

    if _mesh_verts is not None:
        dome, beams, side0, side1 = reciprocal_beam_elements_from_mesh(
            _mesh_verts, _mesh_faces,
            angle=v["angle"],
            scale=v["scale"],
            beam_w=v["beam_w"],
            extend_factor=v["extend_factor"],
            cut_offset_factor=v["cut_offset"],
        )
    else:
        dome, beams, side0, side1 = reciprocal_beam_elements(
            nx=v["nx"], ny=v["ny"],
            W=v["W"], D=v["D"], h=v["h"],
            angle=v["angle"],
            scale=v["scale"],
            beam_w=v["beam_w"],
            extend_factor=v["extend_factor"],
            cut_offset_factor=v["cut_offset"],
        )

    session.add(dome)
    for m in beams:
        session.add(m)
    for pl in side0:
        session.add(pl)
    for pl in side1:
        session.add(pl)
    session.draw()
    Rhino.RhinoApp.WriteLine(
        f"dome: {dome.number_of_faces()} faces  beams: {len(beams)}"
        + (" [user mesh]" if _mesh_verts else " [dome]")
    )


process_input(
    {
        # Parametric dome parameters (ignored when a mesh is selected)
        "nx":           (12,   int),
        "ny":           (10,   int),
        "W":            (12.0, float),
        "D":            (10.0, float),
        "h":            (3.0,  float),
        # Reciprocal frame parameters
        "angle":        (0.35, float),   # rotation about face normal (radians)
        "scale":        (1.4,  float),   # scales beam lines about midpoint (1.0 = original edge length)
        "beam_w":       (0.10, float),   # beam width; height = 2 × beam_w
        "extend_factor":(5.0,  float),   # extend = extend_factor × beam_w past endpoints
        "cut_offset":   (1.0,  float),   # cut plane offset = cut_offset × beam_w
    },
    callback=_run,
)
