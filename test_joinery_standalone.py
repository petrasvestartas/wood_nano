"""Standalone joinery solver test — runs without Rhino.

Reads plate coordinates from the debug log written by _joinery_solver.cpp
(C:/Users/Petras/Desktop/joinery_debug.txt) and re-runs solve_joinery so
you can iterate without opening Rhino.

Usage:
    "C:/Users/Petras/.rhinocode/py39-rh8/python.exe" test_joinery_standalone.py [search_type]
    # or
    uv run python test_joinery_standalone.py [search_type]

search_type: 0=face_to_face  1=cross_joint (default)  2=both
"""
import sys
import re
import os
import faulthandler
faulthandler.enable()

DEBUG_LOG = r"C:/Users/Petras/Desktop/joinery_debug.txt"


def parse_pts(line):
    """Parse a coordinate line like bot=[(x,y,z), (x,y,z), ...]"""
    matches = re.findall(r"\(([^)]+)\)", line)
    pts = []
    for m in matches:
        parts = [float(x) for x in m.split(",")]
        pts.append(tuple(parts))
    return pts


def load_plates_from_debug_log(path):
    """Extract plate data from the last solve_joinery debug run."""
    with open(path) as f:
        lines = f.readlines()

    plates = {}   # pair_index -> {"bot": [...], "top": [...]}
    current_pair = None
    for line in lines:
        line = line.strip()
        m = re.match(r"pair (\d+)\s+bot=\d+\s+top=\d+", line)
        if m:
            current_pair = int(m.group(1))
            plates[current_pair] = {}
            continue
        if current_pair is not None:
            if line.startswith("bot=["):
                plates[current_pair]["bot"] = parse_pts(line)
            elif line.startswith("top=["):
                plates[current_pair]["top"] = parse_pts(line)
            elif line.startswith("->"):
                current_pair = None

    return [
        [plates[k]["bot"], plates[k]["top"]]
        for k in sorted(plates.keys())
        if "bot" in plates[k] and "top" in plates[k]
    ]


def main():
    search_type = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    if not os.path.exists(DEBUG_LOG):
        print(f"Debug log not found: {DEBUG_LOG}")
        print("Run joinery_solver.py in Rhino first to generate it.")
        sys.exit(1)

    plates_data = load_plates_from_debug_log(DEBUG_LOG)
    if not plates_data:
        print("No plate data found in debug log.")
        sys.exit(1)

    print(f"Loaded {len(plates_data)} plates from debug log")
    for i, pair in enumerate(plates_data):
        print(f"  pair {i}: bot={len(pair[0])} pts  top={len(pair[1])} pts")
        print(f"    bot[0]={pair[0][0]}  bot[-1]={pair[0][-1]}")
        print(f"    top[0]={pair[1][0]}  top[-1]={pair[1][-1]}")

    print(f"\nCalling solve_joinery(search_type={search_type}) ...")

    # Import _joinery_solver directly via its .pyd path to avoid Rhino-only
    # modules (plate_topology.py imports `System` which only exists in Rhino).
    import importlib.util
    pyd = os.path.join(os.path.dirname(__file__), "src", "wood_nano",
                       "_joinery_solver.cp39-win_amd64.pyd")
    spec = importlib.util.spec_from_file_location("_joinery_solver", pyd)
    _joinery_solver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_joinery_solver)
    result = _joinery_solver.solve_joinery(plates_data, search_type)

    joints = result["joints"]
    elements = result["elements"]
    print(f"\nDone: {len(joints)} joints, {len(elements)} elements")
    for j in joints:
        print(f"  joint type={j['joint_type']}  el_ids={j['el_ids']}")
        print(f"    area: {len(j['joint_area'])} pts")
        print(f"    volumes: {len(j['joint_volumes'])} polylines  "
              + "  ".join(f"[{len(v)} pts]" for v in j['joint_volumes']))
        print(f"    lines: {len(j['joint_lines'])} segments")
    for i, el in enumerate(elements):
        tops = el['top_outlines']
        bots = el['bottom_outlines']
        print(f"  elem {i}: top_outlines={len(tops)}  bot_outlines={len(bots)}")
        for k, pl in enumerate(tops):
            pts = pl
            p0 = f"({pts[0][0]:.1f},{pts[0][1]:.1f},{pts[0][2]:.1f})" if pts else "?"
            print(f"    top[{k}]: {len(pts)} pts  first={p0}")
        for k, pl in enumerate(bots):
            pts = pl
            p0 = f"({pts[0][0]:.1f},{pts[0][1]:.1f},{pts[0][2]:.1f})" if pts else "?"
            print(f"    bot[{k}]: {len(pts)} pts  first={p0}")


if __name__ == "__main__":
    main()
