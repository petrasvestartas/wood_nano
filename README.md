# wood_nano

Python bindings for the wood C++ joinery library.

## Dev environment setup (uv)

Prerequisites: [uv](https://docs.astral.sh/uv/getting-started/installation/), CMake, and a C++ compiler.

```bash
# First time (or after a fresh clone): creates venv, installs all deps, builds C++
uv sync

# Run an example
uv run python examples_compas_wood/solver/joinery_solver_translation_shell.py
```

`uv sync` uses Python 3.13 (pinned in `.python-version`).

## Rebuild after C++ changes

```bash
uv pip install --no-build-isolation -e .
```

`--no-build-isolation` reuses the nanobind already in the venv (faster than `uv sync` for incremental rebuilds).
Python-only changes (`src/wood_nano/*.py`) take effect immediately — no rebuild needed.

## Install in Rhino (first time)

**1. Install build tools** (run once from a regular terminal):

```bash
"C:/Users/Petras/.rhinocode/py39-rh8/python.exe" -m pip install scikit-build-core nanobind ninja
```

**2. Build and install** (Rhino ScriptEditor terminal or regular terminal):

```bash
"C:/Users/Petras/.rhinocode/py39-rh8/python.exe" -m pip install --no-build-isolation -e "C:/pc/3_code/code_cpp/wood_nano"
```

Then **Reset Python Engine** in the ScriptEditor toolbar.

## System prerequisites

- **CMake ≥ 3.15** — `winget install Kitware.CMake` (Windows) or `brew install cmake` (macOS)
- **C++ compiler** — Visual Studio Build Tools on Windows, Xcode CLT (`xcode-select --install`) on macOS, `sudo apt install build-essential` on Ubuntu

## Usage

```python
from wood_nano import translation_shell_elements

shell, elements = translation_shell_elements(
    thickness=15.0,
    chamfer=2.0,
    chamfer_angle=90.0,
)
```