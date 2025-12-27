wood_nano
=========

Python bindings for the [wood](https://github.com/petrasvestartas/wood) C++ library using [nanobind](https://github.com/wjakob/nanobind).

|      CI              | status |
|----------------------|--------|
| Build                | [![Build](https://github.com/petrasvestartas/wood_nano/actions/workflows/build.yml/badge.svg)](https://github.com/petrasvestartas/wood_nano/actions/workflows/build.yml) |
| Release              | [![Release](https://github.com/petrasvestartas/wood_nano/actions/workflows/release.yml/badge.svg)](https://github.com/petrasvestartas/wood_nano/actions/workflows/release.yml) |

Quick Start
-----------

```bash
pip install wood_nano
```

```python
import wood_nano as m
print(m.add(1, 2))
```

Build from Source
-----------------

All C++ dependencies (CGAL, Boost, Eigen, etc.) are downloaded automatically by CMake.

### Windows

```bash
git clone --recursive https://github.com/petrasvestartas/wood_nano.git
cd wood_nano
pip install uv
uv venv .venv
.venv\Scripts\activate
uv pip install -r requirements-dev.txt
uv pip install --no-build-isolation -ve .
```

### macOS

```bash
git clone --recursive https://github.com/petrasvestartas/wood_nano.git
cd wood_nano
pip install uv
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt
uv pip install --no-build-isolation -ve .
```

### Linux

```bash
git clone --recursive https://github.com/petrasvestartas/wood_nano.git
cd wood_nano
pip install uv
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt
uv pip install --no-build-isolation -ve .
```

Test
----

```bash
python -c "import wood_nano as m; print(m.add(1, 2))"
```

PyPI Release
------------

Releases are automated via GitHub Actions using trusted publishing.

**One-time setup (PyPI):**
1. Go to https://pypi.org/manage/account/publishing/
2. Add pending publisher:
   - Project: `wood_nano`
   - Owner: `petrasvestartas`
   - Repository: `wood_nano`
   - Workflow: `release.yml`

**To publish:**
```bash
git tag v0.2.0
git push origin v0.2.0
```

Development
-----------

Update wood submodule:
```bash
git submodule update --init --recursive
```

Clean rebuild:
```bash
rm -rf build .deps
pip install --no-build-isolation -ve .
```
