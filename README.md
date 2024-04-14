wood_nano
=============

|      CI              | status |
|----------------------|--------|
| pip builds           | [![Pip Action Status][actions-pip-badge]][actions-pip-link] |
| wheels               | [![Wheel Action Status][actions-wheels-badge]][actions-wheels-link] |

[actions-pip-link]:        https://github.com/wjakob/nanobind_example/actions?query=workflow%3APip
[actions-pip-badge]:       https://github.com/wjakob/nanobind_example/workflows/Pip/badge.svg
[actions-wheels-link]:     https://github.com/wjakob/nanobind_example/actions?query=workflow%3AWheels
[actions-wheels-badge]:    https://github.com/wjakob/nanobind_example/workflows/Wheels/badge.svg


This repository contains a tiny project showing how to create C++ bindings
using [nanobind](https://github.com/wjakob/nanobind) and
[scikit-build-core](https://scikit-build-core.readthedocs.io/en/latest/index.html). It
was derived from the corresponding _pybind11_ [example
project](https://github.com/pybind/scikit_build_example/) developed by
[@henryiii](https://github.com/henryiii).

Installation
------------

1. Clone this repository
2. Run `pip install ./wood_nano`

Afterwards, you should be able to issue the following commands (shown in an
interactive Python session):

```pycon
>>> import nanobind_example
>>> nanobind_example.add(1, 2)
3
```

CI Examples
-----------

The `.github/workflows` directory contains two continuous integration workflows
for GitHub Actions. The first one (`pip`) runs automatically after each commit
and ensures that packages can be built successfully and that tests pass.

The `wheels` workflow uses
[cibuildwheel](https://cibuildwheel.readthedocs.io/en/stable/) to automatically
produce binary wheels for a large variety of platforms. If a `pypi_password`
token is provided using GitHub Action's _secrets_ feature, this workflow can
even automatically upload packages on PyPI.


License
-------

_nanobind_ and this example repository are both provided under a BSD-style
license that can be found in the [LICENSE](./LICENSE) file. By using,
distributing, or contributing to this project, you agree to the terms and
conditions of this license.

Customization
=============

Conda envirnoment
-----------------

```bash
conda config --add channels conda-forge
conda create -n wood python==3.8.16 pypy=7.3.11

```

Rhino ScriptEditor
------------------

```bash
C:/Users/petras/.rhinocode/py39-rh8/python.exe -m pip install . 
```

```python
import os
import os.path as op
import sys
import ctypes

CONDA_ENV = r'C:\Users\petras\.conda\envs\wood'
COMPAS_WOOD_PATH = r'C:\brg\2_code\wood_nano\build\pp38-pypy38_pp73-win_amd64\Release'
sys.path.append(op.join(CONDA_ENV, r"Lib\site-packages"))
sys.path.append(COMPAS_WOOD_PATH)
os.add_dll_directory(op.join(CONDA_ENV, r'Library\bin'))
os.add_dll_directory(COMPAS_WOOD_PATH)

import nanobind_example
print(nanobind_example.add(1, 2))

```

wood submodule and download dependecies
-------------------------------------------

```bash
cd ~/brg/2_code/wood_nano/src
git submodule add https://github.com/petrasvestartas/wood.git
cd wood
sudo '/home/petras/brg/2_code/wood_nano/src/wood/install_ubuntu.sh'
```


link wood dependencies to nanobind cmake
--------------------------------------------
-   Ubuntu - linked, Check: a) PCH is not speeding the build, b) SQL has no be unlocked like this ```sudo chown -R```, be aware that the .sh file installs gmp and mpfr in ubuntu, not as a cmake source code.
-   Windows - linked, Check: a) C:\Users\petras\.conda\envs\wood\Lib\site-packages\wood_nano must have cgal libgmp-10.dll and libmpfr-4.dll, it would be great that gmp and mpfr would be compiled together into one single .pyd file.
-   Mac - not linked

pip
---
```bash
pip install build setuptools wheel
conda install twine
ubuntu:
export BUILDING_DIST="1" && python -m build --wheel
windows:
python -m build --wheel
```
-   upload to pip https://github.com/petrasvestartas/compas_snippets

code wrapping
-------------
-   for development you need to use pip install . and even you changed __init__.py
-   function based on the EDX tutorial

compas_wood
-----------


```bash
git branch v2
git checkout v2
conda config --add channels conda-forge
conda create -n compas_wood python==3.8.16 pypy=7.3.11
conda activate compas_wood
pip install build setuptools wheel cookiecutter jinja2_time compas_invocations
sudo apt install twine or conda install twine
cookiecutter gh:compas-dev/compas_package_template
export PATH="~/anaconda3/envs/compas_wood/bin:$PATH"
sudo apt install invoke
pip install -r requirements.txt
```

-   add requirements wood-cpp-nano
-   rewrite examples
-   compas_wood must be installable by ```pip install compas_wood```
-   documentation based on edx tutorials
-   create compas_model with vizualization
-   upload to pip https://github.com/petrasvestartas/compas_snippets

EDX
---
-   answer comments