#include "vda_mesh.h"

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

namespace nb = nanobind;
using namespace nb::literals;

// ── helpers ──────────────────────────────────────────────────────────────────

static nb::list polyline_to_list(const Polyline& pl)
{
    nb::list pts;
    for (int k = 0; k < (int)pl.point_count(); ++k) {
        auto p = pl.get_point(k);
        nb::list pt;
        pt.append(p[0]); pt.append(p[1]); pt.append(p[2]);
        pts.append(pt);
    }
    return pts;
}

static nb::list polylines2d_to_list(const std::vector<std::vector<Polyline>>& data)
{
    nb::list outer;
    for (const auto& row : data) {
        nb::list inner;
        for (const auto& pl : row)
            inner.append(polyline_to_list(pl));
        outer.append(inner);
    }
    return outer;
}

static nb::dict plane_to_dict(const Plane& pl)
{
    nb::dict d;
    nb::list o, x, y;
    o.append(pl.origin()[0]); o.append(pl.origin()[1]); o.append(pl.origin()[2]);
    x.append(pl.x_axis()[0]); x.append(pl.x_axis()[1]); x.append(pl.x_axis()[2]);
    y.append(pl.y_axis()[0]); y.append(pl.y_axis()[1]); y.append(pl.y_axis()[2]);
    d["origin"] = o; d["x_axis"] = x; d["y_axis"] = y;
    return d;
}

static nb::list planes2d_to_list(const std::vector<std::vector<Plane>>& data)
{
    nb::list outer;
    for (const auto& row : data) {
        nb::list inner;
        for (const auto& pl : row)
            inner.append(pl.is_valid() ? (nb::object)plane_to_dict(pl) : nb::none());
        outer.append(inner);
    }
    return outer;
}

static nb::list strings2d_to_list(const std::vector<std::vector<std::string>>& data)
{
    nb::list outer;
    for (const auto& row : data) {
        nb::list inner;
        for (const auto& s : row) inner.append(s);
        outer.append(inner);
    }
    return outer;
}

// ── mesh from Python lists ────────────────────────────────────────────────────
static Mesh mesh_from_lists(nb::list verts_list, nb::list faces_list)
{
    std::vector<Point> pts;
    pts.reserve(verts_list.size());
    for (size_t i = 0; i < verts_list.size(); ++i) {
        auto row = nb::cast<nb::list>(verts_list[i]);
        pts.emplace_back(nb::cast<double>(row[0]),
                         nb::cast<double>(row[1]),
                         nb::cast<double>(row[2]));
    }
    std::vector<std::vector<size_t>> faces;
    faces.reserve(faces_list.size());
    for (size_t i = 0; i < faces_list.size(); ++i) {
        auto fl = nb::cast<nb::list>(faces_list[i]);
        std::vector<size_t> f;
        f.reserve(fl.size());
        for (size_t j = 0; j < fl.size(); ++j)
            f.push_back((size_t)nb::cast<int>(fl[j]));
        faces.push_back(std::move(f));
    }
    return Mesh::from_vertices_and_faces(pts, faces);
}

// ── parse face_positions / edge_divisions / edge_division_len ─────────────────
static std::vector<double> list_to_doubles(nb::list lst)
{
    std::vector<double> v;
    v.reserve(lst.size());
    for (size_t i = 0; i < lst.size(); ++i) v.push_back(nb::cast<double>(lst[i]));
    return v;
}
static std::vector<int> list_to_ints(nb::list lst)
{
    std::vector<int> v;
    v.reserve(lst.size());
    for (size_t i = 0; i < lst.size(); ++i) v.push_back(nb::cast<int>(lst[i]));
    return v;
}

// ── module ────────────────────────────────────────────────────────────────────
NB_MODULE(_vda_mesh, m) {
    nb::class_<VdaMesh>(m, "VdaMesh")
        .def(nb::init<>())
        .def_prop_ro("f_polylines",
            [](const VdaMesh& v) { return polylines2d_to_list(v.f_polylines); })
        .def_prop_ro("f_polylines_planes",
            [](const VdaMesh& v) { return planes2d_to_list(v.f_polylines_planes); })
        .def_prop_ro("f_polylines_index",
            [](const VdaMesh& v) { return strings2d_to_list(v.f_polylines_index); })
        .def_prop_ro("e_polylines",
            [](const VdaMesh& v) { return polylines2d_to_list(v.e_polylines); })
        .def_prop_ro("e_polylines_planes",
            [](const VdaMesh& v) { return planes2d_to_list(v.e_polylines_planes); })
        .def_prop_ro("e_polylines_index",
            [](const VdaMesh& v) { return strings2d_to_list(v.e_polylines_index); });

    // Factory: from Python mesh data
    m.def("make_vda_mesh",
        [](nb::list verts, nb::list faces,
           double   face_thickness,
           nb::list face_positions,
           nb::list edge_divisions,
           nb::list edge_division_len,
           double   rect_width,
           double   rect_height,
           double   rect_thickness)
        {
            Mesh mesh = mesh_from_lists(verts, faces);
            auto fp   = list_to_doubles(face_positions);
            auto ed   = list_to_ints(edge_divisions);
            auto edl  = list_to_doubles(edge_division_len);
            if (fp.empty())  fp  = {0.0};
            if (ed.empty())  ed  = {2};
            return VdaMesh(std::move(mesh), face_thickness, fp, ed, edl, {},
                           rect_width, rect_height, rect_thickness);
        },
        "vertices"_a,
        "faces"_a,
        "face_thickness"_a    = 20.0,
        "face_positions"_a    = nb::list{},
        "edge_divisions"_a    = nb::list{},
        "edge_division_len"_a = nb::list{},
        "rect_width"_a        = 200.0,
        "rect_height"_a       = 200.0,
        "rect_thickness"_a    = 20.0);

    // Factory: default 2-quad mesh
    m.def("make_default_vda_mesh",
        [](double   face_thickness,
           nb::list face_positions,
           nb::list edge_divisions,
           nb::list edge_division_len,
           double   rect_width,
           double   rect_height,
           double   rect_thickness)
        {
            auto fp  = list_to_doubles(face_positions);
            auto ed  = list_to_ints(edge_divisions);
            auto edl = list_to_doubles(edge_division_len);
            if (fp.empty()) fp = {0.0};
            if (ed.empty()) ed = {2};
            return VdaMesh(VdaMesh::default_mesh(), face_thickness, fp, ed, edl, {},
                           rect_width, rect_height, rect_thickness);
        },
        "face_thickness"_a    = 20.0,
        "face_positions"_a    = nb::list{},
        "edge_divisions"_a    = nb::list{},
        "edge_division_len"_a = nb::list{},
        "rect_width"_a        = 200.0,
        "rect_height"_a       = 200.0,
        "rect_thickness"_a    = 20.0);
}
