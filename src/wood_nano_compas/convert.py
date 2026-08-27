"""Direct converters from C++ raw dicts/lists to compas geometry types.

All functions take the raw Python objects returned by the nanobind C++ bindings
and produce compas types — no session_py intermediate.
"""

from compas.datastructures import Mesh
from compas.geometry import Frame, Polyline


def mesh_from_cpp(data: dict) -> Mesh:
    """Convert C++ ``{vertices, faces[, face_tris]}`` dict to :class:`compas.datastructures.Mesh`.

    When ``face_tris`` is present (CDT triangulation from the joinery solver),
    those triangles are used directly so the result matches the C++ triangulation.
    Faces without CDT entries are fan-triangulated as a fallback.
    """
    verts = [[float(v[0]), float(v[1]), float(v[2])] for v in data["vertices"]]
    faces_raw = data["faces"]
    face_tris = data.get("face_tris")

    if face_tris is not None:
        triangles = []
        for i, face in enumerate(faces_raw):
            tris = face_tris[i] if i < len(face_tris) else None
            if tris:
                triangles.extend([int(t[0]), int(t[1]), int(t[2])] for t in tris)
            else:
                face = list(map(int, face))
                triangles.extend([face[0], face[j], face[j + 1]] for j in range(1, len(face) - 1))
        return Mesh.from_vertices_and_faces(verts, triangles)

    return Mesh.from_vertices_and_faces(verts, [list(map(int, f)) for f in faces_raw])


def polyline_from_cpp(pts) -> Polyline:
    """Convert C++ point list (list of [x,y,z]) to :class:`compas.geometry.Polyline`."""
    return Polyline([[float(p[0]), float(p[1]), float(p[2])] for p in pts])


def frame_from_cpp(d: dict) -> Frame:
    """Convert C++ plane dict ``{origin, x_axis, y_axis}`` to :class:`compas.geometry.Frame`."""
    o = d["origin"]
    x = d["x_axis"]
    y = d["y_axis"]
    return Frame(
        [float(o[0]), float(o[1]), float(o[2])],
        [float(x[0]), float(x[1]), float(x[2])],
        [float(y[0]), float(y[1]), float(y[2])],
    )
