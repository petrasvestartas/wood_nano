#include "chevron.h"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/pair.h>
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

NB_MODULE(_chevron, m) {
    // Import _wood_element so WoodElement is registered once in nanobind's
    // global type registry.
    nb::module_::import_("wood_nano._wood_element");

    nb::class_<Chevron>(m, "Chevron")
        .def(nb::init<>())
        .def_prop_ro("mesh",     [](const Chevron& c) { return mesh_to_dict(c.mesh); })
        .def_prop_ro("elements", [](const Chevron& c) { return c.elements; })
        .def_prop_ro("insertion_vectors",
            [](const Chevron& c) { return c.insertion_vectors; })
        .def_prop_ro("joints_per_face",
            [](const Chevron& c) { return c.joints_per_face; });

    m.def("make_chevron_annen",
        [](const std::string& json_path, int surface_idx,
           int    u_divisions,
           double v_division_dist,
           double shift,
           double scale,
           double box_height,
           double top_plate_inlet,
           double plate_thickness,
           double edge_rotation,
           double edge_offset) {
            auto surfaces = wood_chevron::annen_surfaces(json_path);
            if (surfaces.empty())
                throw std::runtime_error("make_chevron_annen: failed to load " + json_path);
            if (surface_idx < 0 || surface_idx >= (int)surfaces.size())
                throw std::out_of_range(
                    "make_chevron_annen: surface_idx " + std::to_string(surface_idx) +
                    " out of range [0.." + std::to_string((int)surfaces.size() - 1) + "]");
            return Chevron(surfaces[surface_idx],
                           u_divisions, v_division_dist, shift, scale,
                           box_height, top_plate_inlet, plate_thickness,
                           edge_rotation, edge_offset);
        },
        "json_path"_a,
        "surface_idx"_a     = 0,
        "u_divisions"_a     = 4,
        "v_division_dist"_a = 900.0,
        "shift"_a           = 0.5,
        "scale"_a           = 0.05799,
        "box_height"_a      = 760.0,
        "top_plate_inlet"_a = 80.0,
        "plate_thickness"_a = 40.0,
        "edge_rotation"_a   = 1.0,
        "edge_offset"_a     = 0.5);

    m.def("make_default_chevron",
        [](int    u_divisions,
           double v_division_dist,
           double shift,
           double scale,
           double box_height,
           double top_plate_inlet,
           double plate_thickness,
           double edge_rotation,
           double edge_offset) {
            return Chevron(Chevron::default_surface(),
                           u_divisions, v_division_dist, shift, scale,
                           box_height, top_plate_inlet, plate_thickness,
                           edge_rotation, edge_offset);
        },
        "u_divisions"_a     = 4,
        "v_division_dist"_a = 900.0,
        "shift"_a           = 0.5,
        "scale"_a           = 0.05799,
        "box_height"_a      = 760.0,
        "top_plate_inlet"_a = 80.0,
        "plate_thickness"_a = 40.0,
        "edge_rotation"_a   = 1.0,
        "edge_offset"_a     = 0.5);
}
