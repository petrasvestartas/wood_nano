import sys
sys.path.insert(0, r"C:\pc\3_code\code_rust\session\session_py\src")
sys.path.insert(0, r"C:\pc\3_code\code_rust\session\session_rhino\src")

from session_py.session import Session as PySession
from session_rhino.rhino_mesh import _to_rhino_welded_with_ngons
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import System
import math

# ── Change this to inspect different elements ─────────────────────────────
PB_PATH = r"C:\Users\Petras\Desktop\joinery_elem_0.pb"
ADD_NGONS = True   # False = raw CDT triangles, True = ngon version
# ─────────────────────────────────────────────────────────────────────────

data = PySession.pb_load(PB_PATH)
doc  = Rhino.RhinoDoc.ActiveDoc
log  = Rhino.RhinoApp.WriteLine

log(f"Loaded: {PB_PATH}")
log(f"  polylines={len(data.objects.polylines)}  meshes={len(data.objects.meshes)}")

# Draw polylines (outer + hole rings).
for i, pl in enumerate(data.objects.polylines):
    pts = [rg.Point3d(p.x, p.y, p.z) for p in pl.points]
    if len(pts) >= 2:
        rpl = rg.Polyline(pts)
        doc.Objects.AddPolyline(rpl)
    log(f"  polyline {i}: {len(pts)} pts")

# ── Hole ring 2D diagnostics ───────────────────────────────────────────────
def signed_area_2d(pts_2d):
    n = len(pts_2d)
    a = 0.0
    for i in range(n):
        j = (i + 1) % n
        a += pts_2d[i][0] * pts_2d[j][1] - pts_2d[j][0] * pts_2d[i][1]
    return a * 0.5

def best_fit_plane(pts_3d):
    """Returns (origin, xaxis, yaxis, zaxis) for a list of (x,y,z) tuples."""
    n = len(pts_3d)
    cx = sum(p[0] for p in pts_3d) / n
    cy = sum(p[1] for p in pts_3d) / n
    cz = sum(p[2] for p in pts_3d) / n
    # Covariance
    xx=xy=xz=yy=yz=zz = 0.0
    for p in pts_3d:
        dx,dy,dz = p[0]-cx, p[1]-cy, p[2]-cz
        xx+=dx*dx; xy+=dx*dy; xz+=dx*dz
        yy+=dy*dy; yz+=dy*dz; zz+=dz*dz
    # Normal via newell cross products
    nx = ny = nz = 0.0
    for i in range(n):
        j = (i+1)%n
        ax,ay,az = pts_3d[i][0]-cx, pts_3d[i][1]-cy, pts_3d[i][2]-cz
        bx,by,bz = pts_3d[j][0]-cx, pts_3d[j][1]-cy, pts_3d[j][2]-cz
        nx += ay*bz - az*by
        ny += az*bx - ax*bz
        nz += ax*by - ay*bx
    L = math.sqrt(nx*nx+ny*ny+nz*nz)
    if L < 1e-12:
        return (cx,cy,cz),(1,0,0),(0,1,0),(0,0,1)
    zaxis = (nx/L, ny/L, nz/L)
    # build xaxis perpendicular to zaxis
    if abs(zaxis[0]) < 0.9:
        rx,ry,rz = 1,0,0
    else:
        rx,ry,rz = 0,1,0
    # xaxis = r - (r.z)z
    dot = rx*zaxis[0]+ry*zaxis[1]+rz*zaxis[2]
    xx2 = rx-dot*zaxis[0]; xy2 = ry-dot*zaxis[1]; xz2 = rz-dot*zaxis[2]
    L2 = math.sqrt(xx2**2+xy2**2+xz2**2)
    xaxis = (xx2/L2, xy2/L2, xz2/L2)
    yaxis = (zaxis[1]*xaxis[2]-zaxis[2]*xaxis[1],
             zaxis[2]*xaxis[0]-zaxis[0]*xaxis[2],
             zaxis[0]*xaxis[1]-zaxis[1]*xaxis[0])
    return (cx,cy,cz), xaxis, yaxis, zaxis

def project_2d(p, origin, xaxis, yaxis):
    dx,dy,dz = p[0]-origin[0], p[1]-origin[1], p[2]-origin[2]
    u = dx*xaxis[0]+dy*xaxis[1]+dz*xaxis[2]
    v = dx*yaxis[0]+dy*yaxis[1]+dz*yaxis[2]
    return (u, v)

# Draw mesh.
for mesh in data.objects.meshes:
    log(f"  mesh: verts={len(mesh.vertex)}  faces={len(mesh.face)}  tris={len(mesh.triangulation)}  holes={len(mesh.face_holes)}")
    verts = {vk: (v.x, v.y, v.z) for vk, v in mesh.vertex.items()}

    for fk, rings in mesh.face_holes.items():
        outer_vks = list(mesh.face.get(fk, []))
        outer_pts = [verts[vk] for vk in outer_vks if vk in verts]
        log(f"    face {fk}: outer={len(outer_pts)} verts, {len(rings)} hole ring(s): {[len(r) for r in rings]}")

        if len(outer_pts) < 3:
            continue
        origin, xaxis, yaxis, zaxis = best_fit_plane(outer_pts)

        for hi, ring in enumerate(rings):
            ring_pts = [verts[vk] for vk in ring if vk in verts]
            ring_2d  = [project_2d(p, origin, xaxis, yaxis) for p in ring_pts]
            area = signed_area_2d(ring_2d)
            # Check adjacency in triangulation
            tris = mesh.triangulation.get(fk, [])
            ring_set = set(ring)
            adj_count = sum(1 for t in tris if any(v in ring_set for v in t))
            log(f"      hole[{hi}] vks={ring}  area2d={area:.4f}  adj_tris={adj_count}")
            for j, (pt3, pt2) in enumerate(zip(ring_pts, ring_2d)):
                log(f"        vk={ring[j]}  3D=({pt3[0]:.2f},{pt3[1]:.2f},{pt3[2]:.2f})  2D=({pt2[0]:.2f},{pt2[1]:.2f})")

    # Count naked edges
    edge_count = {}
    for fk, tris in mesh.triangulation.items():
        for tri in tris:
            for i in range(3):
                a,b = tri[i], tri[(i+1)%3]
                e = (min(a,b), max(a,b))
                edge_count[e] = edge_count.get(e, 0) + 1
    naked = sum(1 for cnt in edge_count.values() if cnt == 1)
    # also check face-boundary edges
    for fk, vks in mesh.face.items():
        n = len(vks)
        for i in range(n):
            a, b = vks[i], vks[(i+1)%n]
            e = (min(a,b), max(a,b))
            edge_count[e] = edge_count.get(e, 0) + 1
    boundary = sum(1 for cnt in edge_count.values() if cnt == 1)
    log(f"  CDT naked edges (tri-only): {naked}  boundary after adding face edges: {boundary}")

    rmesh = _to_rhino_welded_with_ngons(mesh, add_ngons=ADD_NGONS)
    valid, vlog = rmesh.IsValidWithLog()
    log(f"  rhino mesh: verts={rmesh.Vertices.Count}  faces={rmesh.Faces.Count}  ngons={rmesh.Ngons.Count}  valid={valid}")
    if not valid:
        log(f"    reason: {vlog.strip()}")
    guid = doc.Objects.AddMesh(rmesh)
    log(f"  added: {guid != System.Guid.Empty}")

doc.Views.Redraw()
