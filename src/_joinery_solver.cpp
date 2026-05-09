#include "wood_session.h"
#include "wood_element.h"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/vector.h>

#include <fstream>
#include <string>

// Debug log — written step by step; the last line before crash shows where it dies.
static std::ofstream _dbg;
static void dbg(const std::string& msg) {
    if (_dbg.is_open()) { _dbg << msg << "\n"; _dbg.flush(); }
}

namespace nb = nanobind;
using namespace nb::literals;
using Pt3 = std::array<double, 3>;
using Pts = std::vector<Pt3>;

static session_cpp::Polyline pts_to_polyline(const Pts& pts)
{
    std::vector<session_cpp::Point> p;
    p.reserve(pts.size());
    for (const auto& v : pts) p.emplace_back(v[0], v[1], v[2]);
    return session_cpp::Polyline(p);
}

static nb::list polyline_to_list(const session_cpp::Polyline& pl)
{
    nb::list out;
    for (size_t i = 0; i < pl.point_count(); ++i) {
        nb::list pt;
        pt.append(pl[i][0]);
        pt.append(pl[i][1]);
        pt.append(pl[i][2]);
        out.append(pt);
    }
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

    // Remap helpers: internal vertex/face keys → sequential indices.
    auto vidx = mesh.vertex_index();
    std::vector<size_t> fkeys;
    fkeys.reserve(mesh.face.size());
    for (const auto& [k, _] : mesh.face) fkeys.push_back(k);
    std::sort(fkeys.begin(), fkeys.end());
    std::map<size_t, size_t> fidx;
    for (size_t i = 0; i < fkeys.size(); ++i) fidx[fkeys[i]] = i;

    // face_tris: list[i] = triangulation for the i-th face (parallel to faces list).
    // Stores pre-computed CDT triangles (with holes already excluded).
    // _to_mesh on the Python side populates mesh.triangulation so to_rhino
    // uses these directly instead of re-running CDT without hole info.
    const auto& tris_map = mesh.get_triangulation();
    nb::list face_tris;
    for (size_t fk : fkeys) {
        auto it = tris_map.find(fk);
        if (it == tris_map.end() || it->second.empty()) {
            face_tris.append(nb::none());
        } else {
            nb::list tlist;
            for (const auto& tri : it->second) {
                nb::list t;
                for (size_t vk : tri) {
                    auto vit = vidx.find(vk);
                    t.append(vit != vidx.end() ? (int)vit->second : -1);
                }
                tlist.append(t);
            }
            face_tris.append(tlist);
        }
    }

    // face_holes: {sequential_face_index: [[v0,v1,...], ...]}
    nb::dict face_holes_dict;
    for (const auto& [fk, rings] : mesh.get_face_holes()) {
        auto fit = fidx.find(fk);
        if (fit == fidx.end()) continue;
        nb::list ring_list;
        for (const auto& ring : rings) {
            nb::list r;
            for (size_t vk : ring) {
                auto vit = vidx.find(vk);
                if (vit != vidx.end()) r.append((int)vit->second);
            }
            ring_list.append(r);
        }
        face_holes_dict[nb::int_(fit->second)] = ring_list;
    }

    nb::dict out;
    out["vertices"]   = nb::ndarray<nb::numpy, double, nb::ndim<2>>(vd, 2, shape, owner);
    out["faces"]      = face_list;
    out["face_tris"]  = face_tris;
    out["face_holes"] = face_holes_dict;
    return out;
}

NB_MODULE(_joinery_solver, m) {
    // Register WoodElement once in nanobind's global type registry.
    nb::module_::import_("wood_nano._wood_element");

    // solve_joinery(plates, search_type=1)
    //
    // plates : list of pairs — plates[i][0] = bottom pts, plates[i][1] = top pts
    //          each pts is a list of [x, y, z] triples
    // search_type : 0 = face_to_face, 1 = cross_joint (default), 2 = both
    //
    // Returns dict:
    //   "joints"   : list of joint dicts (el_ids, joint_type, joint_area,
    //                joint_volumes, joint_lines)
    //   "elements" : list of element dicts (top_outlines, bottom_outlines,
    //                loft_mesh) — features are populated after detection
    m.def("solve_joinery",
        [](const std::vector<std::vector<Pts>>& plates_data,
           int search_type_int,
           std::vector<double> joint_params,
           std::vector<double> joint_volume_ext) -> nb::dict {
            // Initialise all wood globals to their documented defaults.
            // Tests do this via reset_defaults(); without it JOINTS_PARAMETERS_AND_TYPES
            // is an empty vector → JPT[row*3] crashes on first cross/lap joint.
            wood_session::globals::reset_defaults();
            // Optional caller-supplied joint family parameters (21 doubles = 7 families × 3).
            // When provided, overrides the reset_defaults() values.
            if (joint_params.size() == 21)
                wood_session::globals::JOINTS_PARAMETERS_AND_TYPES = joint_params;
            // Optional joint volume extension: [width, height, length] in mm.
            if (joint_volume_ext.size() >= 3) {
                wood_session::globals::JOINT_VOLUME_EXTENSION[0] = joint_volume_ext[0];
                wood_session::globals::JOINT_VOLUME_EXTENSION[1] = joint_volume_ext[1];
                wood_session::globals::JOINT_VOLUME_EXTENSION[2] = joint_volume_ext[2];
            }
            // Tighten cross-joint endpoint rejection threshold: default 0.01 (0.1 mm)
            // can reject valid crossings for off-centre connectors (edge_divisions > 1).
            // 1e-6 = 0.001 mm is safe for any realistic geometry.
            wood_session::set_cross_joint_distance_squared(1e-6);

            _dbg.open("C:/Users/Petras/Desktop/joinery_debug.txt", std::ios::trunc);
            dbg("solve_joinery start  plates=" + std::to_string(plates_data.size())
                + "  search_type=" + std::to_string(search_type_int));

            nb::dict empty;
            empty["joints"]   = nb::list();
            empty["elements"] = nb::list();
            if (plates_data.empty()) { dbg("empty input"); return empty; }

            // Build WoodElements from bottom/top polyline pairs.
            std::vector<wood_session::WoodElement> elements;
            elements.reserve(plates_data.size());
            for (size_t i = 0; i < plates_data.size(); ++i) {
                const auto& pair = plates_data[i];
                if (pair.size() < 2) { dbg("  pair " + std::to_string(i) + " skipped (size<2)"); continue; }
                // Dump full coordinates so we can reproduce the test standalone.
                auto dump_pts = [&](const char* tag, const Pts& pts) {
                    std::string s = "    "; s += tag; s += "=[";
                    for (size_t p = 0; p < pts.size(); ++p) {
                        if (p) s += ", ";
                        s += "("; s += std::to_string(pts[p][0]);
                        s += ","; s += std::to_string(pts[p][1]);
                        s += ","; s += std::to_string(pts[p][2]); s += ")";
                    }
                    s += "]"; dbg(s);
                };
                dbg("  pair " + std::to_string(i)
                    + "  bot=" + std::to_string(pair[0].size())
                    + "  top=" + std::to_string(pair[1].size()));
                dump_pts("bot", pair[0]);
                dump_pts("top", pair[1]);
                elements.emplace_back(pts_to_polyline(pair[0]), pts_to_polyline(pair[1]));
                dbg("    -> WoodElement planes=" + std::to_string(elements.back().planes.size())
                    + " polylines=" + std::to_string(elements.back().polylines.size()));
            }
            if (elements.empty()) { dbg("no elements built"); return empty; }

            // Run joint detection + merge pipeline.
            // After the call, each element's features.top/bottom are populated
            // with merged cut outlines.
            dbg("get_connection_zones start  elements=" + std::to_string(elements.size()));
            SearchType search_type = static_cast<SearchType>(search_type_int);
            auto joints = get_connection_zones(elements, search_type);
            dbg("get_connection_zones done  joints=" + std::to_string(joints.size()));

            // ── Convert joints ────────────────────────────────────────────
            dbg("converting joints");
            nb::list py_joints;
            for (const auto& j : joints) {
                nb::dict jd;
                jd["el_ids"]     = nb::make_tuple(j.el_ids.first, j.el_ids.second);
                jd["joint_type"] = j.joint_type;
                jd["joint_area"] = polyline_to_list(j.joint_area);

                // joint_volumes: up to 4 optional polylines
                nb::list vols;
                for (const auto& vol : j.joint_volumes_pair_a_pair_b) {
                    if (vol.has_value())
                        vols.append(polyline_to_list(*vol));
                }
                jd["joint_volumes"] = vols;

                // joint_lines: 2 Lines → [[start_pt, end_pt], ...]
                nb::list lines;
                for (const auto& ln : j.joint_lines) {
                    auto s = ln.start();
                    auto e = ln.end();
                    nb::list sp; sp.append(s[0]); sp.append(s[1]); sp.append(s[2]);
                    nb::list ep; ep.append(e[0]); ep.append(e[1]); ep.append(e[2]);
                    nb::list seg; seg.append(sp); seg.append(ep);
                    lines.append(seg);
                }
                jd["joint_lines"] = lines;

                py_joints.append(jd);
            }

            // ── Convert element features ──────────────────────────────────
            dbg("converting elements  count=" + std::to_string(elements.size()));
            nb::list py_elements;
            for (size_t ei = 0; ei < elements.size(); ++ei) {
                const auto& e = elements[ei];
                dbg("  elem " + std::to_string(ei)
                    + "  top_outlines=" + std::to_string(e.features.top.size())
                    + "  bot_outlines=" + std::to_string(e.features.bottom.size()));
                nb::dict ed;

                nb::list tops;
                for (const auto& pl : e.features.top)
                    tops.append(polyline_to_list(pl));
                ed["top_outlines"] = tops;

                nb::list bots;
                for (const auto& pl : e.features.bottom)
                    bots.append(polyline_to_list(pl));
                ed["bottom_outlines"] = bots;

                dbg("  elem " + std::to_string(ei) + " loft_mesh start");
                session_cpp::Mesh lm;
                // features.top / features.bottom: [0] = outer boundary, [1..] = hole rings.
                // session_cpp::Mesh::loft handles outer + holes natively.
                if (!e.features.top.empty() && !e.features.bottom.empty()) {
                    dbg("    top_rings=" + std::to_string(e.features.top.size())
                        + "  bot_rings=" + std::to_string(e.features.bottom.size()));
                    lm = session_cpp::Mesh::loft(e.features.top, e.features.bottom);
                }
                if (lm.vertex.empty()) lm = e.loft_mesh();
                ed["loft_mesh"] = mesh_to_dict(lm);
                dbg("  elem " + std::to_string(ei) + " loft_mesh done");

                py_elements.append(ed);
            }

            dbg("solve_joinery complete");
            nb::dict out;
            out["joints"]   = py_joints;
            out["elements"] = py_elements;
            return out;
        },
        "plates"_a,
        "search_type"_a       = 1,
        "joint_params"_a      = std::vector<double>{},
        "joint_volume_ext"_a  = std::vector<double>{}
    );
}
