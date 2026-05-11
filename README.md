# wood_nano

Python bindings for the wood C++ timber joinery library.

## Install in Rhino (first time or after clearing packages)

Run these four commands in order in the Rhino ScriptEditor terminal:

```
pip install numpy protobuf grpcio-tools
pip install -e C:\pc\3_code\code_rust\session\session_py
pip install -e C:\pc\3_code\code_rust\session\session_rhino
pip install scikit-build-core nanobind
pip install --no-build-isolation -e C:\pc\3_code\code_cpp\wood_nano
```

## Rebuild after C++ changes

Run when `.cpp`, `.h`, or `CMakeLists.txt` files change:

```
uv pip install --no-build-isolation -e C:/pc/3_code/code_cpp/wood_nano
"C:/Users/Petras/.rhinocode/py39-rh8/python.exe" -m pip install --no-build-isolation -e C:/pc/3_code/code_cpp/wood_nano    
```

Then click **Reset Python Engine** in the ScriptEditor toolbar.

Python-only changes (`src/wood_nano/*.py`) take effect immediately — no rebuild needed.

## Usage

```python
from wood_nano import translation_shell_elements

shell, elements = translation_shell_elements(
    thickness=15.0,
    chamfer=2.0,
    chamfer_angle=90.0,
)
```