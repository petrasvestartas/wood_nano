#include "reflex_fold.h"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/vector.h>

namespace nb = nanobind;
using namespace nb::literals;
using Pt3 = std::array<double, 3>;
using Pts = std::vector<Pt3>;

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

static Polyline pts_to_polyline(const Pts& pts)
{
    std::vector<Point> p;
    p.reserve(pts.size());
    for (const auto& v : pts) p.emplace_back(v[0], v[1], v[2]);
    return Polyline(p);
}

NB_MODULE(_reflex_fold, m) {
    // Import _wood_element so WoodElement is registered once in nanobind's
    // global type registry — returning rf.elements works without re-registering.
    nb::module_::import_("wood_nano._wood_element");

    nb::class_<ReflexFold>(m, "ReflexFold")
        .def(nb::init<>())
        .def_prop_ro("mesh",     [](const ReflexFold& rf) { return mesh_to_dict(rf.mesh); })
        .def_prop_ro("elements", [](const ReflexFold& rf) { return rf.elements; });

    m.def("make_reflex_fold",
        [](const Pts& cs, const Pts& pr,
           double thickness, double chamfer, double chamfer_angle) {
            return ReflexFold(pts_to_polyline(cs), pts_to_polyline(pr),
                              thickness, chamfer, chamfer, chamfer_angle);
        },
        "cross_section"_a, "profile"_a,
        "thickness"_a = 10.0, "chamfer"_a = 20.0, "chamfer_angle"_a = 45.0);

    m.def("make_default_reflex_fold",
        [](double thickness, double chamfer, double chamfer_angle) {
            return ReflexFold(ReflexFold::default_cross_section(),
                              ReflexFold::default_profile(),
                              thickness, chamfer, chamfer, chamfer_angle);
        },
        "thickness"_a = 10.0, "chamfer"_a = 20.0, "chamfer_angle"_a = 45.0);
}
