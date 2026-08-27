#include "reciprocal_rotation.h"
#include "primitives.h"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <cmath>
#include "tolerance.h"

namespace nb = nanobind;
using namespace nb::literals;

static nb::dict mesh_to_dict(const Mesh& mesh)
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
    nb::list face_tris_list;   // fan triangulation per face (empty list for tri faces)
    for (const auto& f : faces) {
        nb::list fl;
        for (size_t vi : f) fl.append((int)vi);
        face_list.append(fl);

        nb::list tris;
        int n = (int)f.size();
        if (n > 4) {  // only for n>4 (pent/hex); quads stay as quads
            for (int i = 1; i < n - 1; ++i) {
                nb::list tri;
                tri.append((int)f[0]);
                tri.append((int)f[i]);
                tri.append((int)f[i + 1]);
                tris.append(tri);
            }
        }
        face_tris_list.append(tris);
    }
    nb::dict out;
    out["vertices"]   = nb::ndarray<nb::numpy, double, nb::ndim<2>>(vd, 2, shape, owner);
    out["faces"]      = face_list;
    out["face_tris"]  = face_tris_list;  // populated for n>3 faces; empty otherwise
    return out;
}

static nb::list polylines_to_list(const std::vector<Polyline>& pls)
{
    nb::list result;
    for (const auto& pl : pls) {
        nb::list pts_list;
        for (int k = 0; k < (int)pl.point_count(); k++) {
            auto p = pl.get_point(k);
            nb::list pt;
            pt.append(p[0]); pt.append(p[1]); pt.append(p[2]);
            pts_list.append(pt);
        }
        result.append(pts_list);
    }
    return result;
}

/// Rotate each face's vertex list until the first three vertices are non-collinear.
static bool _collinear3(const Point& a, const Point& b, const Point& c, double eps = 1e-6)
{
    double abx = b[0]-a[0], aby = b[1]-a[1], abz = b[2]-a[2];
    double acx = c[0]-a[0], acy = c[1]-a[1], acz = c[2]-a[2];
    double cx = aby*acz - abz*acy, cy = abz*acx - abx*acz, cz = abx*acy - aby*acx;
    double ab2 = abx*abx + aby*aby + abz*abz;
    double ac2 = acx*acx + acy*acy + acz*acz;
    return (cx*cx + cy*cy + cz*cz) < eps * eps * ab2 * ac2;
}

static Mesh fix_face_starts(const Mesh& m)
{
    auto [pts, faces] = m.to_vertices_and_faces();
    for (auto& face : faces) {
        int n = (int)face.size();
        for (int s = 0; s < n; ++s) {
            if (!_collinear3(pts[face[s % n]], pts[face[(s+1) % n]], pts[face[(s+2) % n]])) {
                std::rotate(face.begin(), face.begin() + s, face.end());
                break;
            }
        }
    }
    return Mesh::from_vertices_and_faces(pts, faces);
}

/// Ensure every face's normal has a positive z-component (points upward).
static Mesh orient_faces_upward(const Mesh& m)
{
    auto [pts, faces] = m.to_vertices_and_faces();
    for (auto& face : faces) {
        int n = (int)face.size();
        double nz = 0.0;
        for (int i = 0; i < n; ++i) {
            const auto& a = pts[face[i]];
            const auto& b = pts[face[(i + 1) % n]];
            nz += (a[0] - b[0]) * (a[1] + b[1]);
        }
        if (nz < 0.0)
            std::reverse(face.begin(), face.end());
    }
    return Mesh::from_vertices_and_faces(pts, faces);
}

/// Remove beams on boundary edges (edges adjacent to only one face).
static void filter_boundary_beams(ReciprocalRotation& rb)
{
    auto ekeys = rb.dome_mesh.edges();
    std::vector<Mesh>     beams_ok;
    std::vector<Polyline> side0_ok, side1_ok;
    std::vector<std::array<double,3>> dirs_ok, ups_ok;
    beams_ok.reserve(rb.beams.size());
    side0_ok.reserve(rb.side0.size());
    side1_ok.reserve(rb.side1.size());

    // Count faces per undirected edge in ONE pass over the faces.
    // edge_faces() scans every face on every call, so calling it per edge was
    // O(E*F) - session_cpp's own naked_edges comment warns against exactly
    // that. At the 100x100 divisions the surface constructor accepts, the old
    // loop did ~8e8 comparisons; this map is O(E).
    std::map<std::pair<size_t,size_t>, int> edge_face_count;
    for (const auto& [fkey, fverts] : rb.dome_mesh.face) {
        size_t n = fverts.size();
        for (size_t k = 0; k < n; ++k) {
            size_t a = fverts[k], b = fverts[(k + 1) % n];
            if (a > b) std::swap(a, b);
            edge_face_count[{a, b}]++;
        }
    }

    for (int i = 0; i < (int)ekeys.size(); i++) {
        size_t a = ekeys[i].first, b = ekeys[i].second;
        if (a > b) std::swap(a, b);
        auto it = edge_face_count.find({a, b});
        if (it != edge_face_count.end() && it->second == 2) {
            beams_ok.push_back(std::move(rb.beams[i]));
            side0_ok.push_back(std::move(rb.side0[i]));
            side1_ok.push_back(std::move(rb.side1[i]));
            dirs_ok.push_back(rb.beam_dirs[i]);
            ups_ok.push_back(rb.beam_ups[i]);
        }
    }
    rb.beams     = std::move(beams_ok);
    rb.side0     = std::move(side0_ok);
    rb.side1     = std::move(side1_ok);
    rb.beam_dirs = std::move(dirs_ok);
    rb.beam_ups  = std::move(ups_ok);
}

/// Build a NurbsSurface (degree-1 bilinear) from sinusoidal dome sample points.
static NurbsSurface build_dome_surface(int nx, int ny, double W, double D, double h)
{
    int nu = nx + 1, nv = ny + 1;
    NurbsSurface srf;
    srf.create_raw(3, false, 2, 2, nu, nv);

    for (int i = 0; i < nu; i++)
        srf.set_nurbsknot(0, i, (double)i / nx);
    for (int j = 0; j < nv; j++)
        srf.set_nurbsknot(1, j, (double)j / ny);

    for (int i = 0; i <= nx; i++)
        for (int j = 0; j <= ny; j++) {
            double x = W * i / nx;
            double y = D * j / ny;
            double z = h * std::sin(Tolerance::PI * x / W) * std::sin(Tolerance::PI * y / D);
            srf.set_cv(i, j, Point(x, y, z));
        }
    srf.transpose();
    return srf;
}

static ReciprocalRotation build_from_mesh_data(
    nb::list vertices_list, nb::list faces_list,
    double angle, double scale, double beam_w, double beam_h,
    double extend_factor, double cut_offset_factor)
{
    std::vector<Point> pts;
    pts.reserve(vertices_list.size());
    for (size_t i = 0; i < vertices_list.size(); i++) {
        auto row = nb::cast<nb::list>(vertices_list[i]);
        pts.emplace_back(nb::cast<double>(row[0]),
                         nb::cast<double>(row[1]),
                         nb::cast<double>(row[2]));
    }
    std::vector<std::vector<size_t>> faces;
    faces.reserve(faces_list.size());
    for (size_t i = 0; i < faces_list.size(); i++) {
        auto fl = nb::cast<nb::list>(faces_list[i]);
        std::vector<size_t> f;
        f.reserve(fl.size());
        for (size_t j = 0; j < fl.size(); j++)
            f.push_back((size_t)nb::cast<int>(fl[j]));
        faces.push_back(std::move(f));
    }
    Mesh mesh = Mesh::from_vertices_and_faces(pts, faces);
    return ReciprocalRotation(std::move(mesh), angle, scale, beam_w, beam_h,
                              extend_factor, cut_offset_factor);
}



/// Unwelded (per-face vertex copies, flat shading) dict of a mesh, computed
/// in C++. The Python path used to round-trip every beam across the boundary
/// three times: mesh_to_dict -> Python lists -> unweld_mesh_dict -> dict.
static nb::dict mesh_to_dict_unwelded(const session_cpp::Mesh& mesh)
{
    auto [pts, faces_sz] = mesh.to_vertices_and_faces();

    // Sequential-face-order triangulation, remapped to sequential vertex ids
    // (mirrors mesh_to_dict).
    auto vidx = mesh.vertex_index();
    std::vector<size_t> fkeys;
    fkeys.reserve(mesh.face.size());
    for (const auto& [k, _] : mesh.face) fkeys.push_back(k);
    std::sort(fkeys.begin(), fkeys.end());
    const auto& tris_map = mesh.get_triangulation();

    std::vector<std::array<double,3>> new_verts;
    new_verts.reserve(faces_sz.size() * 5);
    nb::list new_faces;
    nb::list new_face_tris;

    for (size_t fi = 0; fi < faces_sz.size(); ++fi) {
        const auto& face = faces_sz[fi];
        // per-face remap: welded sequential id -> unwelded id (first match,
        // matching unweld_mesh_dict_impl semantics)
        std::vector<std::pair<size_t,int>> remap;
        remap.reserve(face.size());
        nb::list nf;
        for (size_t old_vi : face) {
            int nvi = (int)new_verts.size();
            new_verts.push_back({pts[old_vi][0], pts[old_vi][1], pts[old_vi][2]});
            remap.push_back({old_vi, nvi});
            nf.append(nvi);
        }
        new_faces.append(nf);

        auto it = tris_map.find(fkeys[fi]);
        if (it == tris_map.end() || it->second.empty()) {
            new_face_tris.append(nb::none());
        } else {
            nb::list tlist;
            for (const auto& tri : it->second) {
                nb::list t;
                bool ok = true;
                for (size_t vk : tri) {
                    auto vit = vidx.find(vk);
                    if (vit == vidx.end()) { ok = false; break; }
                    size_t old_vi = vit->second;
                    int mapped = -1;
                    for (const auto& [o, nvi] : remap)
                        if (o == old_vi) { mapped = nvi; break; }
                    if (mapped < 0) { ok = false; break; }
                    t.append(mapped);
                }
                if (ok) tlist.append(t);
            }
            new_face_tris.append(tlist);
        }
    }

    size_t nv = new_verts.size();
    auto* vd = new double[nv * 3];
    for (size_t i = 0; i < nv; ++i) {
        vd[i*3+0] = new_verts[i][0];
        vd[i*3+1] = new_verts[i][1];
        vd[i*3+2] = new_verts[i][2];
    }
    nb::capsule owner(vd, [](void* q) noexcept { delete[] static_cast<double*>(q); });
    size_t shape[2] = {nv, 3};

    nb::dict out;
    out["vertices"]  = nb::ndarray<nb::numpy, double, nb::ndim<2>>(vd, 2, shape, owner);
    out["faces"]     = new_faces;
    out["face_tris"] = new_face_tris;
    return out;
}

/// Apply per-direction-group vertical offsets to beams and side polylines,
/// in place. This used to live in the PYTHON wrapper as per-vertex coordinate
/// arithmetic (a direct violation of the all-computation-in-C++ rule, in four
/// diverging copies), and because it rebuilt the Mesh from vertices+faces it
/// silently dropped the CDT triangulation and face_holes of offset beams.
/// Translating the session Mesh here keeps all of that intact.
static void apply_beam_offsets_impl(ReciprocalRotation& rb,
                                    const std::vector<double>& beam_offsets)
{
    if (beam_offsets.empty()) return;
    bool all_zero = true;
    for (double o : beam_offsets) if (o != 0.0) { all_zero = false; break; }
    if (all_zero) return;

    const int n_dirs = (int)beam_offsets.size();
    const double bin_width = 3.14159265358979323846 / n_dirs;

    for (size_t i = 0; i < rb.beams.size(); ++i) {
        if (i >= rb.beam_dirs.size() || i >= rb.beam_ups.size()) continue;
        const double bdx = rb.beam_dirs[i][0], bdy = rb.beam_dirs[i][1];
        double angle = std::atan2(bdy, bdx);
        angle = std::fmod(angle, 3.14159265358979323846);
        if (angle < 0.0) angle += 3.14159265358979323846;   // match Python % semantics
        int dir_idx = (int)((angle + bin_width * 0.5) / bin_width) % n_dirs;
        const double offset = beam_offsets[dir_idx];
        if (offset == 0.0) continue;

        double ux = rb.beam_ups[i][0], uy = rb.beam_ups[i][1], uz = rb.beam_ups[i][2];
        if (uz < 0.0) { ux = -ux; uy = -uy; uz = -uz; }
        const double dx = ux * offset, dy = uy * offset, dz = uz * offset;

        for (auto& [vk, vd] : rb.beams[i].vertex) {
            vd.x += dx; vd.y += dy; vd.z += dz;
        }
        Vector t(dx, dy, dz);
        if (i < rb.side0.size()) rb.side0[i].translate(t);
        if (i < rb.side1.size()) rb.side1[i].translate(t);
    }
}

NB_MODULE(_reciprocal_rotation, m) {
    m.def("apply_beam_offsets", &apply_beam_offsets_impl,
          "rb"_a, "beam_offsets"_a,
          "Translate beams + side polylines along their up axis by the\n"
          "per-direction-group scalar. In C++ so the meshes keep their\n"
          "CDT triangulation and face_holes.");


    nb::class_<ReciprocalRotation>(m, "ReciprocalRotation")
        .def(nb::init<>())
        .def_prop_ro("dome_mesh",
            [](const ReciprocalRotation& r) { return mesh_to_dict(r.dome_mesh); })
        .def_prop_ro("beams_unwelded", [](const ReciprocalRotation& r) {
            nb::list result;
            for (const auto& bm : r.beams) result.append(mesh_to_dict_unwelded(bm));
            return result;
        })
        .def_prop_ro("beams", [](const ReciprocalRotation& r) {
            nb::list result;
            for (const auto& bm : r.beams)
                result.append(mesh_to_dict(bm));
            return result;
        })
        .def_prop_ro("side0",
            [](const ReciprocalRotation& r) { return polylines_to_list(r.side0); })
        .def_prop_ro("side1",
            [](const ReciprocalRotation& r) { return polylines_to_list(r.side1); })
        .def_prop_ro("beam_dirs", [](const ReciprocalRotation& r) {
            nb::list result;
            for (const auto& d : r.beam_dirs) {
                nb::list v; v.append(d[0]); v.append(d[1]); v.append(d[2]);
                result.append(v);
            }
            return result;
        })
        .def_prop_ro("beam_ups", [](const ReciprocalRotation& r) {
            nb::list result;
            for (const auto& u : r.beam_ups) {
                nb::list v; v.append(u[0]); v.append(u[1]); v.append(u[2]);
                result.append(v);
            }
            return result;
        });

    m.def("make_reciprocal_rotation_from_mesh",
        [](nb::list vertices_list, nb::list faces_list,
           double angle, double scale, double beam_w, double beam_h,
           double extend_factor, double cut_offset_factor) {
            return build_from_mesh_data(vertices_list, faces_list,
                                        angle, scale, beam_w, beam_h,
                                        extend_factor, cut_offset_factor);
        },
        "vertices"_a,
        "faces"_a,
        "angle"_a             = 0.35,
        "scale"_a             = 1.4,
        "beam_w"_a            = 100.0,
        "beam_h"_a            = 0.0,
        "extend_factor"_a     = 5.0,
        "cut_offset_factor"_a = 1.0);

    // Default sinusoidal dome — quad mesh only (legacy, no boundary filtering).
    m.def("make_default_reciprocal_rotation",
        [](int nx, int ny, double W, double D, double h,
           double angle, double scale, double beam_w, double beam_h,
           double extend_factor, double cut_offset_factor) {
            return ReciprocalRotation(nx, ny, W, D, h,
                                      angle, scale, beam_w, beam_h,
                                      extend_factor, cut_offset_factor);
        },
        "nx"_a                = 12,
        "ny"_a                = 10,
        "W"_a                 = 12000.0,
        "D"_a                 = 10000.0,
        "h"_a                 = 3000.0,
        "angle"_a             = 0.35,
        "scale"_a             = 1.4,
        "beam_w"_a            = 100.0,
        "beam_h"_a            = 0.0,
        "extend_factor"_a     = 5.0,
        "cut_offset_factor"_a = 1.0);

    // Default sinusoidal dome with selectable mesh subdivision and boundary-beam filtering.
    // mesh_type: "quad" | "hex" | "diamond"
    m.def("make_default_reciprocal_rotation_typed",
        [](int nx, int ny, double W, double D, double h,
           const std::string& mesh_type,
           double angle, double scale, double beam_w, double beam_h,
           double extend_factor, double cut_offset_factor) {
            ReciprocalRotation rb;
            if (mesh_type == "quad") {
                rb = ReciprocalRotation(nx, ny, W, D, h,
                                        angle, scale, beam_w, beam_h,
                                        extend_factor, cut_offset_factor);
                filter_boundary_beams(rb);
            } else {
                NurbsSurface srf = build_dome_surface(nx, ny, W, D, h);
                if (mesh_type == "hex") {
                    Mesh base_mesh = Primitives::hex_mesh(srf, nx, ny);
                    rb = ReciprocalRotation(std::move(base_mesh), angle, scale, beam_w, beam_h,
                                           extend_factor, cut_offset_factor);
                    filter_boundary_beams(rb);
                    rb.dome_mesh = orient_faces_upward(rb.dome_mesh);
                } else {  // diamond
                    Mesh full_mesh = Primitives::diamond_mesh(srf, nx, ny);
                    rb = ReciprocalRotation(fix_face_starts(full_mesh), angle, scale, beam_w, beam_h,
                                           extend_factor, cut_offset_factor);
                    filter_boundary_beams(rb);
                    rb.dome_mesh = std::move(full_mesh);
                }
            }
            return rb;
        },
        "nx"_a                = 12,
        "ny"_a                = 10,
        "W"_a                 = 12000.0,
        "D"_a                 = 10000.0,
        "h"_a                 = 3000.0,
        "mesh_type"_a         = "quad",
        "angle"_a             = 0.35,
        "scale"_a             = 1.4,
        "beam_w"_a            = 100.0,
        "beam_h"_a            = 0.0,
        "extend_factor"_a     = 5.0,
        "cut_offset_factor"_a = 1.0);

    // Build from a NURBS surface using a chosen subdivision method.
    // mesh_type: "quad" | "hex" | "diamond"
    m.def("make_reciprocal_rotation_from_surface",
        [](const std::vector<std::vector<double>>& pts,
           const std::vector<double>& knots_u,
           const std::vector<double>& knots_v,
           int degree_u, int degree_v,
           int n_u, int n_v,
           const std::string& mesh_type,
           int u_div, int v_div,
           double angle, double scale, double beam_w, double beam_h,
           double extend_factor, double cut_offset_factor) {
            NurbsSurface srf;
            srf.create_raw(3, false, degree_u + 1, degree_v + 1, n_u, n_v);
            for (int i = 0; i < (int)knots_u.size(); i++)
                srf.set_nurbsknot(0, i, knots_u[i]);
            for (int j = 0; j < (int)knots_v.size(); j++)
                srf.set_nurbsknot(1, j, knots_v[j]);
            if ((int)pts.size() != n_u * n_v)
                throw std::runtime_error("make_reciprocal_rotation_from_surface: pts.size() must equal n_u*n_v");
            for (int i = 0; i < n_u; i++)
                for (int j = 0; j < n_v; j++) {
                    const auto& p = pts[i * n_v + j];
                    srf.set_cv(i, j, Point(p[0], p[1], p[2]));
                }
            if (!srf.is_valid())
                throw std::runtime_error("make_reciprocal_rotation_from_surface: resulting NurbsSurface is invalid");
            srf.transpose();
            Mesh base_mesh;
            if (mesh_type == "hex") {
                base_mesh = Primitives::hex_mesh(srf, u_div, v_div);
                ReciprocalRotation rb(std::move(base_mesh), angle, scale, beam_w, beam_h,
                                      extend_factor, cut_offset_factor);
                filter_boundary_beams(rb);
                rb.dome_mesh = orient_faces_upward(rb.dome_mesh);
                return rb;
            } else if (mesh_type == "diamond") {
                Mesh full_mesh = Primitives::diamond_mesh(srf, u_div, v_div);
                ReciprocalRotation rb(fix_face_starts(full_mesh), angle, scale, beam_w, beam_h,
                                      extend_factor, cut_offset_factor);
                filter_boundary_beams(rb);
                rb.dome_mesh = std::move(full_mesh);
                return rb;
            } else {
                base_mesh = Primitives::quad_mesh(srf, u_div, v_div);
                ReciprocalRotation rb(std::move(base_mesh), angle, scale, beam_w, beam_h,
                                      extend_factor, cut_offset_factor);
                filter_boundary_beams(rb);
                return rb;
            }
        },
        "pts"_a,
        "knots_u"_a,
        "knots_v"_a,
        "degree_u"_a,
        "degree_v"_a,
        "n_u"_a,
        "n_v"_a,
        "mesh_type"_a         = "quad",
        "u_div"_a           = 12,
        "v_div"_a           = 10,
        "angle"_a             = 0.35,
        "scale"_a             = 1.4,
        "beam_w"_a            = 100.0,
        "beam_h"_a            = 0.0,
        "extend_factor"_a     = 5.0,
        "cut_offset_factor"_a = 1.0);
}
