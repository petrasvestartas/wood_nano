#include "wood_element.h"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/vector.h>

namespace nb = nanobind;
using namespace nb::literals;
using Pt3 = std::array<double, 3>;
using Pts = std::vector<Pt3>;

static Pts polyline_to_pts(const session_cpp::Polyline& pl)
{
    Pts pts;
    for (size_t i = 0; i < pl.point_count(); ++i)
        pts.push_back({pl[i][0], pl[i][1], pl[i][2]});
    return pts;
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
        .def("loft_mesh",         [](const wood_session::WoodElement& e) { return mesh_to_dict(e.loft_mesh()); });
}
