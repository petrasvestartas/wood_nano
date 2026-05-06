#include "reciprocal_beam.h"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
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

NB_MODULE(_reciprocal_beam, m) {

    nb::class_<ReciprocalBeam>(m, "ReciprocalBeam")
        .def(nb::init<>())
        .def_prop_ro("dome_mesh",
            [](const ReciprocalBeam& r) { return mesh_to_dict(r.dome_mesh); })
        .def_prop_ro("beams", [](const ReciprocalBeam& r) {
            nb::list result;
            for (const auto& bm : r.beams)
                result.append(mesh_to_dict(bm));
            return result;
        })
        .def_prop_ro("side0",
            [](const ReciprocalBeam& r) { return polylines_to_list(r.side0); })
        .def_prop_ro("side1",
            [](const ReciprocalBeam& r) { return polylines_to_list(r.side1); });

    m.def("make_default_reciprocal_beam",
        [](int nx, int ny, double W, double D, double h,
           double angle, double scale, double beam_w,
           double extend_factor, double cut_offset_factor) {
            return ReciprocalBeam(nx, ny, W, D, h,
                                  angle, scale, beam_w,
                                  extend_factor, cut_offset_factor);
        },
        "nx"_a                = 12,
        "ny"_a                = 10,
        "W"_a                 = 12.0,
        "D"_a                 = 10.0,
        "h"_a                 = 3.0,
        "angle"_a             = 0.35,
        "scale"_a             = 1.4,
        "beam_w"_a            = 0.10,
        "extend_factor"_a     = 5.0,
        "cut_offset_factor"_a = 1.0);
}
