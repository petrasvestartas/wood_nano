#include "wood_session.h"
#include "wood_element.h"

#include <mutex>
#include <unordered_set>
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
    // Build the vertex-key -> sequential-index map ONCE. It used to be built
    // twice per mesh on the hot path: once inside to_vertices_and_faces and
    // once more for the tris/holes remap below. The ordering contract of
    // to_vertices_and_faces is reproduced exactly: vertices land at their
    // vertex_index slot, faces iterate over sorted face keys.
    auto vidx = mesh.vertex_index();
    size_t nv = vidx.size();
    auto* vd = new double[nv * 3];
    for (const auto& [vk, vdta] : mesh.vertex) {
        size_t i = vidx[vk];
        vd[i*3+0] = vdta.x;
        vd[i*3+1] = vdta.y;
        vd[i*3+2] = vdta.z;
    }
    nb::capsule owner(vd, [](void* p) noexcept { delete[] static_cast<double*>(p); });
    size_t shape[2] = {nv, 3};

    std::vector<size_t> fkeys;
    fkeys.reserve(mesh.face.size());
    for (const auto& [k, _] : mesh.face) fkeys.push_back(k);
    std::sort(fkeys.begin(), fkeys.end());

    nb::list face_list;
    for (size_t fk : fkeys) {
        nb::list fl;
        for (size_t vk : mesh.face.at(fk)) {
            auto it = vidx.find(vk);
            fl.append(it != vidx.end() ? (int)it->second : 0);
        }
        face_list.append(fl);
    }
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
                bool ok = true;
                for (size_t vk : tri) {
                    auto vit = vidx.find(vk);
                    if (vit == vidx.end()) { ok = false; break; }
                    t.append((int)vit->second);
                }
                // A triangle referencing a vertex that no longer exists in
                // the mesh used to be emitted with a -1 sentinel, which the
                // Python side passed straight into Mesh construction as a
                // vertex index. Skip the stale triangle instead.
                if (ok) tlist.append(t);
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
            // Consistent winding + outward normals HERE, so the compas_wood
            // adapter (separate repo) could drop its pure-Python
            // unify_cycles/centroid-flip pass (3 full-mesh Python traversals
            // per element) and the session_py layer stops shipping
            // mixed-winding lofts to viewers.
            lm.unify_winding();
            lm.orient_outward();
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
           std::vector<std::pair<int,int>>    adjacency,
           bool include_loft_mesh) -> nb::dict {
            nb::dict empty;
            empty["joints"]   = nb::list();
            empty["elements"] = nb::list();
            if (plates_data.empty()) return empty;

            // ── Compute section: mutex + GIL release ──────────────────────
            // The wood globals are process-wide, so concurrent solves must
            // serialize with or without the GIL; holding this mutex makes
            // that explicit, and with it held the GIL can be RELEASED for
            // the whole C++ compute - the inputs were already materialized
            // into C++ vectors by nanobind, so a long solve no longer blocks
            // every other Python thread in the host (Rhino UI, progress
            // reporting). The GIL is reacquired automatically when the scope
            // exits, including on exceptions.
            std::vector<wood_session::WoodElement> elements;
            std::vector<session_cpp::Polyline> elem_outer_bots, elem_outer_tops;
            std::vector<std::vector<session_cpp::Polyline>> elem_hole_bots, elem_hole_tops;
            std::vector<wood_session::WoodJoint> joints;
            static std::mutex solve_mutex;
            {
            std::lock_guard<std::mutex> solve_lock(solve_mutex);
            nb::gil_scoped_release gil_release;

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

            // Build WoodElements from bottom/top polyline pairs.
            elements.reserve(plates_data.size());
            for (size_t i = 0; i < plates_data.size(); ++i) {
                const auto& pair = plates_data[i];
                if (pair.size() < 2) continue;
                // Convert each outline once: the WoodElement ctor copies its
                // arguments, so the locals stay valid to move into the kept lists.
                auto bot_pl = pts_to_polyline(pair[0]);
                auto top_pl = pts_to_polyline(pair[1]);
                elements.emplace_back(bot_pl, top_pl);
                elem_outer_bots.push_back(std::move(bot_pl));
                elem_outer_tops.push_back(std::move(top_pl));
                std::vector<session_cpp::Polyline> hbots, htops;
                for (size_t hi = 2; hi + 1 < pair.size(); hi += 2) {
                    hbots.push_back(pts_to_polyline(pair[hi]));
                    htops.push_back(pts_to_polyline(pair[hi + 1]));
                }
                elem_hole_bots.push_back(std::move(hbots));
                elem_hole_tops.push_back(std::move(htops));
            }
            if (!elements.empty()) {

            // Run joint detection + merge pipeline.
            // After the call, each element's features.top/bottom are populated
            // with merged cut outlines.
            SearchType search_type = static_cast<SearchType>(search_type_int);
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
                // ChevronJoineryData requires exactly 18 doubles per element
                // (6 faces x 3) and 6 joint types. Zero-pad shorter vectors,
                // but REFUSE longer ones: silently truncating meant a hex
                // plate with >4 side faces lost the insertion vectors and
                // joint types of faces 6+ with no warning — wrong joints that
                // looked like a modelling mistake instead of a data loss.
                wood_session::ChevronJoineryData cd;
                cd.adjacency = std::move(adjacency);
                for (size_t ei = 0; ei < per_element_insertion_vectors.size(); ++ei) {
                    const auto& ivN = per_element_insertion_vectors[ei];
                    if (ivN.size() > 18)
                        throw std::invalid_argument(
                            "element " + std::to_string(ei) + " has " +
                            std::to_string(ivN.size()) + " insertion-vector values, but the "
                            "adjacency/three_valence path supports at most 18 (6 faces x 3). "
                            "Pass fewer faces, or drop adjacency/three_valence to use the "
                            "variable-length path.");
                    std::array<double,18> iv18 = {};
                    for (size_t k = 0; k < ivN.size(); ++k) iv18[k] = ivN[k];
                    cd.insertion_vectors.push_back(iv18);
                }
                for (size_t ei = 0; ei < per_element_joint_types.size(); ++ei) {
                    const auto& jtN = per_element_joint_types[ei];
                    if (jtN.size() > 6)
                        throw std::invalid_argument(
                            "element " + std::to_string(ei) + " has " +
                            std::to_string(jtN.size()) + " joint types, but the "
                            "adjacency/three_valence path supports at most 6 faces. "
                            "Pass fewer faces, or drop adjacency/three_valence to use the "
                            "variable-length path.");
                    std::array<int,6> jt6 = {};
                    for (size_t k = 0; k < jtN.size(); ++k) jt6[k] = jtN[k];
                    cd.joints_per_face.push_back(jt6);
                }
                cd.three_valence = std::move(three_valence);

                // Guard: empty joints_per_face (user deleted all joint-type tags) → out-of-bounds → crash.
                if (cd.joints_per_face.empty() && !elements.empty())
                    cd.joints_per_face.assign(elements.size(), {});

                // Guard: zero IV + type-10 joint → C++ normalises (0,0,0) → NaN → crash.
                //
                // When two adjacent elements BOTH have type-10 and zero IV, applying the
                // plate-face-normal fallback to both produces incompatible IV directions →
                // ss_e_op joint geometry degenerates → joint removed (user sees nothing).
                // User confirmed: element-a zero IV + element-b face-normal IV → works.
                // So for each adjacency pair where both need the fallback, skip element a
                // (leave at zero IV) and only apply fallback to element b.
                // construct_joint picks max(types[a][face], types[b][face]) = max(10,10)=10.

                auto iv_is_zero = [&](size_t ei) -> bool {
                    if (ei >= cd.insertion_vectors.size()) return true;
                    for (double v : cd.insertion_vectors[ei])
                        if (std::abs(v) > 1e-10) return false;
                    return true;
                };
                auto has_type10 = [&](size_t ei) -> bool {
                    if (ei >= cd.joints_per_face.size()) return false;
                    for (int jt : cd.joints_per_face[ei]) if (jt == 10) return true;
                    return false;
                };

                // Collect first elements of pairs where both have type-10 + zero IV.
                std::unordered_set<size_t> skip_iv;
                for (const auto& [a, b] : cd.adjacency) {
                    if (a < 0 || b < 0) continue;
                    size_t sa = static_cast<size_t>(a), sb = static_cast<size_t>(b);
                    if (sa >= elements.size() || sb >= elements.size()) continue;
                    if (has_type10(sa) && iv_is_zero(sa) &&
                        has_type10(sb) && iv_is_zero(sb))
                        skip_iv.insert(sa);
                }

                for (size_t ei = 0; ei < elements.size(); ++ei) {
                    if (skip_iv.count(ei)) continue;  // keep zero IV for this element
                    if (ei >= cd.joints_per_face.size()) break;
                    if (!has_type10(ei)) continue;
                    if (!iv_is_zero(ei)) continue;
                    if (ei >= cd.insertion_vectors.size())
                        cd.insertion_vectors.resize(ei + 1);
                    // Compute plate face normal from outer bottom polyline as fallback IV.
                    const auto& bot = elem_outer_bots[ei];
                    if (bot.point_count() < 3) continue;
                    // Newell's method over the whole ring. The previous
                    // 3-point normal (bot[0], bot[1], bot[n-2]) degenerated
                    // exactly when those points were collinear — an outline
                    // whose start vertex sits mid-edge, or an open triangle
                    // where bot[n-2] == bot[1] — leaving the element with the
                    // zero insertion vector this fallback exists to prevent.
                    session_cpp::Vector n =
                        session_cpp::Vector::average_normal(bot.get_points());
                    double nx = n[0], ny = n[1], nz = n[2];
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

            }  // if (!elements.empty())
            }  // end mutex + GIL-release scope

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

                // Lofting is 63% of the whole solve on a 145-plate model
                // (91 ms of 145 ms: Mesh::loft runs CDT cap triangulation per
                // element, then mesh_to_dict converts it all to Python), and
                // the compas_wood adapter (separate repo) never reads it.
                // Off by default; the
                // Python wrapper reconstructs it lazily from the exported
                // outlines via the standalone loft() binding, which lofts the
                // same rings in the same (top, bottom) order.
                //
                // Featureless elements (no joints, no holes) are the one case
                // the lazy path cannot reproduce: their outlines lists are
                // empty and the eager fallback was WoodElement::loft_mesh(),
                // a hand-rolled prism loft of the base plates. That one is
                // cheap (no CDT), so keep computing it eagerly.
                if (include_loft_mesh) {
                    session_cpp::Mesh lm;
                    if (!e.features.top.empty() && !e.features.bottom.empty())
                        lm = session_cpp::Mesh::loft(e.features.top, e.features.bottom);
                    if (lm.vertex.empty()) lm = e.loft_mesh();
                    lm.unify_winding();
                    lm.orient_outward();
                    ed["loft_mesh"] = mesh_to_dict(lm);
                } else if (e.features.top.empty() || e.features.bottom.empty()) {
                    session_cpp::Mesh lm = e.loft_mesh();
                    lm.unify_winding();
                    lm.orient_outward();
                    ed["loft_mesh"] = mesh_to_dict(lm);
                } else {
                    ed["loft_mesh"] = nb::none();
                }

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
        "adjacency"_a                     = std::vector<std::pair<int,int>>{},
        // Off by default: the loft is 63% of the solve and both Python
        // wrappers reconstruct it lazily from the exported outlines.
        "include_loft_mesh"_a             = false
    );
}
