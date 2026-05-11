#include "wood_session.h"
#include "wood_element.h"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/vector.h>

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

    // loft(polylines0, polylines1)
    //
    // polylines0 : list of list-of-[x,y,z] — bottom rings; [0]=outer, [1..]=holes
    // polylines1 : list of list-of-[x,y,z] — top rings;    [0]=outer, [1..]=holes
    //
    // Returns a mesh dict with keys: vertices, faces, face_tris, face_holes
    m.def("loft",
        [](const std::vector<Pts>& polylines0,
           const std::vector<Pts>& polylines1) -> nb::dict
        {
            std::vector<session_cpp::Polyline> bot, top;
            bot.reserve(polylines0.size());
            for (const auto& pts : polylines0) bot.push_back(pts_to_polyline(pts));
            top.reserve(polylines1.size());
            for (const auto& pts : polylines1) top.push_back(pts_to_polyline(pts));
            session_cpp::Mesh lm = session_cpp::Mesh::loft(bot, top);
            return mesh_to_dict(lm);
        },
        "polylines0"_a, "polylines1"_a);

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
           std::vector<double> joint_volume_ext,
           std::vector<std::vector<double>>   per_element_insertion_vectors,
           std::vector<std::vector<int>>      per_element_joint_types,
           std::vector<std::array<int,4>>     three_valence,
           std::vector<std::pair<int,int>>    adjacency) -> nb::dict {
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

            nb::dict empty;
            empty["joints"]   = nb::list();
            empty["elements"] = nb::list();
            if (plates_data.empty()) return empty;

            // Build WoodElements from bottom/top polyline pairs.
            std::vector<wood_session::WoodElement> elements;
            std::vector<session_cpp::Polyline> elem_outer_bots, elem_outer_tops;
            std::vector<std::vector<session_cpp::Polyline>> elem_hole_bots, elem_hole_tops;
            elements.reserve(plates_data.size());
            for (size_t i = 0; i < plates_data.size(); ++i) {
                const auto& pair = plates_data[i];
                if (pair.size() < 2) continue;
                elements.emplace_back(pts_to_polyline(pair[0]), pts_to_polyline(pair[1]));
                elem_outer_bots.push_back(pts_to_polyline(pair[0]));
                elem_outer_tops.push_back(pts_to_polyline(pair[1]));
                std::vector<session_cpp::Polyline> hbots, htops;
                for (size_t hi = 2; hi + 1 < pair.size(); hi += 2) {
                    hbots.push_back(pts_to_polyline(pair[hi]));
                    htops.push_back(pts_to_polyline(pair[hi + 1]));
                }
                elem_hole_bots.push_back(std::move(hbots));
                elem_hole_tops.push_back(std::move(htops));
            }
            if (elements.empty()) return empty;

            // Run joint detection + merge pipeline.
            // After the call, each element's features.top/bottom are populated
            // with merged cut outlines.
            SearchType search_type = static_cast<SearchType>(search_type_int);
            std::vector<wood_session::WoodJoint> joints;
            // direct path: iv and/or jt assigned by user, no adjacency/three_valence.
            // Both insertion_vectors and joint_types are set directly on elements;
            // wood_main.cpp simple overload reads them from element fields (no temp files).
            bool has_iv = !per_element_insertion_vectors.empty();
            bool has_jt = !per_element_joint_types.empty();
            bool direct_path = (has_iv || has_jt) && adjacency.empty() && three_valence.empty();
            // chevron path: adjacency or three_valence present → ChevronJoineryData (temp files).
            bool use_chevron = !adjacency.empty() || !three_valence.empty();
            if (direct_path) {
                for (size_t ei = 0; ei < elements.size(); ++ei) {
                    // Insertion vectors — variable-length flat list: n_faces = size/3.
                    if (ei < per_element_insertion_vectors.size()) {
                        const auto& ivN = per_element_insertion_vectors[ei];
                        auto& ivec = elements[ei].insertion_vectors;
                        ivec.clear();
                        for (size_t k = 0; k + 2 < ivN.size(); k += 3)
                            ivec.emplace_back(ivN[k], ivN[k+1], ivN[k+2]);
                    }
                    // Joint types — variable length per element (face 0=bot,1=top,2..N=sides).
                    if (ei < per_element_joint_types.size() && !per_element_joint_types[ei].empty())
                        elements[ei].joint_types = per_element_joint_types[ei];
                }
                joints = get_connection_zones(elements, search_type);
            } else if (use_chevron) {
                // ChevronJoineryData requires exactly 18 doubles per element.
                // Convert variable-length vectors; truncate or zero-pad to 18.
                wood_session::ChevronJoineryData cd;
                cd.adjacency = std::move(adjacency);
                for (const auto& ivN : per_element_insertion_vectors) {
                    std::array<double,18> iv18 = {};
                    for (size_t k = 0; k < 18 && k < ivN.size(); ++k) iv18[k] = ivN[k];
                    cd.insertion_vectors.push_back(iv18);
                }
                for (const auto& jtN : per_element_joint_types) {
                    std::array<int,6> jt6 = {};
                    for (size_t k = 0; k < 6 && k < jtN.size(); ++k) jt6[k] = jtN[k];
                    cd.joints_per_face.push_back(jt6);
                }
                cd.three_valence = std::move(three_valence);

                // Guard: empty joints_per_face (user deleted all joint-type tags) → out-of-bounds → crash.
                if (cd.joints_per_face.empty() && !elements.empty())
                    cd.joints_per_face.assign(elements.size(), {});

                // Guard: zero IV + type-10 joint → C++ normalises (0,0,0) → NaN → crash.
                // For any element where IV is all-zero but joints_per_face contains
                // type 10, compute the plate face normal from the outer bottom polyline
                // and use it as a safe fallback insertion vector.
                for (size_t ei = 0; ei < elements.size(); ++ei) {
                    if (ei >= cd.joints_per_face.size()) break;
                    bool has_t10 = false;
                    for (int jt : cd.joints_per_face[ei])
                        if (jt == 10) { has_t10 = true; break; }
                    if (!has_t10) continue;
                    if (ei < cd.insertion_vectors.size()) {
                        bool nonzero = false;
                        for (double v : cd.insertion_vectors[ei])
                            if (std::abs(v) > 1e-10) { nonzero = true; break; }
                        if (nonzero) continue;
                    } else {
                        cd.insertion_vectors.resize(ei + 1);
                    }
                    // Compute face normal from outer bottom polyline.
                    const auto& bot = elem_outer_bots[ei];
                    if (bot.point_count() < 3) continue;
                    auto p0 = bot[0], p1 = bot[1];
                    auto p2 = bot[bot.point_count() >= 3 ? bot.point_count() - 2 : 0];
                    double ax = p1[0]-p0[0], ay = p1[1]-p0[1], az = p1[2]-p0[2];
                    double bx = p2[0]-p0[0], by = p2[1]-p0[1], bz = p2[2]-p0[2];
                    double nx = ay*bz - az*by, ny = az*bx - ax*bz, nz = ax*by - ay*bx;
                    double len = std::sqrt(nx*nx + ny*ny + nz*nz);
                    if (len < 1e-10) continue;
                    nx /= len; ny /= len; nz /= len;
                    for (int s = 0; s < 6; ++s) {
                        cd.insertion_vectors[ei][s*3+0] = nx;
                        cd.insertion_vectors[ei][s*3+1] = ny;
                        cd.insertion_vectors[ei][s*3+2] = nz;
                    }
                }

                joints = get_connection_zones(elements, search_type, cd);
            } else {
                joints = get_connection_zones(elements, search_type);
            }

            // ── Convert joints ────────────────────────────────────────────
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
            nb::list py_elements;
            for (size_t ei = 0; ei < elements.size(); ++ei) {
                auto& e = elements[ei];
                nb::dict ed;

                // Inject original hole polylines into features before lofting.
                // features[0] = outer boundary (after joint cuts), features[1..] = cut notches from joints.
                // Append original plate-geometry holes so the loft includes them.
                if (!elem_hole_bots[ei].empty()) {
                    if (e.features.bottom.empty()) e.features.bottom.push_back(elem_outer_bots[ei]);
                    if (e.features.top.empty())    e.features.top.push_back(elem_outer_tops[ei]);
                    for (const auto& h : elem_hole_bots[ei]) e.features.bottom.push_back(h);
                    for (const auto& h : elem_hole_tops[ei]) e.features.top.push_back(h);
                }

                nb::list tops;
                for (const auto& pl : e.features.top)
                    tops.append(polyline_to_list(pl));
                ed["top_outlines"] = tops;

                nb::list bots;
                for (const auto& pl : e.features.bottom)
                    bots.append(polyline_to_list(pl));
                ed["bottom_outlines"] = bots;

                session_cpp::Mesh lm;
                if (!e.features.top.empty() && !e.features.bottom.empty())
                    lm = session_cpp::Mesh::loft(e.features.top, e.features.bottom);
                if (lm.vertex.empty()) lm = e.loft_mesh();
                ed["loft_mesh"] = mesh_to_dict(lm);

                py_elements.append(ed);
            }

            nb::dict out;
            out["joints"]   = py_joints;
            out["elements"] = py_elements;
            return out;
        },
        "plates"_a,
        "search_type"_a                   = 1,
        "joint_params"_a                  = std::vector<double>{},
        "joint_volume_ext"_a              = std::vector<double>{},
        "per_element_insertion_vectors"_a = std::vector<std::vector<double>>{},
        "per_element_joint_types"_a       = std::vector<std::vector<int>>{},
        "three_valence"_a                 = std::vector<std::array<int,4>>{},
        "adjacency"_a                     = std::vector<std::pair<int,int>>{}
    );
}
