# wood_nano

Python bindings for the wood C++ timber joinery library.

## Install in Rhino (first time)

**1. Install build tools** (terminal, once):

```bash
"C:/Users/Petras/.rhinocode/py39-rh8/python.exe" -m pip install scikit-build-core nanobind ninja
```

**2. Install dependencies and wood_nano** (Rhino ScriptEditor terminal):

```bash
pip install numpy
pip install -e C:\pc\3_code\code_rust\session\session_py
pip install -e C:\pc\3_code\code_rust\session\session_rhino
pip install --no-build-isolation -e C:\pc\3_code\code_cpp\wood_nano
```

## Rebuild after C++ changes

```bash
"C:/Users/Petras/.rhinocode/py39-rh8/python.exe" -m pip install --no-build-isolation -e C:/pc/3_code/code_cpp/wood_nano
copy "C:/Users/Petras/.rhinocode/py39-rh8/lib/site-packages/wood_nano/_translation_shell.cp39-win_amd64.pyd" src/wood_nano/
```

Then **Reset Python Engine** in the ScriptEditor toolbar.

Python-only changes (`src/wood_nano/*.py`) take effect immediately.

## uv dev environment (first time)

```bash
uv venv
uv pip install scikit-build-core nanobind numpy pytest ninja
uv pip install --no-build-isolation -e .
```

## Usage

```python
from wood_nano import translation_shell_elements

shell, elements = translation_shell_elements(
    thickness=15.0,
    chamfer=2.0,
    chamfer_angle=90.0,
)
```