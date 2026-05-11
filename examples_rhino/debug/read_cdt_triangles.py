#! python3
"""Show raw C++ CDT cap triangles from a joinery element pb file.

Draws:
  - Each CDT triangle of a cap face as a separate red mesh
  - Hole ring polylines in cyan
  - Outer boundary of the cap face in white
"""
import sys
sys.path.insert(0, r"C:\pc\3_code\code_rust\session\session_py\src")
sys.path.insert(0, r"C:\pc\3_code\code_rust\session\session_rhino\src")

from session_py.session import Session as PySession
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import System

# ─────────────────────────────────────────────────────────────────────────────
PB_PATH = r"C:\Users\Petras\Desktop\joinery_elem_0.pb"
# ─────────────────────────────────────────────────────────────────────────────

data = PySession.pb_load(PB_PATH)
doc  = Rhino.RhinoDoc.ActiveDoc
log  = Rhino.RhinoApp.WriteLine

log(f"=== CDT debug: {PB_PATH} ===")

for mesh in data.objects.meshes:
    verts = {vk: (v.x, v.y, v.z) for vk, v in mesh.vertex.items()}
    log(f"mesh: {len(verts)} verts  {len(mesh.face)} faces  "
        f"{len(mesh.triangulation)} tris_faces  {len(mesh.face_holes)} hole_faces")

    for fk, tri_list in mesh.triangulation.items():
        # Get face outer boundary
        outer_vks = list(mesh.face.get(fk, []))
        rings = mesh.face_holes.get(fk, [])
        log(f"  face {fk}: outer={len(outer_vks)} vks  "
            f"holes={len(rings)}  tris={len(tri_list)}")

        # Draw outer boundary polyline (white)
        outer_pts = [verts[vk] for vk in outer_vks if vk in verts]
        if len(outer_pts) >= 2:
            outer_pts.append(outer_pts[0])  # close
            rpl = rg.Polyline([rg.Point3d(*p) for p in outer_pts])
            doc.Objects.AddPolyline(rpl)

        # Draw hole ring polylines (cyan)
        for hi, ring in enumerate(rings):
            ring_pts = [verts[vk] for vk in ring if vk in verts]
            adj = sum(1 for t in tri_list if any(v in set(ring) for v in t))
            log(f"    hole[{hi}] vks={ring}  adj_tris={adj}")
            if len(ring_pts) >= 2:
                ring_pts.append(ring_pts[0])
                rpl = rg.Polyline([rg.Point3d(*p) for p in ring_pts])
                doc.Objects.AddPolyline(rpl)

        # Draw each CDT triangle as individual mesh (red)
        for ti, tri in enumerate(tri_list):
            if len(tri) < 3:
                continue
            p0 = verts.get(tri[0])
            p1 = verts.get(tri[1])
            p2 = verts.get(tri[2])
            if not (p0 and p1 and p2):
                continue
            rm = rg.Mesh()
            rm.Vertices.Add(rg.Point3f(p0[0], p0[1], p0[2]))
            rm.Vertices.Add(rg.Point3f(p1[0], p1[1], p1[2]))
            rm.Vertices.Add(rg.Point3f(p2[0], p2[1], p2[2]))
            rm.Faces.AddFace(0, 1, 2)
            rm.Normals.ComputeNormals()
            doc.Objects.AddMesh(rm)

        log(f"  => drew {len(tri_list)} triangles for face {fk}")

doc.Views.Redraw()
log("Done.")
