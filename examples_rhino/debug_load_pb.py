#! python3
"""Load a session .pb file and display all meshes in the active Rhino document.

Usage: run this script in Rhino's ScriptEditor (Ctrl+Shift+E).
Set PB_PATH below to the .pb file you want to inspect.
"""

import Rhino
import scriptcontext as sc

from session_py.session import Session as PySession
from session_rhino.rhino_mesh import to_rhino as _mesh_to_rhino

PB_PATH = r"C:\pc\3_code\code_cpp\wood\data\output\example_loft_holes_cpp.pb"

data = PySession.pb_load(PB_PATH)
meshes = list(data.objects.meshes)
print(f"meshes in pb: {len(meshes)}")

doc = sc.doc
added = 0
for mesh in meshes:
    rmesh = _mesh_to_rhino(mesh)
    if rmesh is None:
        print(f"  [{mesh.name}] → could not convert")
        continue
    valid, log = rmesh.IsValidWithLog()
    print(f"  [{mesh.name}] verts={rmesh.Vertices.Count} faces={rmesh.Faces.Count} valid={valid}")
    if not valid:
        print(f"    reason: {log.strip()}")
    attr = Rhino.DocObjects.ObjectAttributes()
    attr.Name = mesh.name or f"mesh_{added}"
    doc.Objects.AddMesh(rmesh, attr)
    added += 1

doc.Views.Redraw()
print(f"added {added} meshes to document")
