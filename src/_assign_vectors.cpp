#include "point.h"
#include "vector.h"

#include <nanobind/nanobind.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/vector.h>

#include <cmath>
#include <map>

namespace nb = nanobind;
using namespace nb::literals;
using namespace session_cpp;

using Pt3 = std::array<double, 3>;
using Pts = std::vector<Pt3>;

// ── helpers ──────────────────────────────────────────────────────────────────

static Point pt3(const Pt3& p) { return Point(p[0], p[1], p[2]); }

/// Minimum distance from point p to line segment [a, b].
static double seg_dist(const Point& p, const Point& a, const Point& b)
{
    double abx = b[0]-a[0], aby = b[1]-a[1], abz = b[2]-a[2];
    double apx = p[0]-a[0], apy = p[1]-a[1], apz = p[2]-a[2];
    double ab2 = abx*abx + aby*aby + abz*abz;
    if (ab2 < 1e-20) return std::sqrt(apx*apx + apy*apy + apz*apz);
    double t = (apx*abx + apy*aby + apz*abz) / ab2;
    if (t < 0.0) t = 0.0; if (t > 1.0) t = 1.0;
    double dx = apx - t*abx, dy = apy - t*aby, dz = apz - t*abz;
    return std::sqrt(dx*dx + dy*dy + dz*dz);
}

struct PlateData {
    std::vector<std::pair<Point, Point>> segs;  // edge segments
    Vector normal;                               // Newell face normal
};

static PlateData build_plate(const Pts& raw)
{
    PlateData pd;
    if (raw.size() < 3) return pd;

    std::vector<Point> pts;
    pts.reserve(raw.size());
    for (const auto& p : raw) pts.emplace_back(p[0], p[1], p[2]);

    size_t n = pts.size();
    bool closed = (n >= 2
        && std::abs(pts[0][0]-pts[n-1][0]) < 1e-6
        && std::abs(pts[0][1]-pts[n-1][1]) < 1e-6
        && std::abs(pts[0][2]-pts[n-1][2]) < 1e-6);
    size_t n_edges = closed ? n-1 : n;

    for (size_t i = 0; i < n_edges; ++i)
        pd.segs.push_back({pts[i], pts[(i+1) % n]});

    std::vector<Point> ring(pts.begin(), closed ? pts.begin()+(ptrdiff_t)(n-1) : pts.end());
    pd.normal = Vector::average_normal(ring);
    return pd;
}

// ── module ────────────────────────────────────────────────────────────────────

NB_MODULE(_assign_vectors, m) {

    // Returns list of (plate_idx, face_slot, iv_x, iv_y, iv_z).
    // face_slot = edge_idx + 2  (0=bot cap, 1=top cap, 2..N+1=side edges).
    // Only the best-distance match per (plate_idx, face_slot) is kept.
    m.def("assign_insertion_vectors",
        [](const std::vector<Pts>& bot_polylines,
           const std::vector<Pt3>& line_starts,
           const std::vector<Pt3>& line_ends,
           double snap_radius) -> nb::list
        {
            size_t n_plates = bot_polylines.size();
            std::vector<PlateData> plates(n_plates);
            for (size_t pi = 0; pi < n_plates; ++pi)
                plates[pi] = build_plate(bot_polylines[pi]);

            // best[(plate_idx, face_slot)] = (dist, ix, iy, iz)
            std::map<std::pair<int,int>, std::tuple<double,double,double,double>> best;

            for (size_t li = 0; li < line_starts.size(); ++li) {
                Point start = pt3(line_starts[li]);
                Point end   = pt3(line_ends[li]);
                double dx = end[0]-start[0], dy = end[1]-start[1], dz = end[2]-start[2];
                double len = std::sqrt(dx*dx + dy*dy + dz*dz);
                if (len < 1e-10) continue;
                Vector unit_dir(dx/len, dy/len, dz/len);

                for (size_t pi = 0; pi < n_plates; ++pi) {
                    for (size_t ei = 0; ei < plates[pi].segs.size(); ++ei) {
                        const auto& [a, b] = plates[pi].segs[ei];
                        double d = std::min(seg_dist(start, a, b),
                                            seg_dist(end,   a, b));
                        if (d > snap_radius) continue;

                        int face_slot = (int)ei + 2;
                        auto key = std::make_pair((int)pi, face_slot);

                        // IV = normalise(cross(plate_normal, unit_dir))
                        // If normal is degenerate, pass the line direction through.
                        Vector iv;
                        if (plates[pi].normal.magnitude() > 1e-12)
                            iv = plates[pi].normal.cross(unit_dir).normalized();
                        else
                            iv = unit_dir;

                        auto it = best.find(key);
                        if (it == best.end() || d < std::get<0>(it->second))
                            best[key] = {d, iv[0], iv[1], iv[2]};
                    }
                }
            }

            nb::list result;
            for (const auto& [key, val] : best) {
                auto [pi, fs]      = key;
                auto [d, ix,iy,iz] = val;
                result.append(nb::make_tuple(pi, fs, ix, iy, iz));
            }
            return result;
        },
        "bot_polylines"_a, "line_starts"_a, "line_ends"_a, "snap_radius"_a);

    // Returns list of (query_idx, plate_idx, edge_idx) for every
    // (query point, plate edge) pair within snap_radius.
    m.def("match_points_to_plate_edges",
        [](const std::vector<Pts>& bot_polylines,
           const std::vector<Pt3>& query_points,
           double snap_radius) -> nb::list
        {
            size_t n_plates = bot_polylines.size();
            std::vector<std::vector<std::pair<Point,Point>>> segs(n_plates);
            for (size_t pi = 0; pi < n_plates; ++pi) {
                const auto& raw = bot_polylines[pi];
                if (raw.size() < 3) continue;
                std::vector<Point> pts;
                pts.reserve(raw.size());
                for (const auto& p : raw) pts.emplace_back(p[0], p[1], p[2]);
                size_t n = pts.size();
                bool closed = (n >= 2
                    && std::abs(pts[0][0]-pts[n-1][0]) < 1e-6
                    && std::abs(pts[0][1]-pts[n-1][1]) < 1e-6
                    && std::abs(pts[0][2]-pts[n-1][2]) < 1e-6);
                size_t n_edges = closed ? n-1 : n;
                for (size_t i = 0; i < n_edges; ++i)
                    segs[pi].push_back({pts[i], pts[(i+1) % n]});
            }

            nb::list result;
            for (size_t qi = 0; qi < query_points.size(); ++qi) {
                Point q = pt3(query_points[qi]);
                for (size_t pi = 0; pi < n_plates; ++pi) {
                    for (size_t ei = 0; ei < segs[pi].size(); ++ei) {
                        const auto& [a, b] = segs[pi][ei];
                        if (seg_dist(q, a, b) <= snap_radius)
                            result.append(nb::make_tuple((int)qi, (int)pi, (int)ei));
                    }
                }
            }
            return result;
        },
        "bot_polylines"_a, "query_points"_a, "snap_radius"_a);
}
