#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/tuple.h>
#include <nanobind/stl/vector.h>

#include <fstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

// nlohmann/json is provided transitively via session_core's PUBLIC include dirs
#include "json.h"

namespace nb = nanobind;
using PointList    = std::vector<std::vector<double>>;        // one polyline: [[x,y,z], ...]
using PolylineList = std::vector<PointList>;                  // list of polylines

// Load a dataset JSON file produced by convert_xml_to_json.py.
// Format: {"name": "...", "polylines": [[x0,y0,z0, x1,y1,z1, ...], ...]}
// Even-indexed polylines are bottom faces; odd-indexed are top faces.
// Returns (bottom_polylines, top_polylines).
static std::tuple<PolylineList, PolylineList>
load_dataset(const std::string& path)
{
    std::ifstream f(path);
    if (!f)
        throw std::runtime_error("load_dataset: cannot open " + path);

    nlohmann::json doc;
    f >> doc;

    auto& raw = doc.at("polylines");
    PolylineList bottom, top;

    for (std::size_t i = 0; i < raw.size(); ++i) {
        auto& coords = raw[i];
        PointList polyline;
        for (std::size_t j = 0; j + 2 < coords.size(); j += 3)
            polyline.push_back({coords[j], coords[j + 1], coords[j + 2]});
        if (i % 2 == 0)
            bottom.push_back(polyline);
        else
            top.push_back(polyline);
    }
    return {bottom, top};
}

NB_MODULE(_datasets, m)
{
    m.doc() = "Dataset loader: reads wood_nano JSON datasets produced from XML source files.";

    m.def("load_dataset", &load_dataset,
          nb::arg("path"),
          "Load a dataset JSON file → (bottom_polylines, top_polylines).\n"
          "Each polyline is a list of [x, y, z] sublists.");
}
