# wood_nano — Agent Instructions

## Core Rule

**All computation must happen in C++.** The Python layer (`src/wood_nano/*.py`) is
pure data transfer: it converts inputs to the C++ binding format, calls the C++
function, and converts the output to `session_py` types. Never implement
geometry, math, or algorithms in Python.

## Workflow for adding a new function

1. Implement the algorithm in `src/_translation_shell.cpp` (or a new `src/_<name>.cpp`)
   as a `NB_MODULE` function using pure STL — no session_cpp `.cpp` files, no protobuf.
2. Add the nanobind module to `CMakeLists.txt` with `nanobind_add_module`.
3. Write a thin Python wrapper in `src/wood_nano/<name>.py` that:
   - Accepts `session_py` types or raw lists
   - Calls the C++ binding
   - Returns `session_py` types
4. Export the wrapper from `src/wood_nano/__init__.py`.
5. After rebuilding, copy the new plain `.pyd` files to `src/wood_nano/` (see below).

## No-prototype rule

Never implement geometry in the Python wrappers as a "temporary" approximation.
If the C++ side is not ready, leave the function unimplemented rather than
writing a Python fallback that will silently produce wrong results.

## Rebuild steps (after C++ changes)

```bash
# uv dev environment (Python 3.13)
uv pip install --no-build-isolation -e .

# Rhino Python (Python 3.9, stable ABI)
"C:/Users/Petras/.rhinocode/py39-rh8/python.exe" -m pip install --no-build-isolation -e .
```

Both commands build all C++ modules and create a scikit-build-core editable install.
No manual file copying or `.pth` creation is needed.

## uv dev environment (first time)

```bash
uv sync                                    # creates venv, installs all deps
uv pip install --no-build-isolation -e .   # build C++ + editable install
uv run python examples_session_py/solver/joinery_solver_translation_shell.py
```

`uv sync` uses Python 3.13 (see `.python-version`). Python 3.13 is pinned to
match Rhino 9's Python runtime, and because downstream consumers (the
compas_wood adapter, in its own repo) may share the interpreter with libraries
that are not yet 3.14-clean.

## Running anything long: use the guard

**Never launch a solver, benchmark, example or dataset sweep directly.** Run it
through `tools/run_guarded.ps1`, which applies a wall-clock timeout, a
kernel-enforced memory cap, and a one-at-a-time check:

```powershell
tools/run_guarded.ps1 -FilePath .venv/Scripts/python.exe `
    -Arguments 'examples_session_py/solver/joinery_solver_datasets.py' `
    -TimeoutMinutes 10 -MemoryLimitGB 4
```

Defaults are 10 minutes and 4 GB. Exit code 124 means the timeout killed it.

Why this exists: on 2026-08-27 three concurrent copies of wood's
`main_wood_04_all_datasets.exe` reached 51 GB, 45 GB and 18 GB of committed
memory on a 32 GB machine. Windows logged Resource-Exhaustion-Detector (event
2004) three times and then took a dirty shutdown (Kernel-Power 41).

Three rules follow from that:

1. **Bound every run.** These algorithms are small; anything that has not
   finished in ten minutes is wedged, not slow. Kill it and investigate.
2. **Bound the memory too.** A timeout alone would not have saved that machine —
   it was thrashing long before any sensible deadline expired. The memory cap is
   the guard that protects the box, because the kernel refuses the allocation
   instead of letting it eat the page file.
3. **One run at a time.** Never start a second copy of a sweep while one is
   running. Concurrency is what turned a survivable leak into a crash, and the
   copies also raced on each other's output files.

Never run a build or a sweep with `run_in_background` and then start another
without checking whether the first is still alive.
