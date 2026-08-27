#include "wood_element.h"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/vector.h>

namespace nb = nanobind;
using namespace nb::literals;
using Pt3 = std::array<double, 3>;
using Pts = std::vector<Pt3>;

// ---------------------------------------------------------------------------
// unweld_mesh_dict — C++ replacement for the Python unweld_mesh() loop.
//
// Inputs (all plain Python lists — no numpy required):
//   verts      : list[list[float, float, float]]  — N vertex positions
//   faces      : list[list[int]]                  — F faces, each a list of
//                                                   vertex indices into verts
//   face_tris  : list[list[list[int, int, int]]]  — per-face CDT triangles
//                (inner lists may be empty; all ints are indices into verts)
//
// Output dict (matches _to_mesh() expectations):
//   "vertices"  : numpy ndarray(V, 3) — duplicated vertex positions
//   "faces"     : list[list[int]]     — same topology, new sequential indices
//   "face_tris" : list[list[list[int,int,int]]] — remapped CDT triangles
// ---------------------------------------------------------------------------
static nb::dict unweld_mesh_dict_impl(
    const std::vector<Pt3>&                           verts,
    const std::vector<std::vector<int>>&              faces,
    const std::vector<std::vector<std::vector<int>>>& face_tris)
{
    const size_t n_faces = faces.size();

    std::vector<Pt3>                              new_verts;
    std::vector<std::vector<int>>                 new_faces;
    std::vector<std::vector<std::vector<int>>>    new_face_tris;
    new_verts.reserve(n_faces * 5);
    new_faces.reserve(n_faces);
    new_face_tris.reserve(n_faces);

    int vi = 0;
    for (size_t fi = 0; fi < n_faces; ++fi) {
        const auto& face = faces[fi];
        const int   n    = (int)face.size();

        // Build old_vk → new_vi remap for this face (linear scan; n is tiny)
        std::vector<std::pair<int,int>> remap;
        remap.reserve(n);
        std::vector<int> nf;
        nf.reserve(n);

        for (int old_vk : face) {
            new_verts.push_back(verts[old_vk]);
            remap.push_back({old_vk, vi});
            nf.push_back(vi);
            ++vi;
        }
        new_faces.push_back(std::move(nf));

        // Remap CDT triangles for this face
        std::vector<std::vector<int>> ntris;
        if (fi < face_tris.size()) {
            for (const auto& tri : face_tris[fi]) {
                std::vector<int> nt;
                nt.reserve(3);
                for (int ov : tri) {
                    int nv_k = ov;
                    for (const auto& [ok, nk] : remap)
                        if (ok == ov) { nv_k = nk; break; }
                    nt.push_back(nv_k);
                }
                ntris.push_back(std::move(nt));
            }
        }
        new_face_tris.push_back(std::move(ntris));
    }

    // --- output ---
    const size_t nv = new_verts.size();
    auto* vd = new double[nv * 3];
    for (size_t i = 0; i < nv; ++i) {
        vd[i*3+0] = new_verts[i][0];
        vd[i*3+1] = new_verts[i][1];
        vd[i*3+2] = new_verts[i][2];
    }
    nb::capsule owner(vd, [](void* p) noexcept { delete[] static_cast<double*>(p); });
    size_t shape[2] = {nv, 3};

    nb::list out_faces;
    for (const auto& f : new_faces) {
        nb::list fl;
        for (int v : f) fl.append(v);
        out_faces.append(fl);
    }

    nb::list out_tris;
    for (const auto& tlist : new_face_tris) {
        nb::list tl;
        for (const auto& tri : tlist) {
            nb::list t;
            for (int v : tri) t.append(v);
            tl.append(t);
        }
        out_tris.append(tl);
    }

    nb::dict out;
    out["vertices"]  = nb::ndarray<nb::numpy, double, nb::ndim<2>>(vd, 2, shape, owner);
    out["faces"]     = out_faces;
    out["face_tris"] = out_tris;
    return out;
}

static Pts polyline_to_pts(const session_cpp::Polyline& pl)
{
    Pts pts;
    for (size_t i = 0; i < pl.point_count(); ++i)
        pts.push_back({pl[i][0], pl[i][1], pl[i][2]});
    return pts;
}

// ---------------------------------------------------------------------------
// Core unweld logic operating directly on C++ vertices/faces.
// Loft meshes from WoodElement have no CDT triangulation, so face_tris is
// omitted here — output dict has empty face_tris lists for every face.
// ---------------------------------------------------------------------------
static nb::dict unweld_pts_and_faces(
    const std::vector<Pt3>&              verts,
    const std::vector<std::vector<int>>& faces)
{
    const size_t n_faces = faces.size();
    std::vector<Pt3>             new_verts;
    std::vector<std::vector<int>> new_faces;
    new_verts.reserve(n_faces * 5);
    new_faces.reserve(n_faces);

    for (const auto& face : faces) {
        std::vector<int> nf;
        nf.reserve(face.size());
        for (int old_vk : face) {
            nf.push_back((int)new_verts.size());
            new_verts.push_back(verts[old_vk]);
        }
        new_faces.push_back(std::move(nf));
    }

    const size_t nv = new_verts.size();
    auto* vd = new double[nv * 3];
    for (size_t i = 0; i < nv; ++i) {
        vd[i*3+0] = new_verts[i][0];
        vd[i*3+1] = new_verts[i][1];
        vd[i*3+2] = new_verts[i][2];
    }
    nb::capsule owner(vd, [](void* p) noexcept { delete[] static_cast<double*>(p); });
    size_t shape[2] = {nv, 3};

    nb::list out_faces;
    for (const auto& f : new_faces) {
        nb::list fl;
        for (int v : f) fl.append(v);
        out_faces.append(fl);
    }

    // Empty face_tris: one empty list per face (matches _to_mesh expectations)
    nb::list out_tris;
    for (size_t i = 0; i < n_faces; ++i) out_tris.append(nb::list());

    nb::dict out;
    out["vertices"]  = nb::ndarray<nb::numpy, double, nb::ndim<2>>(vd, 2, shape, owner);
    out["faces"]     = out_faces;
    out["face_tris"] = out_tris;
    return out;
}

static nb::dict mesh_to_dict(const session_cpp::Mesh& mesh)
{
    auto [pts, faces] = mesh.to_vertices_and_faces();
    size_t nv = pts.size();
    auto* vd = new double[nv * 3];
    for (size_t i = 0; i < nv; ++i) {
        vd[i*3+0] = pts[i][0];
        vd[i*3+1] = pts[i][1];
        vd[i*3+2] = pts[i][2];
    }
    nb::capsule owner(vd, [](void* p) noexcept { delete[] static_cast<double*>(p); });
    size_t shape[2] = {nv, 3};

    nb::list face_list;
    for (const auto& f : faces) {
        nb::list fl;
        for (size_t vi : f) fl.append((int)vi);
        face_list.append(fl);
    }
    nb::dict out;
    out["vertices"] = nb::ndarray<nb::numpy, double, nb::ndim<2>>(vd, 2, shape, owner);
    out["faces"]    = face_list;
    return out;
}

NB_MODULE(_wood_element, m) {
    nb::class_<wood_session::WoodElement>(m, "WoodElement")
        .def_prop_ro("bottom",    [](const wood_session::WoodElement& e) { return polyline_to_pts(e.polylines[0]); })
        .def_prop_ro("top",       [](const wood_session::WoodElement& e) { return polyline_to_pts(e.polylines[1]); })
        .def_prop_ro("thickness", [](const wood_session::WoodElement& e) { return e.thickness; })
        .def("loft_mesh",         [](const wood_session::WoodElement& e) {
            auto lm = e.loft_mesh();
            // Consistent winding + outward normals in C++, so the compas
            // layer needs no Python-side unify/flip pass.
            lm.unify_winding();
            lm.orient_outward();
            return mesh_to_dict(lm);
        })
        .def("unweld_loft_mesh",  [](const wood_session::WoodElement& e) {
            auto lm = e.loft_mesh();
            lm.unify_winding();
            lm.orient_outward();
            auto [session_pts, faces_sz] = lm.to_vertices_and_faces();
            // Convert session_cpp::Point → Pt3 and size_t → int
            Pts pts;
            pts.reserve(session_pts.size());
            for (const auto& p : session_pts)
                pts.push_back({p[0], p[1], p[2]});
            std::vector<std::vector<int>> faces;
            faces.reserve(faces_sz.size());
            for (const auto& f : faces_sz) {
                std::vector<int> fi;
                fi.reserve(f.size());
                for (size_t v : f) fi.push_back((int)v);
                faces.push_back(std::move(fi));
            }
            return unweld_pts_and_faces(pts, faces);
        });

    m.def("unweld_mesh_dict", &unweld_mesh_dict_impl,
          "verts"_a, "faces"_a, "face_tris"_a,
          "Duplicate vertices per face (flat shading) in C++; returns dict with "
          "'vertices', 'faces', 'face_tris'.");
}
