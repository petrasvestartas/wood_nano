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
5. After rebuilding, copy the new `.pyd` to `src/wood_nano/` for Rhino compatibility.

## No-prototype rule

Never implement geometry in the Python wrappers as a "temporary" approximation.
If the C++ side is not ready, leave the function unimplemented rather than
writing a Python fallback that will silently produce wrong results.

## Rebuild steps (after C++ changes)

```bash
# Rhino Python (primary target)
"C:/Users/Petras/.rhinocode/py39-rh8/python.exe" -m pip install --no-build-isolation -e .
copy "C:/Users/Petras/.rhinocode/py39-rh8/lib/site-packages/wood_nano/_translation_shell.cp39-win_amd64.pyd" src/wood_nano/

# uv dev environment
uv pip install --no-build-isolation -e .
```
