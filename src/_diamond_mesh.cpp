#include "diamond_mesh.h"
#include "../wood_chevron.h"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

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

NB_MODULE(_diamond_mesh, m) {
    // Import _wood_element so WoodElement is registered once in nanobind's
    // global type registry — returning dm.elements works without re-registering.
    nb::module_::import_("wood_nano._wood_element");

    nb::class_<DiamondMesh>(m, "DiamondMesh")
        .def(nb::init<>())
        .def_prop_ro("mesh",
            [](const DiamondMesh& d) { return mesh_to_dict(d.mesh); })
        .def_prop_ro("elements",
            [](const DiamondMesh& d) { return d.elements; });

    m.def("make_diamond_mesh_annen",
        [](const std::string& json_path, int surface_idx,
           int u_div, int v_div,
           double thickness, double chamfer, double chamfer_angle) {
            auto surfaces = wood_chevron::annen_surfaces(json_path);
            if (surfaces.empty())
                throw std::runtime_error("make_diamond_mesh_annen: failed to load " + json_path);
            if (surface_idx < 0 || surface_idx >= (int)surfaces.size())
                throw std::out_of_range(
                    "make_diamond_mesh_annen: surface_idx " + std::to_string(surface_idx) +
                    " out of range [0.." + std::to_string((int)surfaces.size() - 1) + "]");
            return DiamondMesh(surfaces[surface_idx], u_div, v_div,
                               thickness, chamfer, chamfer_angle);
        },
        "json_path"_a,
        "surface_idx"_a    = 0,
        "u_div"_a          = 8,
        "v_div"_a          = 4,
        "thickness"_a      = 10.0,
        "chamfer"_a        = 1.0,
        "chamfer_angle"_a  = 180.0);

    m.def("make_default_diamond_mesh",
        [](int u_div, int v_div,
           double thickness, double chamfer, double chamfer_angle) {
            return DiamondMesh(DiamondMesh::default_surface(), u_div, v_div,
                               thickness, chamfer, chamfer_angle);
        },
        "u_div"_a         = 8,
        "v_div"_a         = 4,
        "thickness"_a     = 10.0,
        "chamfer"_a       = 1.0,
        "chamfer_angle"_a = 180.0);

    // Build a DiamondMesh from a user-supplied NURBS surface passed as raw data.
    // pts      : flat list of [x,y,z] in row-major order (u varies slowest)
    // knots_u/v: OpenNURBS knot vectors (first/last already stripped)
    // degree_u/v, n_u, n_v: surface structure
    m.def("make_diamond_mesh_from_surface",
        [](const std::vector<std::vector<double>>& pts,
           const std::vector<double>& knots_u,
           const std::vector<double>& knots_v,
           int degree_u, int degree_v,
           int n_u, int n_v,
           int u_div, int v_div,
           double thickness, double chamfer, double chamfer_angle) {
            NurbsSurface srf;
            srf.create_raw(3, false, degree_u + 1, degree_v + 1, n_u, n_v);
            for (int i = 0; i < (int)knots_u.size(); i++)
                srf.set_nurbsknot(0, i, knots_u[i]);
            for (int j = 0; j < (int)knots_v.size(); j++)
                srf.set_nurbsknot(1, j, knots_v[j]);
            if ((int)pts.size() != n_u * n_v)
                throw std::runtime_error("make_diamond_mesh_from_surface: pts.size() must equal n_u*n_v");
            for (int i = 0; i < n_u; i++)
                for (int j = 0; j < n_v; j++) {
                    const auto& p = pts[i * n_v + j];
                    srf.set_cv(i, j, Point(p[0], p[1], p[2]));
                }
            if (!srf.is_valid())
                throw std::runtime_error("make_diamond_mesh_from_surface: resulting NurbsSurface is invalid");
            srf.transpose();
            return DiamondMesh(srf, u_div, v_div, thickness, chamfer, chamfer_angle);
        },
        "pts"_a,
        "knots_u"_a,
        "knots_v"_a,
        "degree_u"_a,
        "degree_v"_a,
        "n_u"_a,
        "n_v"_a,
        "u_div"_a         = 8,
        "v_div"_a         = 4,
        "thickness"_a     = 10.0,
        "chamfer"_a       = 1.0,
        "chamfer_angle"_a = 180.0);
}
