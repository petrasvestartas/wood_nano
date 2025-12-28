# wood_nano

Python bindings for the [wood](https://github.com/petrasvestartas/wood) C++ library using [nanobind](https://github.com/wjakob/nanobind).

## Project Overview

This project provides Python bindings for a computational geometry library focused on timber/wood joinery and connections. It wraps C++ code that uses CGAL, Boost, Eigen, and other computational geometry libraries.

## Tech Stack

- **Language**: C++23 with Python bindings
- **Binding Framework**: nanobind (modern, lightweight alternative to pybind11)
- **Build System**: CMake + scikit-build-core
- **Wheel Building**: cibuildwheel
- **Key Dependencies**:
  - CGAL 6.0.1 (computational geometry)
  - Boost 1.82.0 (header-only)
  - Eigen 3.4.0 (linear algebra)
  - Clipper2 (polygon clipping)
  - SQLite3 (database)
  - CDT (constrained Delaunay triangulation)

## Project Structure

```
wood_nano/
├── src/
│   ├── nanobind_binding.cpp    # Main Python bindings
│   ├── wood_nano/
│   │   ├── __init__.py         # Python package exports
│   │   └── conversions_python.py
│   └── wood/                   # C++ library (git submodule)
│       └── cmake/
│           └── src/wood/include/  # Core C++ headers and implementations
├── tests/
│   ├── test_basic.py           # Basic functionality tests
│   └── test_skeleton.py        # Mesh skeleton tests
├── data/                       # Test data files
├── .github/workflows/
│   ├── build.yml               # CI build workflow
│   └── release.yml             # PyPI release workflow
├── CMakeLists.txt              # Main CMake configuration
├── pyproject.toml              # Python project configuration
└── .deps/                      # Downloaded dependencies (auto-fetched)
```

## Core Functionality

### Exposed Python Types

- `point`, `point1`, `point2`, `point3`, `point4` - CGAL Point_3 and nested vectors
- `vector`, `vector1`, `vector2`, `vector3`, `vector4` - CGAL Vector_3 and nested vectors
- `int1`, `int2`, `int3`, `int4` - Integer vectors (nested)
- `double1`, `double2`, `double3`, `double4` - Double vectors (nested)
- `cut_type`, `cut_type1`, `cut_type2` - Enumeration for cutting operations
- `GLOBALS` - Global configuration parameters

### Key Functions

| Function | Description |
|----------|-------------|
| `add(a, b)` | Simple test function |
| `middle_point(a, b)` | Calculate midpoint between two points |
| `rtree(...)` | RTree spatial indexing for collision detection |
| `get_connection_zones(...)` | Main joinery algorithm |
| `joints(...)` | Joint detection between elements |
| `closed_mesh_from_polylines(...)` | Create mesh from polylines |
| `mesh_boolean_difference_from_polylines(...)` | Boolean difference operations |
| `beam_volumes(...)` | Compute beam volumes for joinery |
| `mesh_skeleton(...)` | Extract skeleton from mesh |
| `beam_skeleton(...)` | Extract beam axis from mesh |
| `read_xml_polylines(...)` | Read polylines from XML |
| `test()` | Print test message |

### Cut Types (Fabrication Operations)

- `nothing`, `edge_insertion`, `hole`
- `slice`, `slice_projectsheer`
- `mill`, `mill_project`, `mill_projectsheer`
- `cut`, `cut_project`, `cut_projectsheer`, `cut_reverse`
- `conic`, `conic_reverse`
- `drill`, `drill_50`, `drill_10`

## Build Instructions

### Prerequisites

- Python 3.9+
- C++ compiler with C++23 support
- CMake 3.15+

### Development Build

```bash
git clone --recursive https://github.com/petrasvestartas/wood_nano.git
cd wood_nano
pip install uv
uv venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
uv pip install -r requirements-dev.txt
uv pip install --no-build-isolation -ve .
```

### Clean Rebuild

```bash
rm -rf build .deps
pip install --no-build-isolation -ve .
```

## Testing

```bash
pytest tests/
```

Or quick test:

```bash
python -c "import wood_nano as m; print(m.add(1, 2))"
```

## Release Process

See [PYPI.md](PYPI.md) for PyPI publishing setup.

1. Update version in `src/wood_nano/__init__.py`
2. Commit and push
3. Create and push tag: `git tag v0.x.x && git push origin v0.x.x`

## Global Configuration

The `GLOBALS` class exposes various configuration parameters:

```python
import wood_nano as m

# Clipper settings
m.GLOBALS.CLIPPER_SCALE
m.GLOBALS.CLIPPER_AREA

# Distance tolerances
m.GLOBALS.DISTANCE
m.GLOBALS.DISTANCE_SQUARED
m.GLOBALS.ANGLE

# File paths
m.GLOBALS.DATA_SET_INPUT_FOLDER
m.GLOBALS.DATA_SET_OUTPUT_FILE
m.GLOBALS.DATA_SET_OUTPUT_DATABASE

# Joint parameters
m.GLOBALS.JOINT_VOLUME_EXTENSION
m.GLOBALS.JOINTS_PARAMETERS_AND_TYPES
m.GLOBALS.OUTPUT_GEOMETRY_TYPE
```

## Dependencies Auto-Download

All C++ dependencies are automatically downloaded by CMake on first build:

- Boost (header-only) -> `.deps/boost/`
- CGAL (header-only) -> `.deps/cgal/`
- Eigen (header-only) -> `.deps/eigen/`
- CDT -> `.deps/cdt/`
- Clipper2 -> `.deps/clipper2/`
- SQLite3 -> `.deps/sqlite3/`
- GoogleTest -> `.deps/googletest/`

## Platform Support

- Windows (x64)
- macOS (arm64, Intel)
- Linux (manylinux_2_28, x86_64)

Python versions: 3.9 - 3.12

## License

BSD License
